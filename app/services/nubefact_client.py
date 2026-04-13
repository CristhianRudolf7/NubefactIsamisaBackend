import httpx
import asyncio
from typing import Optional, Dict, Any
from ..config import get_settings
from ..schemas.nubefact import (
    NubeFactRequest,
    NubeFactResponse,
    NubeFactGuiaRequest,
    NubeFactRetencionRequest,
    NubeFactConsultRequest,
    NubeFactConsultAnulacionRequest,
)


class NubeFactClient:
    """Cliente HTTP para API de NubeFact"""
    
    def __init__(self):
        settings = get_settings()
        self.base_url = settings.nubefact_url
        self.token = settings.nubefact_token
        self.headers = {
            "Authorization": f"Token token=\"{self.token}\"",
            "Content-Type": "application/json",
        }
        self.timeout = 30.0  # SUNAT puede tardar ~3 segundos
    
    async def _send_request(self, data: Dict[str, Any]) -> NubeFactResponse:
        """Envía solicitud a NubeFact"""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    self.base_url,
                    headers=self.headers,
                    json=data
                )
                response_data = response.json()
                
                # Procesar respuesta
                if "errors" in response_data:
                    return NubeFactResponse(
                        success=False,
                        message="Error en NubeFact",
                        errors=response_data["errors"] if isinstance(response_data["errors"], list) else [response_data["errors"]]
                    )
                
                return NubeFactResponse(
                    success=True,
                    message="Comprobante procesado correctamente",
                    tipo_de_comprobante=response_data.get("tipo_de_comprobante"),
                    serie=response_data.get("serie"),
                    numero=response_data.get("numero"),
                    enlace=response_data.get("enlace"),
                    enlace_del_pdf=response_data.get("enlace_del_pdf"),
                    enlace_del_xml=response_data.get("enlace_del_xml"),
                    enlace_del_cdr=response_data.get("enlace_del_cdr"),
                    aceptada_por_sunat=response_data.get("aceptada_por_sunat"),
                    sunat_description=response_data.get("sunat_description"),
                    sunat_note=response_data.get("sunat_note"),
                    sunat_responsecode=response_data.get("sunat_responsecode"),
                    sunat_soap_error=response_data.get("sunat_soap_error"),
                    pdf_zip_base64=response_data.get("pdf_zip_base64"),
                    xml_zip_base64=response_data.get("xml_zip_base64"),
                    cdr_zip_base64=response_data.get("cdr_zip_base64"),
                    cadena_para_codigo_qr=response_data.get("cadena_para_codigo_qr"),
                    codigo_hash=response_data.get("codigo_hash"),
                )
            except httpx.TimeoutException:
                return NubeFactResponse(
                    success=False,
                    message="Timeout al conectar con NubeFact",
                    errors=["La solicitud tardó demasiado tiempo"]
                )
            except Exception as e:
                return NubeFactResponse(
                    success=False,
                    message="Error al conectar con NubeFact",
                    errors=[str(e)]
                )
    
    async def generar_comprobante(self, request: NubeFactRequest) -> NubeFactResponse:
        """Genera factura, boleta, nota de crédito o débito"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data)
    
    async def generar_guia(self, request: NubeFactGuiaRequest) -> NubeFactResponse:
        """Genera guía de remisión"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data)
    
    async def generar_retencion(self, request: NubeFactRetencionRequest) -> NubeFactResponse:
        """Genera comprobante de retención"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data)
    
    async def consultar_comprobante(self, request: NubeFactConsultRequest) -> NubeFactResponse:
        """Consulta estado de un CPE"""
        data = request.model_dump()
        return await self._send_request(data)
    
    async def consultar_anulacion(self, request: NubeFactConsultAnulacionRequest) -> NubeFactResponse:
        """Consulta estado de una anulación"""
        data = request.model_dump()
        return await self._send_request(data)
    
    async def generar_anulacion(self, tipo_comprobante: int, serie: str, numero: str, motivo: str = "") -> NubeFactResponse:
        """Genera anulación de comprobante"""
        data = {
            "operacion": "generar_anulacion",
            "tipo_de_comprobante": tipo_comprobante,
            "serie": serie,
            "numero": numero,
            "motivo": motivo or "Error en documento"
        }
        return await self._send_request(data)


# Instancia global del cliente
nubefact_client = NubeFactClient()
