import asyncio
from sqlalchemy.orm import Session
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
import math
import httpx

from ..models.guias import WHTransaction, WHTransactionDetail
from ..models.retenciones import APRetencion, APRetencionDetail, APRetencionStatus
from ..models.ventas import ARDocument, ARDocumentDetail
from ..models.nube_response import ARFENube
from ..models.guia_response import WHTransactionNube
from ..schemas.common import EstadoDocumento, AuditoriaBase
from .notification_service import NotificationService
from ..schemas.nubefact import (
    NubeFactRequest,
    NubeFactGuiaRequest,
    NubeFactRetencionRequest,
    NubeFactItem,
    NubeFactRetencionItem,
)
from .nubefact_client import nubefact_client
from ..utils.datetime import now_peru


class DocumentService:
    """Servicio para gestión de documentos"""

    def __init__(self, db: Session):
        self.db = db
    
    def _fecha_excel_to_date(self, excel_date: Any) -> str:
        """Convierte fecha (datetime, float de Excel o str) a formato dd-mm-YYYY"""
        if not excel_date:
            return ""
        from datetime import datetime, date, timedelta
        
        # Si ya es un objeto datetime o date
        if isinstance(excel_date, (datetime, date)):
            return excel_date.strftime("%d-%m-%Y")
            
        try:
            # Si es un número (o string numérico) que representa fecha de Excel
            # Excel fecha base: 30/12/1899
            val = float(excel_date)
            base_date = datetime(1899, 12, 30)
            result_date = base_date + timedelta(days=int(val))
            return result_date.strftime("%d-%m-%Y")
        except (ValueError, TypeError):
            # Si es un string, intentar limpiar y retornar o parsear
            if isinstance(excel_date, str):
                # Si ya tiene el formato correcto (ej: 27-05-2026 o 27/05/2026)
                clean_str = excel_date.strip()
                if len(clean_str) == 10 and (clean_str[2] == '-' or clean_str[2] == '/'):
                    return clean_str.replace('/', '-')
                # Si viene en formato YYYY-MM-DD
                try:
                    parsed_dt = datetime.strptime(clean_str[:10], "%Y-%m-%d")
                    return parsed_dt.strftime("%d-%m-%Y")
                except ValueError:
                    pass
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
    
    async def enviar_guia(self, transaction_id: str, usuario: str, es_masivo: bool = False) -> Dict[str, Any]:
        """Envía guía de remisión llamando a la API PHP local de envío y luego a la de consulta"""
        # 1. Obtener guía con detalles
        guia = self.db.query(WHTransaction).filter(
            WHTransaction.Transaction == transaction_id
        ).first()
        
        if not guia:
            return {"success": False, "message": "Guía no encontrada"}
        
        if guia.envio_nube and "aceptada" in guia.envio_nube.lower():
            return {"success": False, "message": "La guía ya fue enviada y aceptada"}
        
        if guia.necesita_aprobacion:
            return {"success": False, "message": "La guía requiere aprobación del administrador antes de ser enviada"}
        
        # Resetear el estado a 'pendiente' en la base de datos antes de llamar al PHP de envío
        guia.envio_nube = "pendiente"
        guia.nube_status_web = "pendiente"
        self.db.commit()
        
        # --- PASO 1: LLAMAR A LA API PHP DE ENVÍO (envioguia1.php) ---
        url_envio = f"http://192.168.1.3/sistemas/gr/envioguia1.php?Doc={transaction_id}"
        if not es_masivo:
            print(f"[GUIA] Paso 1: Llamando a API local de Envío: {url_envio}")
            
        php_envio_output = ""
        try:
            # Timeout de 60.0 segundos ya que el script de PHP puede tardar en responder al comunicarse con NubeFact/SUNAT
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url_envio)
                php_envio_output = response.text.strip()
                if not es_masivo:
                    print(f"[GUIA] Respuesta API Envío - Status: {response.status_code}")
                    print(f"[GUIA] Cuerpo respuesta Envío: {php_envio_output[:500]}")
        except Exception as e:
            php_envio_output = f"Error al conectar con la API local de Envío: {type(e).__name__} - {str(e)}"
            if not es_masivo:
                print(f"[GUIA] {php_envio_output}")

        # Esperar un momento y rollback para sincronizar la sesión antes de verificar
        await asyncio.sleep(1.5)
        self.db.rollback()
        
        # Volver a obtener el registro de la guía
        guia = self.db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()
        
        # Analizar respuesta del envío
        php_envio_lower = php_envio_output.lower()
        is_accepted = "aceptada" in php_envio_lower or php_envio_lower == "aceptada"
        is_already_sent = False
        if "ya fue enviado" in php_envio_lower or "ya existe" in php_envio_lower or "enviado anteriormente" in php_envio_lower:
            is_already_sent = True

        if not (is_accepted or is_already_sent):
            # Si el envío falló, registrar el error y salir sin llamar al script de consulta
            guia.envio_nube = "error"
            guia.nube_status_web = "error"
            guia.RejectionReason = php_envio_output[:500]
            self.db.commit()
            
            # Notificar error de envío por WhatsApp
            try:
                notification_service = NotificationService(self.db)
                await notification_service.notificar_error_documento(
                    tipo_modulo="guias",
                    tipo_documento="guia",
                    serie=guia.DocumentSerie,
                    numero=guia.DocumentNo,
                    error=php_envio_output,
                    documento_id=guia.Transaction
                )
            except Exception as ne:
                if not es_masivo:
                    print(f"[GUIA] Error al enviar notificación de error de envío por WhatsApp: {ne}")
                    
            return {
                "success": False,
                "message": f"Error en envío inicial (envioguia1.php): {php_envio_output}",
                "data": {"errors": [php_envio_output]}
            }

        # --- PASO 2: LLAMAR A LA API PHP DE CONSULTA (consult_guia.php) ---
        # Determinamos el ID a enviar (id_guia_remision o en su defecto transaction_id)
        id_doc_consulta = guia.id_guia_remision or transaction_id
        url_consulta = f"http://192.168.1.3/sis/guias/consult_guia.php?serie={guia.DocumentSerie}&numero={guia.DocumentNo}&id={id_doc_consulta}"
        
        if not es_masivo:
            print(f"[GUIA] Paso 2: Llamando a API local de Consulta: {url_consulta}")
            
        php_consulta_output = ""
        try:
            # Llamamos al PHP de consulta (este script actualiza NB_GuiasStatus y envía WhatsApps de éxito/rechazo de SUNAT)
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url_consulta)
                php_consulta_output = response.text.strip()
                if not es_masivo:
                    print(f"[GUIA] Respuesta API Consulta - Status: {response.status_code}")
                    print(f"[GUIA] Cuerpo respuesta Consulta: {php_consulta_output[:500]}")
        except Exception as e:
            php_consulta_output = f"Error al conectar con la API local de Consulta: {type(e).__name__} - {str(e)}"
            if not es_masivo:
                print(f"[GUIA] {php_consulta_output}")

        # Esperar un momento y sincronizar sesión
        await asyncio.sleep(1.5)
        self.db.rollback()
        
        # Volver a obtener el registro de la guía
        guia = self.db.query(WHTransaction).filter(WHTransaction.Transaction == transaction_id).first()

        # --- PASO 3: CONSULTA INTERNA EN PYTHON PARA ACTUALIZAR WH_Transaction_Nube ---
        # Llamamos al método interno de python para asegurar que 'wh_transaction_nube' se actualice 
        # y que el frontend de FastAPI pueda descargar el PDF/XML/CDR desde el dashboard
        consult_result = await self.consultar_guia(transaction_id)
        if consult_result.get("success"):
            return consult_result
            
        # Si la consulta interna de Python falla por alguna razón (ej. problemas de red con el cliente Python), 
        # pero sabemos que la guía fue aceptada por el flujo PHP/Nubefact:
        guia.envio_nube = "aceptada"
        guia.nube_status_web = "aceptado"
        self.db.commit()
        
        return {
            "success": True,
            "message": "La guía ya fue enviada anteriormente" if is_already_sent else "Guía enviada y consultada exitosamente a través de las APIs locales.",
            "data": {}
        }
    
    async def consultar_guia(self, transaction_id: str) -> Dict[str, Any]:
        """Consulta el estado de una guía en NubeFact/SUNAT"""
        from ..schemas.nubefact import NubeFactConsultRequest
        
        guia = self.db.query(WHTransaction).filter(
            WHTransaction.Transaction == transaction_id
        ).first()
        
        if not guia:
            return {"success": False, "message": "Guía no encontrada"}
        
        # Consultar a NubeFact
        consult_request = NubeFactConsultRequest(
            tipo_de_comprobante=7,
            serie=guia.DocumentSerie,
            numero=guia.DocumentNo
        )
        
        response = await nubefact_client.consultar_guia(consult_request)
        
        # Si la consulta fue exitosa y SUNAT aceptó, actualizar
        if response.success and response.aceptada_por_sunat:
            guia.envio_nube = "aceptada"
            guia.nube_status_web = "aceptado"
            guia.RejectionReason = None
            
            # Actualizar o crear registro de respuesta
            nube_record = self.db.query(WHTransactionNube).filter(
                WHTransactionNube.TransactionId == transaction_id
            ).first()
            
            if nube_record:
                nube_record.aceptada_por_sunat = "true"
                nube_record.enlace_del_pdf = response.enlace_del_pdf
                nube_record.enlace_del_xml = response.enlace_del_xml
                nube_record.enlace_del_cdr = response.enlace_del_cdr
                nube_record.sunat_description = response.sunat_description
                nube_record.sunat_note = response.sunat_note
                nube_record.pdf_zip_base64 = response.pdf_zip_base64
                nube_record.xml_zip_base64 = response.xml_zip_base64
                nube_record.cdr_zip_base64 = response.cdr_zip_base64
            
            self.db.commit()
            
            return {
                "success": True,
                "message": "Guía aceptada por SUNAT",
                "data": response.model_dump(exclude_none=True)
            }
        
        # Si hay errores, devolver el mensaje
        mensaje = response.message
        if response.errors:
            mensaje = response.message + ": " + ", ".join(response.errors)
        
        return {
            "success": response.success,
            "message": mensaje,
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
        
        if retencion.necesita_aprobacion:
            return {"success": False, "message": "La retención requiere aprobación del administrador antes de ser enviada"}
        
        # Construir items
        items = []
        for det in retencion.detalles:
            items.append(NubeFactRetencionItem(
                documento_relacionado_serie=det.DRserie or "",
                documento_relacionado_numero=det.DRnumero or "",
                documento_relacionado_fecha_de_emision=self._fecha_excel_to_date(det.DRfecha),
                documento_relacionado_moneda="1" if det.DRmoneda == "LO" else "2",
                documento_relacionado_total=det.DRtotal or 0.0,
                pago_fecha=self._fecha_excel_to_date(det.DRpagoFecha),
                pago_numero=str(det.DRpagoNro or ""),
                pago_total_sin_retencion=det.DRtotal or 0.0,
                tipo_de_cambio=det.TipoCambio or 1.0,
                tipo_de_cambio_fecha=self._fecha_excel_to_date(det.TipoCambioFecha),
                importe_retenido=det.Retenido or 0.0,
                importe_retenido_fecha=self._fecha_excel_to_date(det.RetenidoFecha),
                importe_pagado_con_retencion=det.Pagado or 0.0,
            ))
        
        # Construir request
        request = NubeFactRetencionRequest(
            serie=retencion.Serie,
            numero=retencion.Numero,
            cliente_numero_de_documento=retencion.VendorRuc,
            cliente_denominacion=retencion.VendorName,
            cliente_direccion=retencion.VendorAddress or "",
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
        is_already_sent = False
        if not response.success and response.errors:
            for err in response.errors:
                err_lower = err.lower()
                if "ya fue enviado" in err_lower or "ya existe" in err_lower or "enviado anteriormente" in err_lower:
                    is_already_sent = True
                    break

        if response.success or is_already_sent:
            # Si NubeFact procesó con éxito (o ya fue enviado antes), se considera aceptado
            retencion.status = "aceptada"
            retencion.nube_status_web = "aceptado"
        else:
            retencion.status = "error"
            retencion.nube_status_web = "error"
        
        # Guardar respuesta (tanto exitosa como con errores)
        error_str = ", ".join(response.errors) if (response.errors and not is_already_sent) else None
        status_record = APRetencionStatus(
            Retencion=retencion.Id,
            Status="aceptada" if (response.aceptada_por_sunat or is_already_sent) else "rechazada" if response.success else "error",
            Pdf=response.enlace_del_pdf,
            Xml=response.enlace_del_xml,
            Cdr=response.enlace_del_cdr,
            Aceptacion=response.enlace,
            Descripcion=response.sunat_description or ("La retención ya fue enviada anteriormente" if is_already_sent else None),
            Nota=response.sunat_note,
            ResponseCode=response.sunat_responsecode,
            Soap=response.sunat_soap_error,
            error=error_str,
            XlastUser=usuario,
            XlastDate=now_peru(),
        )
        self.db.add(status_record)
        
        self.db.commit()
        
        # Notificar por WhatsApp
        notification_service = NotificationService(self.db)
        if not response.success and not is_already_sent:
            error_msg = ", ".join(response.errors) if response.errors else response.message
            await notification_service.notificar_error_documento(
                tipo_modulo="retenciones",
                tipo_documento="retencion",
                serie=retencion.Serie,
                numero=retencion.Numero,
                error=error_msg,
                documento_id=str(retencion.Id)
            )
        
        # Construir mensaje con errores si existen
        mensaje = response.message
        if response.errors:
            mensaje = response.message + ": " + ", ".join(response.errors)
            
        return {
            "success": response.success,
            "message": mensaje,
            "data": response.model_dump(exclude_none=True)
        }
    
    # ==================== DOCUMENTOS DE VENTA ====================
    
    async def enviar_documento_venta(self, document_id: str, usuario: str, es_masivo: bool = False) -> Dict[str, Any]:
        """Envía documento de venta llamando a las APIs PHP locales y verificando en la BD"""
        peru_now = now_peru()
        if not es_masivo:
            print(f"\n{'='*60}")
            print(f"ENVIO DOCUMENTO VENTA - ID: {document_id}")
            print(f"Fecha Perú: {peru_now.strftime('%d-%m-%Y %H:%M:%S')}")
            print(f"{'='*60}")
        
        documento = self.db.query(ARDocument).filter(
            ARDocument.Document == document_id,
            ~ARDocument.DocumentSerie.like('T%')
        ).first()
        
        if not documento:
            if not es_masivo:
                print(f"ERROR: Documento no encontrado o es un ticket")
            return {"success": False, "message": "Documento no encontrado o es un ticket (su serie inicia con T)"}
            
        if documento.Status == 'N':
            if not es_masivo:
                print(f"ERROR: Documento {document_id} está anulado en el sistema (Status = N)")
            return {"success": False, "message": "El documento está anulado en el sistema y no puede ser enviado"}
        
        # Validar si ya fue aceptado en el dashboard web o enviado
        if documento.nube_status_web == "aceptado" or (documento.fe == "enviado" and not es_masivo):
            if not es_masivo:
                print(f"ERROR: Documento ya fue enviado")
            return {"success": False, "message": "El documento ya fue enviado"}
        
        if documento.necesita_aprobacion:
            return {"success": False, "message": "El documento requiere aprobación del administrador antes de ser enviado"}
        
        # Determinar URL basada en typeDocSun
        type_doc_sun = (documento.typeDocSun or "").strip().upper()
        if type_doc_sun == 'T':
            url = f"http://192.168.1.3/sistemas/fe/enviov3.php?Doc={documento.Document}&doc={documento.Document}"
        else:
            # Por defecto, si es F o cualquier otro valor, se usa envf.php
            url = f"http://192.168.1.3/sistemas/fe/envf.php?Doc={documento.Document}&doc={documento.Document}"
            
        if not es_masivo:
            print(f"Llamando a API local: {url}")
            
        # Resetear el estado a 'pendiente' en la base de datos antes de llamar al PHP
        # Esto asegura que limpiemos estados anteriores ('error') y podamos leer el nuevo resultado correctamente
        documento.fe = "pendiente"
        documento.nube_status_web = "pendiente"
        self.db.commit() # Esto guarda el cambio de reset y además libera los bloqueos en SQL Server
            
        # Llamar a la API PHP local
        try:
            # Aumentamos el timeout a 60.0 segundos ya que el script de PHP puede tardar en responder al comunicarse con NubeFact/SUNAT
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.get(url)
                if not es_masivo:
                    print(f"Respuesta de la API local - Status: {response.status_code}")
                    print(f"Cuerpo de respuesta de la API local (primeros 500 caracteres): {response.text[:500]}")
        except Exception as e:
            if not es_masivo:
                import traceback
                print(f"Error o Timeout llamando a la API local: {type(e).__name__} - {e}")
                traceback.print_exc()

        # Esperar 1.5 segundos para dar tiempo al script PHP de terminar su ejecución
        await asyncio.sleep(1.5)
        
        # Cerrar la transacción de lectura actual para iniciar una nueva limpia y poder ver los cambios del PHP
        self.db.rollback()
        
        # Volver a obtener el documento
        documento = self.db.query(ARDocument).filter(ARDocument.Document == document_id).first()
        fe_status = (documento.fe or "").strip().lower() if documento else "pendiente"
        if not es_masivo:
            print(f"Estado fe en BD después del envío: {fe_status}")

        success = False
        mensaje = ""
        nube_data = {}

        if fe_status in ('enviado', 'aceptada'):
            success = True
            documento.fe = "enviado"  # Asegurar que esté marcado como enviado
            documento.nube_status_web = "aceptado"
            self.db.commit()
            
            # Buscar la respuesta insertada por la API local en ar_fe_nube
            nube_record = self.db.query(ARFENube).filter(
                ARFENube.serie == documento.DocumentSerie,
                ARFENube.numero == documento.DocumentNo
            ).order_by(ARFENube.id.desc()).first()
            
            if nube_record:
                nube_data = {
                    "enlace": nube_record.enlace,
                    "aceptada_por_sunat": nube_record.aceptada_por_sunat,
                    "sunat_description": nube_record.sunat_description,
                    "sunat_note": nube_record.sunat_note,
                    "sunat_responsecode": nube_record.sunat_responsecode,
                    "sunat_soap_error": nube_record.sunat_soap_error,
                    "pdf_zip_base64": nube_record.pdf_zip_base64,
                    "xml_zip_base64": nube_record.xml_zip_base64,
                    "cdr_zip_base64": nube_record.cdr_zip_base64,
                    "codigo_hash": nube_record.codigo_hash,
                }
                mensaje = nube_record.sunat_description or "El documento fue enviado y aceptado correctamente."
            else:
                mensaje = "Documento enviado correctamente."
            pass

        else:
            # error o se quedó pendiente
            success = False
            documento.fe = "error"
            documento.nube_status_web = "error"
            
            nube_record = self.db.query(ARFENube).filter(
                ARFENube.serie == documento.DocumentSerie,
                ARFENube.numero == documento.DocumentNo
            ).order_by(ARFENube.id.desc()).first()
            
            if not es_masivo:
                print(f"DEBUG: No se detectó éxito. Estado fe en BD: {fe_status}")
                if nube_record:
                    print(f"DEBUG: Registro encontrado en ar_fe_nube: id={nube_record.id}, error={nube_record.error}")
                else:
                    print(f"DEBUG: No se encontró ningún registro en ar_fe_nube para serie={documento.DocumentSerie}, numero={documento.DocumentNo}")
            
            if nube_record and nube_record.error:
                error_msg = nube_record.error
            elif fe_status == "error":
                error_msg = "Error reportado por el script de envío en la base de datos."
            else:
                error_msg = f"Tiempo de espera agotado sin actualización del estado de envío (estado fe: {fe_status})."
                
            documento.RejectionReason = error_msg
            self.db.commit()
            mensaje = error_msg

            # Notificar por WhatsApp de error
            try:
                notification_service = NotificationService(self.db)
                await notification_service.notificar_error_documento(
                    tipo_modulo="ventas",
                    tipo_documento=documento.DocumentType,
                    serie=documento.DocumentSerie,
                    numero=documento.DocumentNo,
                    error=error_msg,
                    documento_id=documento.Document
                )
            except Exception as ne:
                if not es_masivo:
                    print(f"Error al enviar notificación de error por WhatsApp: {ne}")

        if not es_masivo:
            print(f"{'='*60}\n")

        return {
            "success": success,
            "message": mensaje,
            "data": nube_data
        }
    
    def _map_unidad(self, unidad: str) -> str:
        """Mapea unidad de medida"""
        unidad_map = {
            "UND": "NIU",
            "PARES": "PR",
            "KG": "KG",
        }
        return unidad_map.get(unidad, "NIU")

    async def sync_sunat_statuses(self) -> Dict[str, Any]:
        """Sincroniza el estado de SUNAT de comprobantes y guías enviados en los últimos 7 días pero pendientes de aceptación"""
        from ..schemas.nubefact import NubeFactConsultRequest
        from datetime import datetime, timedelta
        
        limit_date = datetime.now() - timedelta(days=7)
        limit_timestamp = limit_date.timestamp()
        
        # 1. Ventas
        print("Sincronizando estado SUNAT de Ventas...")
        ventas_pendientes = self.db.query(ARFENube).filter(
            ARFENube.aceptada_por_sunat == 'false',
            ARFENube.fecha_envio >= limit_timestamp,
            ARFENube.error == None,
            ARFENube.sunat_soap_error == None
        ).all()
        
        ventas_actualizadas = 0
        ventas_rechazadas = 0
        
        for r in ventas_pendientes:
            # Buscar tipo de comprobante en ARDocument
            documento = self.db.query(ARDocument).filter(
                ARDocument.DocumentSerie == r.serie,
                ARDocument.DocumentNo == r.numero
            ).first()
            
            if not documento:
                continue
                
            doc_type_clean = (documento.DocumentType or "").replace(" ", "").upper()
            tipo_doc_map = {
                "LIMADSASFACTURA": 1,
                "LIMADSASBOLETA": 2,
                "LIMADSASCREDITO": 3,
                "LIMADSASDEBITO": 4,
            }
            tipo_comprobante = tipo_doc_map.get(doc_type_clean)
            if not tipo_comprobante:
                continue
                
            try:
                # Consultar a NubeFact
                consult_request = NubeFactConsultRequest(
                    tipo_de_comprobante=tipo_comprobante,
                    serie=r.serie,
                    numero=r.numero
                )
                response = await nubefact_client.consultar_comprobante(consult_request)
                
                if response.success:
                    if response.aceptada_por_sunat:
                        r.aceptada_por_sunat = "true"
                        r.enlace_del_pdf = response.enlace_del_pdf or r.enlace_del_pdf
                        r.enlace_del_xml = response.enlace_del_xml or r.enlace_del_xml
                        r.enlace_del_cdr = response.enlace_del_cdr or r.enlace_del_cdr
                        r.sunat_description = response.sunat_description or r.sunat_description
                        r.sunat_note = response.sunat_note or r.sunat_note
                        r.sunat_responsecode = response.sunat_responsecode or r.sunat_responsecode
                        r.pdf_zip_base64 = response.pdf_zip_base64 or r.pdf_zip_base64
                        r.xml_zip_base64 = response.xml_zip_base64 or r.xml_zip_base64
                        r.cdr_zip_base64 = response.cdr_zip_base64 or r.cdr_zip_base64
                        r.codigo_hash = response.codigo_hash or r.codigo_hash
                        
                        documento.fe = "aceptada"
                        documento.nube_status_web = "aceptado"
                        ventas_actualizadas += 1
                    
                    elif response.errors or (response.sunat_description and "rechazad" in response.sunat_description.lower()):
                        # Si fue rechazado por SUNAT
                        r.aceptada_por_sunat = "false"
                        r.error = ", ".join(response.errors) if response.errors else response.sunat_description
                        r.sunat_description = response.sunat_description or r.sunat_description
                        
                        # Actualizar estado a rechazado en el ERP
                        documento.fe = "rechazado"
                        documento.nube_status_web = "rechazado"
                        if response.errors:
                            documento.RejectionReason = ", ".join(response.errors)
                        elif response.sunat_description:
                            documento.RejectionReason = response.sunat_description
                            
                        # Notificar error por WhatsApp
                        try:
                            notification_service = NotificationService(self.db)
                            await notification_service.notificar_error_documento(
                                tipo_modulo="ventas",
                                tipo_documento=documento.DocumentType,
                                serie=documento.DocumentSerie,
                                numero=documento.DocumentNo,
                                error=r.error,
                                documento_id=documento.Document
                            )
                        except Exception as e:
                            print(f"Error al enviar notificación de rechazo de venta: {e}")
                            
                        ventas_rechazadas += 1
                
                # Esperar 0.5 segundos entre consultas
                import asyncio
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error consultando documento {r.serie}-{r.numero}: {e}")
                
        # 2. Guías
        print("Sincronizando estado SUNAT de Guías...")
        guias_pendientes = self.db.query(WHTransactionNube).filter(
            WHTransactionNube.aceptada_por_sunat == 'false',
            WHTransactionNube.fecha_envio >= limit_timestamp,
            WHTransactionNube.error == None,
            WHTransactionNube.sunat_soap_error == None
        ).all()
        
        guias_actualizadas = 0
        guias_rechazadas = 0
        
        for r in guias_pendientes:
            guia = self.db.query(WHTransaction).filter(
                WHTransaction.Transaction == r.TransactionId
            ).first()
            
            if not guia:
                continue
                
            try:
                # Consultar a NubeFact
                consult_request = NubeFactConsultRequest(
                    tipo_de_comprobante=7,
                    serie=r.serie,
                    numero=r.numero
                )
                response = await nubefact_client.consultar_guia(consult_request)
                
                if response.success:
                    if response.aceptada_por_sunat:
                        r.aceptada_por_sunat = "true"
                        r.enlace_del_pdf = response.enlace_del_pdf or r.enlace_del_pdf
                        r.enlace_del_xml = response.enlace_del_xml or r.enlace_del_xml
                        r.enlace_del_cdr = response.enlace_del_cdr or r.enlace_del_cdr
                        r.sunat_description = response.sunat_description or r.sunat_description
                        r.sunat_note = response.sunat_note or r.sunat_note
                        r.sunat_responsecode = response.sunat_responsecode or r.sunat_responsecode
                        r.pdf_zip_base64 = response.pdf_zip_base64 or r.pdf_zip_base64
                        r.xml_zip_base64 = response.xml_zip_base64 or r.xml_zip_base64
                        r.cdr_zip_base64 = response.cdr_zip_base64 or r.cdr_zip_base64
                        r.codigo_hash = response.codigo_hash or r.codigo_hash
                        
                        guia.envio_nube = "aceptada"
                        guia.nube_status_web = "aceptado"
                        guias_actualizadas += 1
                        
                    elif response.errors or (response.sunat_description and "rechazad" in response.sunat_description.lower()):
                        # Si fue rechazado por SUNAT
                        r.aceptada_por_sunat = "false"
                        r.error = ", ".join(response.errors) if response.errors else response.sunat_description
                        r.sunat_description = response.sunat_description or r.sunat_description
                        
                        guia.envio_nube = "rechazado"
                        guia.nube_status_web = "rechazado"
                        if response.errors:
                            guia.RejectionReason = ", ".join(response.errors)
                        elif response.sunat_description:
                            guia.RejectionReason = response.sunat_description
                            
                        # Notificar error por WhatsApp
                        try:
                            notification_service = NotificationService(self.db)
                            await notification_service.notificar_error_documento(
                                tipo_modulo="guias",
                                tipo_documento="guia",
                                serie=guia.DocumentSerie,
                                numero=guia.DocumentNo,
                                error=r.error,
                                documento_id=guia.Transaction
                            )
                        except Exception as e:
                            print(f"Error al enviar notificación de rechazo de guía: {e}")
                            
                        guias_rechazadas += 1
                        
                # Esperar 0.5 segundos entre consultas
                import asyncio
                await asyncio.sleep(0.5)
                
            except Exception as e:
                print(f"Error consultando guía {r.serie}-{r.numero}: {e}")
                
        self.db.commit()
        return {
            "ventas_actualizadas": ventas_actualizadas,
            "ventas_rechazadas": ventas_rechazadas,
            "guias_actualizadas": guias_actualizadas,
            "guias_rechazadas": guias_rechazadas
        }
