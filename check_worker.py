
import sys
import os

# Add the backend directory to sys.path
sys.path.append('/home/Rudy/proyectos/isamisa_nubefact/backend')

from app.database import SessionLocal
from app.models.config import ConfiguracionEnvio
from app.models.retenciones import APRetencion
from app.config import get_settings

def check_status():
    db = SessionLocal()
    settings = get_settings()
    
    print(f"AUTO_SEND_ENABLED (settings): {settings.auto_send_enabled}")
    print(f"AUTO_SEND_INTERVAL (settings): {settings.auto_send_interval_seconds}")
    
    configs = db.query(ConfiguracionEnvio).all()
    print("\n--- Configuraciones en DB (sy_configuracion_envio) ---")
    for c in configs:
        print(f"Tipo: {c.tipo_documento}, Modo: {c.modo}, Activo: {c.activo}, Intervalo: {c.intervalo_segundos}")
    
    pending_ret = db.query(APRetencion).filter(
        APRetencion.status.in_(['', 'pendiente', None])
    ).all()
    
    print(f"\n--- Retenciones Pendientes: {len(pending_ret)} ---")
    for r in pending_ret[:5]:
        print(f"ID: {r.Id}, Serie-Num: {r.Serie}-{r.Numero}, Status: {r.status}")
    
    db.close()

if __name__ == "__main__":
    check_status()
