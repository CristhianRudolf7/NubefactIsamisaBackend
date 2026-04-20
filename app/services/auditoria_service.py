"""
Servicio para registrar eventos de auditoría
"""
from sqlalchemy.orm import Session
import json

from ..models.auditoria import Auditoria
from ..utils.datetime import now_peru


class AuditoriaService:
    """Servicio para gestionar registros de auditoría"""
    
    def __init__(self, db: Session):
        self.db = db
    
    def registrar(
        self,
        tabla: str,
        registro_id: str | int,
        accion: str,
        datos_anteriores: dict | None = None,
        datos_nuevos: dict | None = None,
        usuario: str | None = None,
        ip: str | None = None
    ) -> Auditoria:
        """
        Registra un evento de auditoría
        
        Args:
            tabla: Nombre de la tabla afectada (ventas, guias, retenciones, usuarios)
            registro_id: ID del registro afectado (string o int)
            accion: Tipo de acción (INSERT, UPDATE, DELETE, SEND, CANCEL)
            datos_anteriores: Datos antes del cambio (dict)
            datos_nuevos: Datos después del cambio (dict)
            usuario: Usuario que realizó la acción
            ip: Dirección IP del usuario
            
        Returns:
            Registro de auditoría creado
        """
        registro = Auditoria(
            tabla=tabla,
            registro_id=registro_id,
            accion=accion,
            datos_anteriores=json.dumps(datos_anteriores, default=str) if datos_anteriores else None,
            datos_nuevos=json.dumps(datos_nuevos, default=str) if datos_nuevos else None,
            usuario=usuario,
            fecha=now_peru(),
            ip=ip
        )
        
        self.db.add(registro)
        self.db.commit()
        self.db.refresh(registro)
        
        return registro
    
    def registrar_envio(
        self,
        tabla: str,
        registro_id: str | int,
        datos_documento: dict,
        usuario: str,
        respuesta_nubefact: dict | None = None,
        ip: str | None = None
    ) -> Auditoria:
        """Registra un envío a SUNAT"""
        datos_nuevos = {
            "documento": datos_documento,
            "respuesta_nubefact": respuesta_nubefact
        }
        return self.registrar(
            tabla=tabla,
            registro_id=registro_id,
            accion="SEND",
            datos_nuevos=datos_nuevos,
            usuario=usuario,
            ip=ip
        )
    
    def registrar_anulacion(
        self,
        tabla: str,
        registro_id: str | int,
        datos_anteriores: dict,
        motivo: str,
        usuario: str,
        respuesta_nubefact: dict | None = None,
        ip: str | None = None
    ) -> Auditoria:
        """Registra una anulación"""
        datos_nuevos = {
            "motivo": motivo,
            "respuesta_nubefact": respuesta_nubefact
        }
        return self.registrar(
            tabla=tabla,
            registro_id=registro_id,
            accion="CANCEL",
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            usuario=usuario,
            ip=ip
        )
    
    def registrar_cambio(
        self,
        tabla: str,
        registro_id: str | int,
        datos_anteriores: dict,
        datos_nuevos: dict,
        usuario: str,
        ip: str | None = None
    ) -> Auditoria:
        """Registra un cambio (UPDATE)"""
        return self.registrar(
            tabla=tabla,
            registro_id=registro_id,
            accion="UPDATE",
            datos_anteriores=datos_anteriores,
            datos_nuevos=datos_nuevos,
            usuario=usuario,
            ip=ip
        )
    
    def registrar_creacion(
        self,
        tabla: str,
        registro_id: str | int,
        datos_nuevos: dict,
        usuario: str,
        ip: str | None = None
    ) -> Auditoria:
        """Registra una creación (INSERT)"""
        return self.registrar(
            tabla=tabla,
            registro_id=registro_id,
            accion="INSERT",
            datos_nuevos=datos_nuevos,
            usuario=usuario,
            ip=ip
        )
    
    def registrar_eliminacion(
        self,
        tabla: str,
        registro_id: str | int,
        datos_anteriores: dict,
        usuario: str,
        ip: str | None = None
    ) -> Auditoria:
        """Registra una eliminación (DELETE)"""
        return self.registrar(
            tabla=tabla,
            registro_id=registro_id,
            accion="DELETE",
            datos_anteriores=datos_anteriores,
            usuario=usuario,
            ip=ip
        )


def get_auditoria_service(db: Session) -> AuditoriaService:
    """Dependency para obtener el servicio de auditoría"""
    return AuditoriaService(db)
