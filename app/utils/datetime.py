"""
Utilidades de fecha y hora con timezone de Perú (America/Lima)
"""
from datetime import datetime
from zoneinfo import ZoneInfo
from app.config import get_settings

# Timezone de Perú (UTC-5)
PERU_TZ = ZoneInfo(get_settings().timezone)


def now_peru() -> datetime:
    """
    Obtiene la fecha y hora actual en timezone de Perú.
    Usa esta función en lugar de datetime.now()
    """
    return datetime.now(PERU_TZ)


def to_peru_tz(dt: datetime) -> datetime:
    """
    Convierte un datetime a timezone de Perú.
    Si el datetime no tiene timezone, se asume UTC.
    """
    if dt.tzinfo is None:
        # Asumir UTC si no tiene timezone
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))
    return dt.astimezone(PERU_TZ)


def format_peru(dt: datetime, fmt: str = "%d/%m/%Y %H:%M:%S") -> str:
    """
    Formatea un datetime en timezone de Perú.
    """
    peru_dt = to_peru_tz(dt) if dt.tzinfo else dt
    return peru_dt.strftime(fmt)


def make_peru_aware(dt: datetime) -> datetime:
    """
    Hace un datetime naive aware de Perú.
    Útil para datetimes creados sin timezone.
    """
    if dt.tzinfo is not None:
        return dt
    return dt.replace(tzinfo=PERU_TZ)
