"""
gmail_sender.py
----------------
Construye el correo de alarma y lo envía usando la Gmail API,
autenticado con las credenciales OAuth del usuario que inició sesión
(auth.py). No usa SMTP ni contraseñas.
"""

import base64
from email.mime.text import MIMEText

from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def _get_service(credentials: Credentials):
    return build("gmail", "v1", credentials=credentials)


def build_message(remitente: str, destinatario: str, asunto: str, cuerpo_html: str) -> dict:
    mensaje = MIMEText(cuerpo_html, "html")
    mensaje["to"] = destinatario
    mensaje["from"] = remitente
    mensaje["subject"] = asunto
    raw = base64.urlsafe_b64encode(mensaje.as_bytes()).decode()
    return {"raw": raw}


def send_alarm_email(credentials: Credentials, remitente: str, destinatario: str,
                      asunto: str, cuerpo_html: str) -> dict:
    """Envía un único correo. Lanza excepción si Gmail lo rechaza."""
    service = _get_service(credentials)
    message = build_message(remitente, destinatario, asunto, cuerpo_html)
    return service.users().messages().send(userId="me", body=message).execute()


def send_bulk(credentials: Credentials, remitente: str, destinatarios: list,
              asunto_template: str, cuerpo_template: str, contexto: dict) -> list:
    """
    Envía la alarma a una lista de profesores.
    destinatarios: lista de dicts {"nombre": ..., "correo": ...}
    Los templates pueden usar {nombre}, {periodo}, {unidad}, {fecha}, {modalidad}.
    Devuelve una lista de resultados (uno por profesor) con éxito/error.
    """
    resultados = []
    for prof in destinatarios:
        ctx = {**contexto, "nombre": prof.get("nombre", "")}
        asunto = asunto_template.format(**ctx)
        cuerpo = cuerpo_template.format(**ctx)
        try:
            send_alarm_email(credentials, remitente, prof["correo"], asunto, cuerpo)
            resultados.append({"correo": prof["correo"], "nombre": prof.get("nombre", ""),
                                "estado": "enviado", "detalle": ""})
        except Exception as e:
            resultados.append({"correo": prof["correo"], "nombre": prof.get("nombre", ""),
                                "estado": "error", "detalle": str(e)})
    return resultados
