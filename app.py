import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
import re

# ---------------- CONFIG ----------------
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": login_url,
}

# ---------------- FUNCIONES ----------------
def login_and_get_defecto_iduunn(session, usuario, password):
    credentials = {
        "data[Usuario][usuario]": usuario,
        "data[Usuario][pass]": password
    }
    login_page = session.get(login_url, headers=headers)
    soup = BeautifulSoup(login_page.text, "html.parser")
    csrf_token = soup.find("input", {"name": "_csrf_token"})
    if csrf_token:
        credentials["_csrf_token"] = csrf_token["value"]

    response = session.post(login_url, data=credentials, headers=headers)
    match_iduunn = re.search(r"var DEFECTO_IDUUNN\s*=\s*'(\d+)'", response.text)
    if not match_iduunn:
        return None, False

    defecto_iduunn = int(match_iduunn.group(1))
    dashboard_response = session.get("http://sigof.distriluz.com.pe/plus/dashboard/modulos", headers=headers)
    if "login" in dashboard_response.text:
        return None, False

    return defecto_iduunn, True

def descargar_archivo(session, codigo):
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).strftime("%Y-%m-%d")    
    url = f"http://sigof.distriluz.com.pe/plus/ComrepOrdenrepartos/ajax_reporte_excel_ordenes_historico/U/0/{codigo}/0/0/{hoy}/{hoy}/0/"
    response = session.get(url, headers=headers)
    if response.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return BytesIO(response.content)
    else:
        return None

def procesar_excel(input_excel_bytes):
    df = pd.read_excel(input_excel_bytes)

    # Ajusta los nombres exactos según tu archivo real
    columnas_necesarias = ["Ciclo", "Sector", "Ruta", "Lecturista", "URL_Foto", "Suministro"]
    for col in columnas_necesarias:
        if col not in df.columns:
            st.error(f"❌ Falta la columna '{col}' en el Excel.")
            return None

    # Elimina filas sin URL válida
    df = df[df["URL_Foto"].notna() & (df["URL_Foto"].str.startswith("http"))]
    return df

# ---------------- STREAMLIT APP ----------------
st.set_page_config(page_title="Galería de Suministros", layout="centered")
st.title("📸 Galería de Fotos de Suministros - SIGOF")

if "session" not in st.session_state:
    st.session_state.session = None
if "df_fotos" not in st.session_state:
    st.session_state.df_fotos = pd.DataFrame()

# --- LOGIN ---
if st.session_state.session is None:
    usuario = st.text_input("👤 Usuario SIGOF", max_chars=30)
    password = st.text_input("🔒 Contraseña SIGOF", type="password", max_chars=20)

    if st.button("Iniciar sesión"):
        if not usuario or not password:
            st.warning("⚠️ Ingrese usuario y contraseña.")
        else:
            session = requests.Session()
            _, login_ok = login_and_get_defecto_iduunn(session, usuario, password)
            if not login_ok:
                st.error("❌ Usuario o contraseña incorrectos.")
            else:
                st.session_state.session = session
                st.success("✅ Login exitoso. Ahora seleccione un ciclo para ver fotos.")

# --- DESCARGA Y VISUALIZACIÓN ---
if st.session_state.session:
    ciclo_codigo = st.text_input("Ingrese el código del Ciclo:")
    if st.button("📥 Cargar fotos del ciclo"):
        if ciclo_codigo:
            contenido = descargar_archivo(st.session_state.session, ciclo_codigo)
            if contenido:
                df = procesar_excel(contenido)
                if df is not None:
                    st.session_state.df_fotos = df
                    st.success(f"✅ Se cargaron {len(df)} fotos.")
            else:
                st.error("⚠️ No se pudo descargar el archivo.")
        else:
            st.warning("⚠️ Ingrese el código del ciclo.")

# --- FILTROS Y GALERÍA ---
if not st.session_state.df_fotos.empty:
    df = st.session_state.df_fotos

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        filtro_ciclo = st.selectbox("Ciclo", ["Todos"] + sorted(df["Ciclo"].unique()))
    with col2:
        filtro_sector = st.selectbox("Sector", ["Todos"] + sorted(df["Sector"].unique()))
    with col3:
        filtro_ruta = st.selectbox("Ruta", ["Todos"] + sorted(df["Ruta"].unique()))
    with col4:
        filtro_lecturista = st.selectbox("Lecturista", ["Todos"] + sorted(df["Lecturista"].unique()))

    df_filtrado = df.copy()
    if filtro_ciclo != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Ciclo"] == filtro_ciclo]
    if filtro_sector != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Sector"] == filtro_sector]
    if filtro_ruta != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Ruta"] == filtro_ruta]
    if filtro_lecturista != "Todos":
        df_filtrado = df_filtrado[df_filtrado["Lecturista"] == filtro_lecturista]

    st.markdown(f"### Se encontraron {len(df_filtrado)} fotos 📷")

    for _, row in df_filtrado.iterrows():
        st.markdown(
            f"""
            <div style='text-align: center; margin-bottom: 15px;'>
                <img src="{row['URL_Foto']}" style='width: 250px; border-radius: 10px;'><br>
                <div style='font-weight: bold; font-size: 14px; margin-top: 5px; color: #007BFF;'>
                    Suministro: {row['Suministro']}
                </div>
            </div>
            """,
            unsafe_allow_html=True
        )
