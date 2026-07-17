"""
app.py
-------
CUN · Sistema de Alarmas de Cierre de Notas

Flujo:
  1) El profesor/coordinador inicia sesión con su cuenta de Google de CUN
     (auth.py) -- desde ese correo se enviará la alarma.
  2) Elige modalidad (Presencial / Virtual).
  3) Elige el periodo (2026A..D o 26P01..26P06).
  4) Elige el Corte (presencial) o Bloque (virtual) -- la app ya sabe
     la fecha de cierre de notas para esa combinación.
  5) Puede modificar la fecha propuesta si lo necesita.
  6) Carga (o usa la ya guardada en el repo) la lista de profesores a alertar.
  7) Revisa/edita el mensaje y lo envía desde su propio Gmail.
"""

import streamlit as st
from datetime import date, timedelta

import auth
import calendar_data as cal
import profesores as prof_mod
import gmail_sender

st.set_page_config(page_title="CUN · Alarmas de cierre de notas", page_icon="🔔", layout="centered")

st.title("🔔 CUN · Alarmas de cierre de notas")

# ---------------------------------------------------------------------
# 1) LOGIN
# ---------------------------------------------------------------------
if not auth.do_login_flow():
    st.stop()

user_email = st.session_state["user_email"]
credentials = auth.dict_to_credentials(st.session_state["credentials"])

col_a, col_b = st.columns([4, 1])
with col_a:
    st.success(f"Sesión iniciada como **{user_email}** — las alarmas se enviarán desde este correo.")
with col_b:
    if st.button("Cerrar sesión"):
        auth.logout()

st.divider()

# ---------------------------------------------------------------------
# 2) MODALIDAD -> PERIODO -> UNIDAD
# ---------------------------------------------------------------------
calendars = cal.load_calendars()

st.subheader("1. Selecciona el periodo académico")

modalidad_label = st.radio("Modalidad", ["Presencial", "Virtual"], horizontal=True)
modalidad = "presencial" if modalidad_label == "Presencial" else "virtual"

periodo = st.selectbox("Periodo", cal.periodos(modalidad, calendars))

etiqueta = cal.etiqueta_unidad(modalidad)
unidad = st.selectbox(f"{etiqueta} (cierre de notas)", cal.unidades(modalidad, periodo, calendars))

fecha_sugerida = cal.fecha_cierre(modalidad, periodo, unidad, calendars)

st.caption(
    f"Según el calendario oficial, el cierre de **{unidad}** de **{periodo}** ({modalidad_label}) "
    f"es el **{fecha_sugerida.strftime('%d/%m/%Y')}**."
)

st.subheader("2. Confirma cuándo se debe enviar la alarma")
dias_antes = st.slider(
    "¿Con cuántos días de anticipación al cierre quieres que se muestre esta alarma?",
    min_value=0, max_value=15, value=3
)
fecha_alarma_sugerida = fecha_sugerida - timedelta(days=dias_antes)

fecha_alarma = st.date_input(
    "Fecha de envío de la alarma (puedes modificarla)",
    value=fecha_alarma_sugerida
)

st.divider()

# ---------------------------------------------------------------------
# 3) LISTA DE PROFESORES
# ---------------------------------------------------------------------
st.subheader("3. Profesores a notificar")

st.write(
    "Se usa por defecto el archivo `data/profesores.xlsx` del repositorio. "
    "Si necesitas usar otra lista solo para este envío, súbela aquí abajo "
    "(para que quede permanente, reemplaza el archivo en GitHub)."
)

archivo_subido = st.file_uploader("Excel de profesores (columnas: nombre, correo)", type=["xlsx"])

try:
    if archivo_subido is not None:
        df_profes = prof_mod.leer_profesores(archivo_subido)
    else:
        df_profes = prof_mod.cargar_profesores_por_defecto()
except ValueError as e:
    st.error(str(e))
    st.stop()

if df_profes.empty:
    st.warning(
        "No hay profesores cargados todavía. Sube un Excel con columnas "
        "'nombre' y 'correo', o agrega `data/profesores.xlsx` al repositorio."
    )
    st.stop()

st.dataframe(df_profes, use_container_width=True, hide_index=True)

opciones = [f"{r.nombre} <{r.correo}>" for r in df_profes.itertuples()]
seleccion = st.multiselect("¿A quién se les envía esta alarma?", opciones, default=opciones)

destinatarios = []
for etiqueta_sel in seleccion:
    idx = opciones.index(etiqueta_sel)
    fila = df_profes.iloc[idx]
    destinatarios.append({"nombre": fila["nombre"], "correo": fila["correo"]})

st.divider()

# ---------------------------------------------------------------------
# 4) MENSAJE
# ---------------------------------------------------------------------
st.subheader("4. Mensaje de la alarma")

asunto_default = "⚠️ Alarma cierre de notas — {periodo} {unidad} ({modalidad})"
cuerpo_default = (
    "<p>Hola {nombre},</p>"
    "<p>Este es un recordatorio automático del sistema de alarmas de CUN:</p>"
    "<p><b>Periodo:</b> {periodo} ({modalidad})<br>"
    "<b>{unidad}</b><br>"
    "<b>Fecha límite de cierre de notas:</b> {fecha_cierre}</p>"
    "<p>Por favor asegúrate de tener las notas cargadas en Campus Digital "
    "antes de esa fecha.</p>"
    "<p>Este mensaje fue enviado el {fecha_envio} desde {remitente}.</p>"
)

asunto_template = st.text_input("Asunto", value=asunto_default)
cuerpo_template = st.text_area("Cuerpo del correo (HTML permitido)", value=cuerpo_default, height=220)

contexto = {
    "periodo": periodo,
    "unidad": unidad,
    "modalidad": modalidad_label,
    "fecha_cierre": fecha_sugerida.strftime("%d/%m/%Y"),
    "fecha_envio": date.today().strftime("%d/%m/%Y"),
    "remitente": user_email,
}

with st.expander("Vista previa del correo"):
    ejemplo_nombre = destinatarios[0]["nombre"] if destinatarios else "Profesor"
    st.markdown(f"**Asunto:** {asunto_template.format(**{**contexto, 'nombre': ejemplo_nombre})}")
    st.markdown(cuerpo_template.format(**{**contexto, "nombre": ejemplo_nombre}), unsafe_allow_html=True)

st.info(
    f"Esta alarma quedará marcada para el **{fecha_alarma.strftime('%d/%m/%Y')}**. "
    "Streamlit no envía correos en segundo plano por sí solo: para enviarla ese día, "
    "alguien debe entrar a la app y presionar 'Enviar alarma ahora' (o puedes automatizar "
    "el envío con GitHub Actions -- ver README)."
)

st.divider()

# ---------------------------------------------------------------------
# 5) ENVÍO
# ---------------------------------------------------------------------
st.subheader("5. Enviar")

if st.button(f"📤 Enviar alarma ahora a {len(destinatarios)} profesor(es)", type="primary"):
    with st.spinner("Enviando correos..."):
        resultados = gmail_sender.send_bulk(
            credentials=credentials,
            remitente=user_email,
            destinatarios=destinatarios,
            asunto_template=asunto_template,
            cuerpo_template=cuerpo_template,
            contexto=contexto,
        )

    exitosos = [r for r in resultados if r["estado"] == "enviado"]
    fallidos = [r for r in resultados if r["estado"] == "error"]

    if exitosos:
        st.success(f"Enviado correctamente a {len(exitosos)} profesor(es).")
    if fallidos:
        st.error(f"Falló el envío a {len(fallidos)} profesor(es):")
        st.table(fallidos)
