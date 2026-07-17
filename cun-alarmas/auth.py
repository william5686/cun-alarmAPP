"""
auth.py
--------
Maneja el login "solo con Google" (OAuth2, Authorization Code + PKCE).
No se guarda ninguna contraseña: Google es quien valida al usuario.

Implementación MANUAL (sin google_auth_oauthlib.Flow):
Cuando Google redirige de vuelta a la app, el navegador hace una petición
HTTP totalmente nueva -> Streamlit puede arrancar una sesión nueva y
perder cualquier dato guardado en st.session_state entre el paso 1
(generar la URL de login) y el paso 2 (recibir el "code"). Por eso el
code_verifier de PKCE no se guarda en session_state: viaja escondido
dentro del parámetro "state", que Google sí devuelve intacto.

Requiere que en Google Cloud Console exista un cliente OAuth tipo
"Aplicación web" con:
  - Un "Authorized redirect URI" IGUAL a la URL pública de esta app
    (ej: https://cun-alarmapp-xxxx.streamlit.app)
  - La "Gmail API" habilitada.
"""

import base64
import hashlib
import secrets

import requests
import streamlit as st
from google.oauth2.credentials import Credentials

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]

AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"
USERINFO_ENDPOINT = "https://www.googleapis.com/oauth2/v2/userinfo"


def _client_id() -> str:
    return st.secrets["google_oauth"]["client_id"]


def _client_secret() -> str:
    return st.secrets["google_oauth"]["client_secret"]


def _redirect_uri() -> str:
    return st.secrets["google_oauth"]["redirect_uri"]


def _new_code_verifier() -> str:
    """String aleatorio de 43-128 caracteres, como pide PKCE (RFC 7636)."""
    return secrets.token_urlsafe(64)[:128]


def _code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def get_login_url() -> str:
    """
    Arma la URL de Google para iniciar sesión. El code_verifier se manda
    como "state" para poder recuperarlo cuando Google redirija de vuelta,
    sin depender de que Streamlit conserve la sesión.
    """
    code_verifier = _new_code_verifier()
    params = {
        "client_id": _client_id(),
        "redirect_uri": _redirect_uri(),
        "response_type": "code",
        "scope": " ".join(SCOPES),
        "access_type": "offline",
        "prompt": "select_account",
        "include_granted_scopes": "true",
        "code_challenge": _code_challenge(code_verifier),
        "code_challenge_method": "S256",
        "state": code_verifier,
    }
    query = "&".join(f"{k}={requests.utils.quote(v, safe='')}" for k, v in params.items())
    return f"{AUTH_ENDPOINT}?{query}"


def exchange_code_for_credentials(code: str, code_verifier: str) -> Credentials:
    """Cambia el 'code' que Google devuelve por un token utilizable."""
    resp = requests.post(
        TOKEN_ENDPOINT,
        data={
            "code": code,
            "client_id": _client_id(),
            "client_secret": _client_secret(),
            "redirect_uri": _redirect_uri(),
            "grant_type": "authorization_code",
            "code_verifier": code_verifier,
        },
        timeout=15,
    )
    if not resp.ok:
        raise RuntimeError(f"Google respondió {resp.status_code}: {resp.text}")
    data = resp.json()
    return Credentials(
        token=data["access_token"],
        refresh_token=data.get("refresh_token"),
        token_uri=TOKEN_ENDPOINT,
        client_id=_client_id(),
        client_secret=_client_secret(),
        scopes=SCOPES,
    )


def get_user_email(credentials: Credentials) -> str:
    """Pregunta a Google con qué correo quedó autenticado el usuario."""
    resp = requests.get(
        USERINFO_ENDPOINT,
        headers={"Authorization": f"Bearer {credentials.token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json().get("email", "")


def credentials_to_dict(credentials: Credentials) -> dict:
    return {
        "token": credentials.token,
        "refresh_token": credentials.refresh_token,
        "token_uri": credentials.token_uri,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "scopes": credentials.scopes,
    }


def dict_to_credentials(data: dict) -> Credentials:
    return Credentials(**data)


def do_login_flow():
    """
    Controla el ciclo completo de login dentro de la página principal de Streamlit.
    Devuelve True si el usuario ya quedó autenticado (y deja todo en session_state).
    """
    if "credentials" in st.session_state:
        return True

    query_params = st.query_params
    if "code" in query_params:
        code = query_params.get("code", "")
        code_verifier = query_params.get("state", "")

        # --- DIAGNÓSTICO TEMPORAL: quitar una vez funcione el login ---
        with st.expander("🔧 Diagnóstico (temporal)", expanded=True):
            st.write("Parámetros recibidos de Google:")
            st.write({k: query_params.get(k) for k in query_params.keys()})
            st.write(f"code presente: {bool(code)} (largo: {len(code)})")
            st.write(f"state/code_verifier presente: {bool(code_verifier)} (largo: {len(code_verifier)})")
        # ---------------------------------------------------------------

        if not code_verifier:
            st.error(
                "No llegó el parámetro 'state' (code_verifier) en la redirección de Google. "
                "Revisa el diagnóstico de arriba."
            )
            return False

        try:
            credentials = exchange_code_for_credentials(code, code_verifier)
            email = get_user_email(credentials)
            st.session_state["credentials"] = credentials_to_dict(credentials)
            st.session_state["user_email"] = email
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo completar el inicio de sesión con Google: {e}")
            st.query_params.clear()
        return False

    st.markdown("### Inicia sesión con tu correo de Google de CUN")
    st.write(
        "El envío de la alarma se hará **desde la cuenta con la que inicies sesión aquí**. "
        "No se guarda ninguna contraseña: la validación la hace Google."
    )
    login_url = get_login_url()
    st.link_button("🔐 Iniciar sesión con Google", login_url, use_container_width=True)
    return False


def logout():
    for key in ("credentials", "user_email"):
        st.session_state.pop(key, None)
    st.rerun()
