"""
Utilidades para manejo de requests
"""
from fastapi import Request


def get_client_ip(request: Request) -> str | None:
    """
    Obtiene la IP del cliente desde el request.
    
    Considera headers de proxy como X-Forwarded-For y X-Real-IP
    para casos donde la app está detrás de un proxy/reverse proxy.
    """
    # Intentar obtener IP de headers de proxy
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        # X-Forwarded-For puede contener múltiples IPs, la primera es la del cliente
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    
    # Si no hay headers de proxy, usar la IP directa del cliente
    if request.client:
        return request.client.host
    
    return None
