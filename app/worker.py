import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session
from .database import SessionLocal
from .services.document_service import DocumentService
from .models.ventas import ARDocument
from .models.guias import WHTransaction
from .models.retenciones import APRetencion
from .models.config import ConfiguracionEnvio
from .config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

class DocumentWorker:
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    async def check_and_send_pending_documents(self):
        """Busca y envía documentos pendientes de forma automática"""
        if self.is_running:
            logger.info("Worker ya está en ejecución, saltando ciclo")
            return

        self.is_running = True
        db = SessionLocal()
        try:
            service = DocumentService(db)
            
            # Obtener configuraciones
            configs = {c.tipo_documento: c for c in db.query(ConfiguracionEnvio).all()}
            
            # 1. Procesar Ventas
            conf_ventas = configs.get('ventas')
            if conf_ventas and conf_ventas.modo == 'automatico' and conf_ventas.activo:
                ventas_pendientes = db.query(ARDocument).filter(
                    ARDocument.fe.in_(['', 'pendiente', None]),
                    ARDocument.Status == '1'
                ).all()
                
                if ventas_pendientes:
                    logger.info(f"Worker: Detectadas {len(ventas_pendientes)} ventas pendientes")
                    for doc in ventas_pendientes:
                        try:
                            await service.enviar_documento_venta(doc.Document, "SISTEMA_AUTO")
                            # Pequeño delay para no saturar
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"Error procesando venta {doc.Document}: {e}")

            # 2. Procesar Guías
            conf_guias = configs.get('guias')
            if conf_guias and conf_guias.modo == 'automatico' and conf_guias.activo:
                guias_pendientes = db.query(WHTransaction).filter(
                    WHTransaction.envio_nube.in_(['', 'pendiente', None]),
                    WHTransaction.Status == '1'
                ).all()
                
                if guias_pendientes:
                    logger.info(f"Worker: Detectadas {len(guias_pendientes)} guías pendientes")
                    for guia in guias_pendientes:
                        try:
                            await service.enviar_guia(guia.Transaction, "SISTEMA_AUTO")
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"Error procesando guía {guia.Transaction}: {e}")

            # 3. Procesar Retenciones
            conf_ret = configs.get('retenciones')
            if conf_ret and conf_ret.modo == 'automatico' and conf_ret.activo:
                retenciones_pendientes = db.query(APRetencion).filter(
                    APRetencion.status.in_(['', 'pendiente', None])
                ).all()
                
                if retenciones_pendientes:
                    logger.info(f"Worker: Detectadas {len(retenciones_pendientes)} retenciones pendientes")
                    for ret in retenciones_pendientes:
                        try:
                            await service.enviar_retencion(ret.Id, "SISTEMA_AUTO")
                            await asyncio.sleep(1)
                        except Exception as e:
                            logger.error(f"Error procesando retención {ret.Id}: {e}")

        except Exception as e:
            logger.error(f"Error crítico en DocumentWorker: {e}")
        finally:
            db.close()
            self.is_running = False

    def start(self):
        if not settings.auto_send_enabled:
            logger.info("Worker automático desactivado por configuración")
            return

        logger.info(f"Iniciando DocumentWorker (intervalo: {settings.auto_send_interval_seconds}s)")
        self.scheduler.add_job(
            self.check_and_send_pending_documents,
            "interval",
            seconds=settings.auto_send_interval_seconds,
            id="check_pending_docs"
        )
        self.scheduler.start()

    def stop(self):
        logger.info("Deteniendo DocumentWorker")
        self.scheduler.shutdown()

worker = DocumentWorker()
