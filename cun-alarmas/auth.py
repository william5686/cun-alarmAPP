"""
auth.py
--------
Maneja el login "solo con Google" (OAuth2, Authorization Code flow).
No se guarda ninguna contraseña: Google es quien valida al usuario.

Requiere que en Google Cloud Console exista un cliente OAuth tipo
"Aplicación web" con:
  - Un "Authorized redirect URI" IGUAL a la URL pública de esta app
    (la que da Streamlit Cloud, ej: https://cun-alarmas.streamlit.app)
  - Las APIs "Gmail API" y "People API" habilitadas.

Los scopes que se piden son el mínimo necesario:
  - gmail.send        -> para poder enviar el correo de alarma
  - userinfo.email     -> para saber con qué correo se autenticó
  - openid              -> requerido por el flujo OAuth de Google
"""

import streamlit as st
from google_auth_oauthlib.flow import Flow
from google.oauth2.credentials import Credentials
import requests

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/userinfo.email",
    "openid",
]


def _get_redirect_uri() -> str:
    """URL pública de la app. Se define en secrets.toml (app_url)."""
    return st.secrets["google_oauth"]["redirect_uri"]


def _build_flow() -> Flow:
    client_config = {
        "web": {
            "client_id": st.secrets["google_oauth"]["client_id"],
            "client_secret": st.secrets["google_oauth"]["client_secret"],
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [_get_redirect_uri()],
        }
    }
    flow = Flow.from_client_config(client_config, scopes=SCOPES)
    flow.redirect_uri = _get_redirect_uri()
    return flow


def get_login_url() -> str:
    """Genera la URL de Google a la que se manda al usuario para iniciar sesión."""
    flow = _build_flow()
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="select_account",
    )
    st.session_state["oauth_state"] = state
    # Google exige PKCE: el mismo code_verifier que se usó para armar la URL
    # de login se debe reutilizar al intercambiar el "code" por el token.
    # Como cada rerun de Streamlit crea un objeto Flow nuevo, hay que
    # guardarlo en session_state para no perderlo.
    st.session_state["code_verifier"] = flow.code_verifier
    return auth_url


def exchange_code_for_credentials(code: str) -> Credentials:
    """Cambia el 'code' que Google devuelve por un token utilizable."""
    flow = _build_flow()
    flow.code_verifier = st.session_state.get("code_verifier")
    flow.fetch_token(code=code)
    return flow.credentials


def get_user_email(credentials: Credentials) -> str:
    """Pregunta a Google con qué correo quedó autenticado el usuario."""
    resp = requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
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
        code = query_params["code"]
        try:
            credentials = exchange_code_for_credentials(code)
            email = get_user_email(credentials)
            st.session_state["credentials"] = credentials_to_dict(credentials)
            st.session_state["user_email"] = email
            st.query_params.clear()
            st.rerun()
        except Exception as e:
            st.error(f"No se pudo completar el inicio de sesión con Google: {e}")
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
    for key in ("credentials", "user_email", "oauth_state"):
        st.session_state.pop(key, None)
    st.rerun() 
