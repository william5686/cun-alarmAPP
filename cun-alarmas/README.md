# CUN · Sistema de Alarmas de Cierre de Notas

App en Streamlit para que los compañeros de CUN envíen, desde su propio
correo de Google, una alarma por email a los profesores encargados,
recordando la fecha de **cierre de notas** de un periodo/bloque/corte
específico (ej. `26P03 Bloque 2`, `2026C Tercer Corte`).

## ¿Cómo funciona?

1. El usuario inicia sesión con su cuenta de Google de CUN (sin escribir
   ninguna contraseña dentro de la app — Google es quien valida).
2. Elige **modalidad** → **periodo** → **corte/bloque**. La app ya conoce
   la fecha oficial de cierre de notas de cada combinación (calendars.json,
   extraído de los calendarios oficiales 2026A-D presencial y
   26P01-26P06 virtual).
3. Puede ajustar la fecha en la que se debe mandar el aviso.
4. Carga (o usa la del repo) la lista de profesores: `data/profesores.xlsx`
   con columnas `nombre` y `correo`.
5. Revisa/edita el asunto y el cuerpo del correo y presiona **Enviar**.
   El correo sale desde la cuenta de Google con la que inició sesión.

## 1. Configurar el login de Google (una sola vez, lo hace un admin de CUN)

1. Entra a [Google Cloud Console](https://console.cloud.google.com/) con
   la cuenta corporativa (o crea un proyecto nuevo para esta app).
2. **APIs & Services → Library**: habilita:
   - `Gmail API`
3. **APIs & Services → OAuth consent screen**:
   - Tipo: *Internal* si todos los usuarios son del dominio `@cun.edu.co`
     (recomendado, así no hay que pedir revisión a Google), o *External*
     con los correos de prueba agregados si aún no está verificada.
   - Agrega el scope `https://www.googleapis.com/auth/gmail.send`.
4. **APIs & Services → Credentials → Create Credentials → OAuth client ID**:
   - Tipo de aplicación: **Web application**.
   - En *Authorized redirect URIs* agrega la URL pública que te va a dar
     Streamlit Cloud, por ejemplo `https://cun-alarmas.streamlit.app`
     (sin `/` al final).
   - Guarda el **Client ID** y el **Client Secret**.

## 2. Subir el proyecto a GitHub

```bash
cd cun-alarmas
git init
git add .
git commit -m "App de alarmas de cierre de notas"
git branch -M main
git remote add origin https://github.com/TU-USUARIO/cun-alarmas.git
git push -u origin main
```

> El archivo `.streamlit/secrets.toml` **nunca se sube** (está en
> `.gitignore`). Las credenciales van solo en Streamlit Cloud (paso 4).

## 3. Cargar la lista real de profesores

Reemplaza `data/profesores.xlsx` (ya viene con una plantilla y una fila
de ejemplo) por la lista real, con columnas `nombre` y `correo`, y sube
el cambio a GitHub:

```bash
git add data/profesores.xlsx
git commit -m "Actualiza lista de profesores"
git push
```

Cada vez que cambie la lista de profesores, se repite este paso.

## 4. Desplegar en Streamlit Community Cloud

1. Entra a [share.streamlit.io](https://share.streamlit.io) y conecta tu
   repositorio de GitHub.
2. Selecciona el repo `cun-alarmas`, archivo principal `app.py`.
3. Antes de darle "Deploy" (o después, en *Settings → Secrets*), pega:

   ```toml
   [google_oauth]
   client_id = "TU_CLIENT_ID.apps.googleusercontent.com"
   client_secret = "TU_CLIENT_SECRET"
   redirect_uri = "https://cun-alarmas.streamlit.app"
   ```

   (usa la URL real que Streamlit te asigne).
4. Si cambiaste la URL, actualiza también el *Authorized redirect URI*
   en Google Cloud Console para que coincidan exactamente.

## Sobre el envío en una fecha futura

Streamlit no mantiene procesos corriendo en segundo plano: la alarma se
envía en el momento en que alguien abre la app y presiona **"Enviar
alarma ahora"**, no automáticamente en la fecha elegida. La app deja
claro en pantalla cuál es la fecha objetivo, para que el equipo sepa
cuándo entrar a dispararla.

Si más adelante quieren automatizar el envío exacto en la fecha (sin que
nadie tenga que entrar), la forma recomendada es agregar un script aparte
que use este mismo `gmail_sender.py` y correrlo con **GitHub Actions**
(`schedule` con cron) usando un *refresh token* guardado como *secret* del
repo — no está incluido en esta primera versión porque implica guardar un
token de larga duración fuera de la sesión del usuario.

## Estructura del proyecto

```
cun-alarmas/
├── app.py               # Interfaz Streamlit (el asistente paso a paso)
├── auth.py               # Login con Google (OAuth2)
├── gmail_sender.py       # Envío de correos vía Gmail API
├── calendar_data.py      # Lectura de calendars.json
├── profesores.py         # Lectura del Excel de profesores
├── calendars.json        # Fechas de cierre de notas (todos los periodos)
├── data/
│   └── profesores.xlsx   # Lista de profesores (nombre, correo)
├── .streamlit/
│   └── secrets.toml.example
├── requirements.txt
└── .gitignore
```

## Periodos incluidos

- **Presencial**: 2026A, 2026B, 2026C, 2026D — cada uno con Primer,
  Segundo y Tercer Corte.
- **Virtual**: 26P01 a 26P06 — cada uno con Primer y Segundo Bloque.

Si sale un calendario nuevo, solo hay que agregar su bloque correspondiente
en `calendars.json` (mismo formato) y hacer `git push`.
