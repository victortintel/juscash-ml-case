import json
import requests
from .settings import settings

def notify_flow(event: str, payload: dict) -> None:
    """
    Envia um POST para o webhook do n8n com {event, payload}.
    Se não houver URL configurada, não faz nada.
    """
    if not settings.N8N_WEBHOOK_URL:
        return
    try:
        requests.post(settings.N8N_WEBHOOK_URL, json={"event": event, "payload": payload}, timeout=5)
    except Exception:
        # Mantemos a API resiliente mesmo se o n8n cair
        pass
