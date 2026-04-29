from sqlalchemy.orm import Session
from typing import List, Optional
from .whatsapp_service import whatsapp_service
from ..models.user import User, UserRole
from ..config import get_settings


class NotificationService:
    """Servicio para gestionar notificaciones de errores"""
    
    TIPO_DOCUMENTO_MAP = {
        "ventas": {
            "LIMADSASFACTURA": "Factura",
            "LIMADSASBOLETA": "Boleta", 
            "LIMADSASCREDITO": "Nota de Crédito",
            "LIMADSASDEBITO": "Nota de Débito",
        },
        "guias": {
            "guia": "Guía de Remisión",
        },
        "retenciones": {
            "retencion": "Comprobante de Retención",
        }
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def _obtener_usuarios_a_notificar(self, tipo_modulo: str) -> List[User]:
        """
        Obtiene lista de usuarios que deben recibir notificación.
        
        Args:
            tipo_modulo: 'ventas', 'guias' o 'retenciones'
            
        Returns:
            Lista de usuarios a notificar
        """
        # Obtener todos los admins con notificaciones activadas
        admins = self.db.query(User).filter(
            User.rol == UserRole.ADMIN,
            User.is_active == True,
            User.recibir_notificaciones == True
        ).all()
        
        # Obtener trabajadores con permiso específico y notificaciones activadas
        trabajadores = []
        if tipo_modulo == "ventas":
            trabajadores = self.db.query(User).filter(
                User.rol == UserRole.TRABAJADOR,
                User.is_active == True,
                User.recibir_notificaciones == True,
                User.puede_acceder_ventas == True
            ).all()
        elif tipo_modulo == "guias":
            trabajadores = self.db.query(User).filter(
                User.rol == UserRole.TRABAJADOR,
                User.is_active == True,
                User.recibir_notificaciones == True,
                User.puede_acceder_guias == True
            ).all()
        elif tipo_modulo == "retenciones":
            trabajadores = self.db.query(User).filter(
                User.rol == UserRole.TRABAJADOR,
                User.is_active == True,
                User.recibir_notificaciones == True,
                User.puede_acceder_retenciones == True
            ).all()
        
        # Combinar y eliminar duplicados
        todos_usuarios = {u.id: u for u in admins + trabajadores}
        return list(todos_usuarios.values())
    
    def _construir_mensaje_error(
        self, 
        tipo_documento: str,
        serie: str,
        numero: str,
        error: str,
        tipo_modulo: str,
        documento_id: str
    ) -> str:
        """
        Construye el mensaje de error formateado para WhatsApp.
        """
        settings = get_settings()
        portal_url = settings.portal_url.rstrip("/")
        
        return f"""*🚨 ERROR EN DOCUMENTO*

*Tipo:* {tipo_documento}
*Serie-Número:* {serie}-{numero}
*Error:* {error}

*Solución:*
Para corregir, haz clic en el siguiente enlace:
{portal_url}/{tipo_modulo}/{documento_id}/editar"""
    
    async def notificar_error_documento(
        self,
        tipo_modulo: str,
        tipo_documento: Optional[str],
        serie: str,
        numero: str,
        error: str,
        documento_id: str
    ) -> dict:
        """Notifica sobre un error en documento"""
        tipo_map = self.TIPO_DOCUMENTO_MAP.get(tipo_modulo, {})
        tipo_legible = tipo_map.get(tipo_documento, tipo_documento or "Documento")
        mensaje = self._construir_mensaje_error(tipo_legible, serie, numero, error, tipo_modulo, documento_id)
        return await self._enviar_a_usuarios(tipo_modulo, mensaje)

    async def notificar_edicion_documento(
        self,
        tipo_modulo: str,
        tipo_documento: Optional[str],
        serie: str,
        numero: str,
        usuario: str,
        documento_id: str
    ) -> dict:
        """Notifica que un documento ha sido editado"""
        tipo_map = self.TIPO_DOCUMENTO_MAP.get(tipo_modulo, {})
        tipo_legible = tipo_map.get(tipo_documento, tipo_documento or "Documento")
        mensaje = self._construir_mensaje_edicion(tipo_legible, serie, numero, usuario, tipo_modulo, documento_id)
        return await self._enviar_a_usuarios(tipo_modulo, mensaje)

    async def notificar_envio_exitoso(
        self,
        tipo_modulo: str,
        tipo_documento: Optional[str],
        serie: str,
        numero: str,
        mensaje_sunat: str
    ) -> dict:
        """Notifica que un documento fue aceptado por SUNAT"""
        tipo_map = self.TIPO_DOCUMENTO_MAP.get(tipo_modulo, {})
        tipo_legible = tipo_map.get(tipo_documento, tipo_documento or "Documento")
        mensaje = self._construir_mensaje_exito(tipo_legible, serie, numero, mensaje_sunat)
        return await self._enviar_a_usuarios(tipo_modulo, mensaje)

    async def _enviar_a_usuarios(self, tipo_modulo: str, mensaje: str) -> dict:
        """Método interno para enviar mensaje a todos los destinatarios pertinentes"""
        usuarios = self._obtener_usuarios_a_notificar(tipo_modulo)
        if not usuarios:
            return {"success": False, "message": "No hay usuarios a notificar", "enviados": 0}

        destinatarios = [(u.celular, mensaje) for u in usuarios if u.celular]
        if not destinatarios:
            return {"success": False, "message": "Usuarios sin celular", "enviados": 0}

        resultados = await whatsapp_service.enviar_mensaje_multiple(destinatarios)
        enviados = sum(1 for r in resultados if r)
        return {"success": enviados > 0, "enviados": enviados}

    def _construir_mensaje_edicion(self, tipo_doc, serie, numero, usuario, tipo_modulo, doc_id):
        settings = get_settings()
        portal_url = settings.portal_url.rstrip("/")
        return f"""*📝 DOCUMENTO EDITADO*

*Tipo:* {tipo_doc}
*Serie-Número:* {serie}-{numero}
*Editado por:* {usuario}

*Estado:* El documento ha sido corregido. Puede intentar el envío nuevamente.
{portal_url}/{tipo_modulo}/{doc_id}/editar"""

    def _construir_mensaje_exito(self, tipo_doc, serie, numero, mensaje_sunat):
        return f"""*✅ DOCUMENTO ACEPTADO*

*Tipo:* {tipo_doc}
*Serie-Número:* {serie}-{numero}
*SUNAT:* {mensaje_sunat or 'Aceptado correctamente'}

El documento ha sido procesado exitosamente."""
