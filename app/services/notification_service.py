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
        Construye el mensaje de error formateado.

        Args:
            tipo_documento: Tipo de documento (Factura, Boleta, etc.)
            serie: Serie del documento
            numero: Número del documento
            error: Mensaje de error
            tipo_modulo: Módulo al que pertenece (ventas, guias, retenciones)
            documento_id: ID del documento para link de edición

        Returns:
            Mensaje formateado para WhatsApp
        """
        settings = get_settings()
        portal_url = settings.portal_url.rstrip("/")
        
        return f"""Tipo de documento: {tipo_documento}
Serie-número: {serie}-{numero}
Error: {error}
Link para corrección: {portal_url}/{tipo_modulo}/{documento_id}/editar"""
    
    async def notificar_error_documento(
        self,
        tipo_modulo: str,
        tipo_documento: Optional[str],
        serie: str,
        numero: str,
        error: str,
        documento_id: str
    ) -> dict:
        """
        Notifica a los usuarios correspondientes sobre un error en documento.

        Args:
            tipo_modulo: 'ventas', 'guias' o 'retenciones'
            tipo_documento: Tipo específico (ej: LIMADSASFACTURA)
            serie: Serie del documento
            numero: Número del documento
            error: Mensaje de error
            documento_id: ID del documento para link de edición

        Returns:
            Diccionario con resultado del envío
        """
        # Obtener usuarios a notificar
        usuarios = self._obtener_usuarios_a_notificar(tipo_modulo)
        
        if not usuarios:
            print(f"No hay usuarios configurados para recibir notificaciones de {tipo_modulo}")
            return {
                "success": False,
                "message": "No hay usuarios configurados para recibir notificaciones",
                "enviados": 0
            }
        
        # Mapear tipo de documento a nombre legible
        tipo_map = self.TIPO_DOCUMENTO_MAP.get(tipo_modulo, {})
        tipo_legible = tipo_map.get(tipo_documento, tipo_documento or "Documento")
        
        # Construir mensaje
        mensaje = self._construir_mensaje_error(tipo_legible, serie, numero, error, tipo_modulo, documento_id)
        
        # Preparar destinatarios (filtrar usuarios sin celular)
        destinatarios = []
        for usuario in usuarios:
            if usuario.celular:
                destinatarios.append((usuario.celular, mensaje))
        
        if not destinatarios:
            print(f"Los usuarios no tienen número de celular configurado")
            return {
                "success": False,
                "message": "Los usuarios no tienen número de celular configurado",
                "enviados": 0
            }
        
        # Enviar notificaciones en paralelo
        print(f"\n=== NOTIFICANDO ERROR A {len(destinatarios)} USUARIOS ===")
        resultados = await whatsapp_service.enviar_mensaje_multiple(destinatarios)
        
        enviados = sum(1 for r in resultados if r)
        fallidos = len(resultados) - enviados
        
        return {
            "success": enviados > 0,
            "message": f"Enviados: {enviados}, Fallidos: {fallidos}",
            "enviados": enviados,
            "fallidos": fallidos
        }
