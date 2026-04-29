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
        self.settings = get_settings()
        self.timeout = 30.0  # SUNAT puede tardar ~3 segundos
    
    def _get_headers(self, token: str) -> Dict[str, str]:
        """Genera headers con el token dinámico"""
        return {
            "Authorization": f"Token token=\"{token}\"",
            "Content-Type": "application/json",
        }
    
    async def _send_request(self, data: Dict[str, Any], url: str, token: str) -> NubeFactResponse:
        """Envía solicitud a NubeFact"""
        print(f"\n--- NUBEFACT CLIENT ---")
        print(f"URL: {url}")
        print(f"Data enviada: {data}")
        
        headers = self._get_headers(token)
        
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            try:
                response = await client.post(
                    url,
                    headers=headers,
                    json=data
                )
                print(f"Status code: {response.status_code}")
                print(f"Response raw: {response.text[:500] if len(response.text) > 500 else response.text}")
                
                response_data = response.json()
                
                # Procesar respuesta
                if "errors" in response_data:
                    print(f"ERRORES de NubeFact: {response_data['errors']}")
                    return NubeFactResponse(
                        success=False,
                        message="Error en NubeFact",
                        errors=response_data["errors"] if isinstance(response_data["errors"], list) else [response_data["errors"]]
                    )
                
                print(f"Respuesta exitosa de NubeFact")
                return NubeFactResponse(
                    success=True,
                    message="Comprobante procesado correctamente",
                    tipo_de_comprobante=response_data.get("tipo_de_comprobante"),
                    serie=str(response_data.get("serie", "")),
                    numero=str(response_data.get("numero", "")),
                    enlace=response_data.get("enlace"),
                    enlace_del_pdf=response_data.get("enlace_del_pdf"),
                    enlace_del_xml=response_data.get("enlace_del_xml"),
                    enlace_del_cdr=response_data.get("enlace_del_cdr"),
                    aceptada_por_sunat=response_data.get("aceptada_por_sunat"),
                    sunat_description=response_data.get("sunat_description"),
                    sunat_note=response_data.get("sunat_note"),
                    sunat_responsecode=str(response_data.get("sunat_responsecode", "")) if response_data.get("sunat_responsecode") else None,
                    sunat_soap_error=response_data.get("sunat_soap_error"),
                    pdf_zip_base64=response_data.get("pdf_zip_base64"),
                    xml_zip_base64=response_data.get("xml_zip_base64"),
                    cdr_zip_base64=response_data.get("cdr_zip_base64"),
                    cadena_para_codigo_qr=response_data.get("cadena_para_codigo_qr"),
                    codigo_hash=response_data.get("codigo_hash"),
                )
            except httpx.TimeoutException as e:
                print(f"TIMEOUT: {e}")
                return NubeFactResponse(
                    success=False,
                    message="Timeout al conectar con NubeFact",
                    errors=["La solicitud tardó demasiado tiempo"]
                )
            except Exception as e:
                print(f"EXCEPCION en _send_request: {type(e).__name__}: {e}")
                return NubeFactResponse(
                    success=False,
                    message="Error al conectar con NubeFact",
                    errors=[str(e)]
                )
    
    async def generar_comprobante(self, request: NubeFactRequest) -> NubeFactResponse:
        """Genera factura, boleta, nota de crédito o débito (Ventas)"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data, self.settings.nubefact_url_ventas, self.settings.nubefact_token_ventas)
    
    async def generar_guia(self, request: NubeFactGuiaRequest) -> NubeFactResponse:
        """Genera guía de remisión"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data, self.settings.nubefact_url_guias, self.settings.nubefact_token_guias)
    
    async def generar_retencion(self, request: NubeFactRetencionRequest) -> NubeFactResponse:
        """Genera comprobante de retención"""
        data = request.model_dump(exclude_none=True)
        return await self._send_request(data, self.settings.nubefact_url_retenciones, self.settings.nubefact_token_retenciones)
    
    async def consultar_comprobante(self, request: NubeFactConsultRequest) -> NubeFactResponse:
        """Consulta estado de un CPE (Ventas)"""
        data = request.model_dump()
        return await self._send_request(data, self.settings.nubefact_url_ventas, self.settings.nubefact_token_ventas)
    
    async def consultar_guia(self, request: NubeFactConsultRequest) -> NubeFactResponse:
        """Consulta estado de una guía de remisión"""
        data = request.model_dump()
        data["operacion"] = "consultar_guia"
        return await self._send_request(data, self.settings.nubefact_url_guias, self.settings.nubefact_token_guias)
    
    async def consultar_anulacion(self, request: NubeFactConsultAnulacionRequest) -> NubeFactResponse:
        """Consulta estado de una anulación (Ventas)"""
        data = request.model_dump()
        return await self._send_request(data, self.settings.nubefact_url_ventas, self.settings.nubefact_token_ventas)
    
    async def generar_anulacion(self, tipo_comprobante: int, serie: str, numero: str, motivo: str = "") -> NubeFactResponse:
        """Genera anulación de comprobante (Ventas)"""
        data = {
            "operacion": "generar_anulacion",
            "tipo_de_comprobante": tipo_comprobante,
            "serie": serie,
            "numero": numero,
            "motivo": motivo or "Error en documento"
        }
        return await self._send_request(data, self.settings.nubefact_url_ventas, self.settings.nubefact_token_ventas)


# Instancia global del cliente
nubefact_client = NubeFactClient()
