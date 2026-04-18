import httpx
import asyncio
from typing import Optional
from ..config import get_settings


class WhatsAppService:
    """Cliente para enviar notificaciones por WhatsApp"""
    
    def __init__(self):
        settings = get_settings()
        self.api_url = settings.whatsapp_api_url
        self.timeout = settings.whatsapp_timeout
    
    async def enviar_mensaje(self, telefono: str, mensaje: str) -> bool:
        """
        Envía un mensaje de WhatsApp a un número específico.
        
        Args:
            telefono: Número de teléfono con código de país (ej: +51923356855)
            mensaje: Contenido del mensaje a enviar
            
        Returns:
            True si se envió correctamente, False si hubo error
        """
        # Asegurar formato del teléfono con código de país
        if not telefono.startswith("+"):
            telefono = f"+51{telefono}"
        
        payload = {
            "telefono": telefono,
            "mensaje": mensaje
        }
        
        print(f"\n--- WHATSAPP SERVICE ---")
        print(f"Enviando a: {telefono}")
        print(f"Mensaje: {mensaje[:100]}...")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout, verify=False) as client:
                response = await client.post(
                    self.api_url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                print(f"Status: {response.status_code}")
                
                if response.status_code == 200:
                    print(f"WhatsApp enviado exitosamente a {telefono}")
                    return True
                else:
                    print(f"Error enviando WhatsApp: {response.status_code} - {response.text}")
                    return False
                    
        except httpx.TimeoutException:
            print(f"Timeout enviando WhatsApp a {telefono}")
            return False
        except Exception as e:
            print(f"Excepción enviando WhatsApp a {telefono}: {type(e).__name__}: {e}")
            return False
    
    async def enviar_mensaje_multiple(self, destinatarios: list[tuple[str, str]]) -> list[bool]:
        """
        Envía el mismo mensaje a múltiples destinatarios en paralelo.
        
        Args:
            destinatarios: Lista de tuplas (telefono, mensaje)
            
        Returns:
            Lista de resultados (True/False por cada destinatario)
        """
        tasks = [
            self.enviar_mensaje(telefono, mensaje) 
            for telefono, mensaje in destinatarios
        ]
        return await asyncio.gather(*tasks)


# Instancia global del servicio
whatsapp_service = WhatsAppService()
