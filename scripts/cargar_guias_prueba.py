"""
Script para cargar guías de remisión de prueba desde archivos JSON.
No envía a NubeFact, solo inserta en la base de datos.
"""
import sys
import os
import json
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models.guias import WHTransaction, WHTransactionDetail


def fecha_excel(fecha_str: str) -> float:
    """Convierte fecha dd-mm-YYYY a formato Excel (días desde 1899-12-30)"""
    try:
        fecha = datetime.strptime(fecha_str, "%d-%m-%Y")
        return (fecha - datetime(1899, 12, 30)).days
    except:
        return (datetime.now() - datetime(1899, 12, 30)).days


def motivo_codigo(motivo: str) -> str:
    """Convierte código de motivo a descripción"""
    motivos = {
        "01": "VENTA",
        "02": "COMPRA",
        "04": "TRASLADOS ENTRE ESTABLECIMIENTOS DE LA EMPRESA",
        "05": "CONSIGNACIÓN",
        "13": "OTROS",
    }
    return motivos.get(motivo, "OTROS")


def cargar_guia(db: Session, data: dict, es_correcta: bool, numero_orden: int, linea_inicio: int) -> dict:
    """Carga una guía de remisión desde datos JSON"""
    
    timestamp = datetime.now().timestamp()
    fecha = fecha_excel(data.get("fecha_de_emision", ""))
    
    # Generar ID único para la transacción
    serie = data.get("serie", "T001")
    numero = data.get("numero", str(numero_orden).zfill(8))
    transaction_id = f"GUIA_TEST_{serie}_{numero}_{datetime.now().strftime('%Y%m%d%H%M%S')}"
    
    # Crear cabecera (truncar valores largos para evitar errores de BD)
    guia = WHTransaction(
        Transaction=transaction_id,
        DocumentSerie=(serie or "")[:10],
        DocumentNo=(numero or "")[:20],
        TransactionDate=fecha,
        FechaTraslado=fecha,  # Fecha de traslado requerida por NubeFact
        TargetPersonRUC=(data.get("cliente_numero_de_documento") or "")[:20],
        TargetPersonName=(data.get("cliente_denominacion") or "")[:200],
        TargetAddress=(data.get("cliente_direccion") or "")[:200],
        MotivoTraslado=motivo_codigo(data.get("motivo_de_traslado", "13")),
        PesoBruto=data.get("peso_bruto_total", 0) if isinstance(data.get("peso_bruto_total"), (int, float)) else 0,
        RucTransportista=(data.get("transportista_documento_numero") or "")[:20],
        Transportista=(data.get("transportista_denominacion") or "")[:100],
        VehicleID=(data.get("transportista_placa_numero") or "")[:20],
        Driver=((data.get("conductor_nombre") or "") + " " + (data.get("conductor_apellidos") or ""))[:100],
        LicenciaConducir=(data.get("conductor_numero_licencia") or "")[:20],
        origenaddress=(data.get("punto_de_partida_direccion") or "")[:200],
        ubigeo_des=(data.get("punto_de_llegada_ubigeo") or "")[:10],
        Comments=(data.get("observaciones") or "")[:4000],
        SaleDocAbbrev="FT" if data.get("documento_relacionado") and isinstance(data.get("documento_relacionado"), list) else None,
        SaleDocSerie=(data["documento_relacionado"][0].get("serie", "") or "")[:10] if data.get("documento_relacionado") and isinstance(data.get("documento_relacionado"), list) else None,
        SaleDocNo=(data["documento_relacionado"][0].get("numero", "") or "")[:20] if data.get("documento_relacionado") and isinstance(data.get("documento_relacionado"), list) else None,
        envio_nube="pendiente",  # Pendiente de envío
        Status=None,
        XLastUser="SCRIPT_CARGA_GUIAS",
        XLastDate=timestamp,
    )
    db.add(guia)
    db.flush()
    
    # Crear detalles con líneas únicas
    items = data.get("items") or []
    for i, item in enumerate(items):
        detalle = WHTransactionDetail(
            Line=linea_inicio + i,  # Línea única global
            Transaction=transaction_id,
            Unit=item.get("unidad_de_medida") or "NIU",
            ItemCode=item.get("codigo") or "",
            ItemDescription=item.get("descripcion") or "",
            Quantity=item.get("cantidad", 0) if isinstance(item.get("cantidad"), (int, float)) else 0,
            XLastUser="SCRIPT_CARGA_GUIAS",
            XLastDate=timestamp,
        )
        db.add(detalle)
    
    return {
        "transaction_id": transaction_id,
        "serie": serie,
        "numero": numero,
        "es_correcta": es_correcta,
        "ruc": data.get("cliente_numero_de_documento", ""),
        "items_count": len(items),
        "siguiente_linea": linea_inicio + len(items),
    }


