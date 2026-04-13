from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime
import math

from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
from ..models.ventas import ARDocument, ARDocumentDetail
from ..models.nube_response import ARFENube
from ..schemas.common import EstadoDocumento, AuditoriaBase
from ..schemas.nubefact import (
    NubeFactRequest,
    NubeFactGuiaRequest,
    NubeFactRetencionRequest,
    NubeFactItem,
    NubeFactRetencionItem,
)
from .nubefact_client import nubefact_client


class DocumentService:
    """Servicio para gestión de documentos"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def _fecha_excel_to_date(self, excel_date: float) -> str:
        """Convierte fecha de Excel a formato dd-mm-YYYY"""
        if not excel_date:
            return ""
        try:
            # Excel fecha base: 30/12/1899
            from datetime import datetime, timedelta
            base_date = datetime(1899, 12, 30)
            result_date = base_date + timedelta(days=int(excel_date))
            return result_date.strftime("%d-%m-%Y")
        except:
            return ""
    
    def _map_estado(self, estado: str) -> EstadoDocumento:
        """Mapea estado de DB a enum"""
        estado_map = {
            "pendiente": EstadoDocumento.PENDIENTE,
            "enviado": EstadoDocumento.ENVIADO_NUBEFACT,
            "enviado_nubefact": EstadoDocumento.ENVIADO_NUBEFACT,
            "aceptada": EstadoDocumento.ACEPTADO_SUNAT,
            "aceptado": EstadoDocumento.ACEPTADO_SUNAT,
            "aceptada_observaciones": EstadoDocumento.ACEPTADO_OBSERVACIONES,
            "rechazada": EstadoDocumento.RECHAZADO,
            "rechazado": EstadoDocumento.RECHAZADO,
            "error": EstadoDocumento.ERROR,
        }
        return estado_map.get(estado.lower(), EstadoDocumento.PENDIENTE)
    
    def _puede_editar(self, estado: str) -> bool:
        """Determina si un documento puede ser editado"""
        estado_enum = self._map_estado(estado)
        return estado_enum in [
            EstadoDocumento.RECHAZADO,
            EstadoDocumento.ACEPTADO_OBSERVACIONES,
            EstadoDocumento.PENDIENTE,
            EstadoDocumento.ERROR,
        ]
    
    # ==================== GUÍAS DE REMISIÓN ====================
    
    async def enviar_guia(self, transaction_id: str, usuario: str) -> Dict[str, Any]:
        """Envía guía de remisión a NubeFact"""
        # Obtener guía con detalles
        guia = self.db.query(WHTransaction).filter(
            WHTransaction.Transaction == transaction_id
        ).first()
        
        if not guia:
            return {"success": False, "message": "Guía no encontrada"}
        
        if guia.envio_nube and "aceptada" in guia.envio_nube.lower():
            return {"success": False, "message": "La guía ya fue enviada y aceptada"}
        
        # Construir request para NubeFact
        items = []
        for det in guia.detalles:
            items.append(NubeFactItem(
                unidad_de_medida="NIU",
                codigo=det.ItemCode or "",
                descripcion=det.ItemDescription or "",
                cantidad=det.Quantity or 0,
            ))
        
        # Mapear motivo de traslado
        motivo_map = {
            "VENTA": "01",
            "CONSIGNACIÓN": "05",
            "TRASLADOS ENTRE ESTABLECIMIENTOS DE LA EMPRESA": "04",
            "OTROS": "13",
            "COMPRA": "02",
        }
        codigo_motivo = motivo_map.get(guia.MotivoTraslado, "")
        
        # Determinar tipo de transporte
        tipo_transporte = "02" if guia.RucTransportista == "20602674488" else "01"
        
        # Construir request
        request = NubeFactGuiaRequest(
            serie=guia.DocumentSerie,
            numero=guia.DocumentNo,
            cliente_tipo_de_documento="6" if len(guia.TargetPersonRUC or "") == 11 else "1",
            cliente_numero_de_documento=guia.TargetPersonRUC or "",
            cliente_denominacion=guia.TargetPersonName or "",
            cliente_direccion=guia.TargetAddress or "",
            fecha_de_emision=self._fecha_excel_to_date(guia.FechaTraslado),
            observaciones=guia.Comments or "",
            motivo_de_traslado=codigo_motivo,
            peso_bruto_total=guia.PesoBruto or 0,
            numero_de_bultos=sum(d.QuantityBultos or 0 for d in guia.detalles),
            tipo_de_transporte=tipo_transporte,
            fecha_de_inicio_de_traslado=self._fecha_excel_to_date(guia.FechaTraslado),
            transportista_documento_numero=guia.RucTransportista or "",
            transportista_denominacion=guia.Transportista or "",
            transportista_placa_numero=guia.VehicleID or "",
            conductor_documento_numero=guia.LicenciaConducir[1:] if guia.LicenciaConducir else "",
            conductor_nombre=guia.Driver.split()[2] if guia.Driver and len(guia.Driver.split()) > 2 else "",
            conductor_apellidos=f"{guia.Driver.split()[0]} {guia.Driver.split()[1]}" if guia.Driver and len(guia.Driver.split()) > 1 else "",
            conductor_numero_licencia=guia.LicenciaConducir or "",
            punto_de_partida_ubigeo=guia.ubigeo_des or "",
            punto_de_partida_direccion=guia.origenaddress or "",
            punto_de_llegada_ubigeo=guia.ubigeo_des or "",
            punto_de_llegada_direccion=guia.TargetAddress or "",
            items=items,
        )
        
        # Enviar a NubeFact
        response = await nubefact_client.generar_guia(request)
        
        # Actualizar estado
        if response.success:
            guia.envio_nube = "aceptada"
        else:
            guia.envio_nube = "error"
        
        self.db.commit()
        
        return {
            "success": response.success,
            "message": response.message,
            "data": response.model_dump(exclude_none=True)
        }
    
    # ==================== RETENCIONES ====================
    
    async def enviar_retencion(self, retencion_id: int, usuario: str) -> Dict[str, Any]:
        """Envía retención a NubeFact"""
        retencion = self.db.query(APRetencion).filter(
            APRetencion.Id == retencion_id
        ).first()
        
        if not retencion:
            return {"success": False, "message": "Retención no encontrada"}
        
        if retencion.status == "enviado":
            return {"success": False, "message": "La retención ya fue enviada"}
        
        # Construir items
        items = []
        for det in retencion.detalles:
            items.append(NubeFactRetencionItem(
                documento_relacionado_serie=det.DRserie,
                documento_relacionado_numero=det.DRnumero,
                documento_relacionado_fecha_de_emision=self._fecha_excel_to_date(det.DRfecha),
                documento_relacionado_moneda="1" if det.DRmoneda == "LO" else "2",
                documento_relacionado_total=det.DRtotal,
                pago_fecha=self._fecha_excel_to_date(det.DRpagoFecha),
                pago_numero=str(det.DRpagoNro),
                pago_total_sin_retencion=det.DRpagoTotal,
                tipo_de_cambio=det.TipoCambio,
                tipo_de_cambio_fecha=self._fecha_excel_to_date(det.TipoCambioFecha),
                importe_retenido=det.Retenido,
                importe_retenido_fecha=self._fecha_excel_to_date(det.RetenidoFecha),
                importe_pagado_con_retencion=det.Pagado,
            ))
        
        # Construir request
        request = NubeFactRetencionRequest(
            serie=retencion.Serie,
            numero=retencion.Numero,
            cliente_numero_de_documento=retencion.VendorRuc,
            cliente_denominacion=retencion.VendorName,
            cliente_direccion=retencion.VendorAddress,
            fecha_de_emision=self._fecha_excel_to_date(retencion.DocumentDate),
            tipo_de_tasa_de_retencion="1" if retencion.Tasa == 3 else "2",
            total_retenido=retencion.TotalRetenido,
            total_pagado=retencion.TotalPagado,
            observaciones=retencion.Obs or "",
            items=items,
        )
        
        # Enviar a NubeFact
        response = await nubefact_client.generar_retencion(request)
        
        # Actualizar estado
        if response.success:
            retencion.status = "enviado"
            
            # Guardar respuesta
            status_record = APRetencionStatus(
                Retencion=retencion.Id,
                Status="aceptada" if response.aceptada_por_sunat else "rechazada",
                Pdf=response.enlace_del_pdf,
                Xml=response.enlace_del_xml,
                Cdr=response.enlace_del_cdr,
                Aceptacion=response.enlace,
                Descripcion=response.sunat_description,
                Nota=response.sunat_note,
                ResponseCode=response.sunat_responsecode,
                Soap=response.sunat_soap_error,
                XlastUser=usuario,
                XlastDate=datetime.now().timestamp(),
            )
            self.db.add(status_record)
        else:
            retencion.status = "error"
        
        self.db.commit()
        
        return {
            "success": response.success,
            "message": response.message,
            "data": response.model_dump(exclude_none=True)
        }
    
    # ==================== DOCUMENTOS DE VENTA ====================
    
    async def enviar_documento_venta(self, document_id: str, usuario: str) -> Dict[str, Any]:
        """Envía documento de venta a NubeFact"""
        documento = self.db.query(ARDocument).filter(
            ARDocument.Document == document_id
        ).first()
        
        if not documento:
            return {"success": False, "message": "Documento no encontrado"}
        
        if documento.fe == "enviado":
            return {"success": False, "message": "El documento ya fue enviado"}
        
        # Construir items
        items = []
        for det in documento.detalles:
            items.append(NubeFactItem(
                unidad_de_medida=self._map_unidad(det.Unit),
                codigo=det.ItemCode or "",
                descripcion=det.Description or "",
                cantidad=det.Quantity or 0,
                valor_unitario=det.Price or 0,
                precio_unitario=det.PriceTax or 0,
                subtotal=det.SubTotal or 0,
                tipo_de_igv="1",
                igv=det.TotalTaxLo or 0,
                total=det.Total or 0,
                codigo_producto_sunat=None,
            ))
        
        # Mapear tipo de documento
        tipo_doc_map = {
            "LIMADSASFACTURA": 1,
            "LIMADSASBOLETA": 2,
            "LIMADSASCREDITO": 3,  # Nota de crédito
            "LIMADSASDEBITO": 4,   # Nota de débito
        }
        tipo_comprobante = tipo_doc_map.get(documento.DocumentType, 1)
        
        # Mapear tipo de cliente
        tipo_cliente = "6" if len(documento.VendorRUC or "") == 11 else "1"
        
        # Construir request
        request = NubeFactRequest(
            tipo_de_comprobante=tipo_comprobante,
            serie=documento.DocumentSerie,
            numero=documento.DocumentNo,
            cliente_tipo_de_documento=tipo_cliente,
            cliente_numero_de_documento=documento.VendorRUC or "",
            cliente_denominacion=documento.VendorName or "",
            cliente_direccion=documento.VendorAddress or "",
            fecha_de_emision=self._fecha_excel_to_date(documento.DocumentDate),
            fecha_de_vencimiento=self._fecha_excel_to_date(documento.DueDate),
            moneda="1" if documento.DocumentCurrency == "LO" else "2",
            tipo_de_cambio=documento.ExchangeRate,
            total_gravada=documento.AmountNetLo or 0,
            total_igv=documento.AmountTaxLo or 0,
            total=documento.AmountTotalLo or 0,
            items=items,
        )
        
        # Enviar a NubeFact
        response = await nubefact_client.generar_comprobante(request)
        
        # Actualizar estado
        if response.success:
            documento.fe = "enviado"
            
            # Guardar respuesta
            nube_record = ARFENube(
                serie=documento.DocumentSerie,
                numero=documento.DocumentNo,
                enlace=response.enlace,
                aceptada_por_sunat="true" if response.aceptada_por_sunat else "false",
                sunat_description=response.sunat_description,
                sunat_note=response.sunat_note,
                sunat_responsecode=response.sunat_responsecode,
                sunat_soap_error=response.sunat_soap_error,
                pdf_zip_base64=response.pdf_zip_base64,
                xml_zip_base64=response.xml_zip_base64,
                cdr_zip_base64=response.cdr_zip_base64,
                codigo_hash_qr=response.cadena_para_codigo_qr,
                codigo_hash=response.codigo_hash,
                fecha_envio=datetime.now().timestamp(),
                usuario_envio=usuario,
            )
            self.db.add(nube_record)
        else:
            documento.fe = "Error"
        
        self.db.commit()
        
        return {
            "success": response.success,
            "message": response.message,
            "data": response.model_dump(exclude_none=True)
        }
    
    def _map_unidad(self, unidad: str) -> str:
        """Mapea unidad de medida"""
        unidad_map = {
            "UND": "NIU",
            "PARES": "PR",
            "KG": "KG",
        }
        return unidad_map.get(unidad, "NIU")