def main():
    db = SessionLocal()
    
    # Ruta de los archivos de prueba
    tests_dir = Path(__file__).parent.parent / "tests" / "guias"
    
    if not tests_dir.exists():
        print(f"Error: No existe el directorio {tests_dir}")
        return
    
    try:
        print("=" * 60)
        print("CARGANDO GUÍAS DE REMISIÓN DE PRUEBA")
        print("=" * 60)
        
        # Obtener el máximo número de línea existente
        max_line = db.query(WHTransactionDetail.Line).order_by(WHTransactionDetail.Line.desc()).first()
        linea_actual = (max_line[0] if max_line else 0) + 1
        
        resultados = []
        numero_orden = 1
        
        # Archivos correctos
        archivos_correctos = ["guia_correcta_01.json", "guia_correcta_02.json"]
        for archivo in archivos_correctos:
            ruta = tests_dir / archivo
            if ruta.exists():
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resultado = cargar_guia(db, data, es_correcta=True, numero_orden=numero_orden, linea_inicio=linea_actual)
                resultados.append(resultado)
                linea_actual = resultado["siguiente_linea"]
                print(f"\n[CORRECTA] {archivo}")
                print(f"  Transaction: {resultado['transaction_id']}")
                print(f"  Serie-Número: {resultado['serie']}-{resultado['numero']}")
                print(f"  RUC: {resultado['ruc']}")
                print(f"  Items: {resultado['items_count']}")
                numero_orden += 1
            else:
                print(f"\n[ADVERTENCIA] No encontrado: {archivo}")
        
        # Archivos incorrectos
        archivos_incorrectos = ["guia_incorrecta_01.json", "guia_incorrecta_02.json"]
        for archivo in archivos_incorrectos:
            ruta = tests_dir / archivo
            if ruta.exists():
                with open(ruta, "r", encoding="utf-8") as f:
                    data = json.load(f)
                resultado = cargar_guia(db, data, es_correcta=False, numero_orden=numero_orden, linea_inicio=linea_actual)
                resultados.append(resultado)
                linea_actual = resultado["siguiente_linea"]
                print(f"\n[INCORRECTA] {archivo}")
                print(f"  Transaction: {resultado['transaction_id']}")
                print(f"  Serie-Número: {resultado['serie']}-{resultado['numero']}")
                print(f"  RUC: {resultado['ruc']}")
                print(f"  Items: {resultado['items_count']}")
                numero_orden += 1
            else:
                print(f"\n[ADVERTENCIA] No encontrado: {archivo}")
        
        db.commit()
        
        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)
        correctas = sum(1 for r in resultados if r["es_correcta"])
        incorrectas = sum(1 for r in resultados if not r["es_correcta"])
        print(f"Guías correctas cargadas: {correctas}")
        print(f"Guías incorrectas cargadas: {incorrectas}")
        print(f"Total: {len(resultados)}")
        print("\nEstado: pendiente (listas para enviar a NubeFact)")
        print("=" * 60)
        
    except Exception as e:
        print(f"\nError: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
