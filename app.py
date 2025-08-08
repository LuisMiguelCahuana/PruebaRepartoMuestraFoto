import streamlit as st
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from zoneinfo import ZoneInfo
import pandas as pd
from io import BytesIO
import re

# CONFIG
login_url = "http://sigof.distriluz.com.pe/plus/usuario/login"
FILE_ID = "1w8QdgVmttfyf5Oe0abfTFC1ijHVj6NQtEZb8UtzJKAY"
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": login_url,
}

# ---- FUNCIONES ----
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

def download_excel_from_drive(file_id):
    url = f"https://docs.google.com/spreadsheets/d/{file_id}/export?format=xlsx"
    response = requests.get(url)
    return pd.read_excel(BytesIO(response.content)) if response.status_code == 200 else None

def descargar_archivo(session, codigo):
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).strftime("%Y-%m-%d")    
    url = f"http://sigof.distriluz.com.pe/plus/ComrepOrdenrepartos/ajax_reporte_excel_ordenes_historico/U/0/{codigo}/0/0/{hoy}/{hoy}/0/"
    response = session.get(url, headers=headers)
    if response.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return BytesIO(response.content)
    else:
        return None

def procesar_y_generar_urls(input_excel_bytes):
    """Filtra 'ver foto' y agrega URL_Foto y Suministro"""
    df = pd.read_excel(input_excel_bytes)

    if df.shape[1] < 26:
        st.error("❌ El archivo no tiene la columna Z (26 columnas).")
        return None

    col_foto = df.columns[25]
    df_filtrado = df[df[col_foto] == "ver foto"]

    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron filas con 'ver foto'.")
        return None

    df_final = df_filtrado.copy()

    # Generar URLs
    H1 = "https://d3jgwc2y5nosue.cloudfront.net/repartos/"
    J1 = "/"
    L1 = "/"
    N1 = "_"
    P1 = "_"
    R1 = ".png"

    urls = []
    for _, row in df_final.iterrows():
        col_a = str(row.iloc[0])
        col_b = str(row.iloc[1])
        col_c = str(row.iloc[2])
        if col_b.strip():
            primeros_dos = col_a[:2]
            url = f"{H1}{col_b}{J1}{primeros_dos}{L1}{col_b}{N1}{primeros_dos}{P1}{col_c}{R1}"
            urls.append(url)
        else:
            urls.append("")
    df_final["URL_Foto"] = urls
    df_final.rename(columns={df_final.columns[1]: "Suministro"}, inplace=True)

    return df_final

# ---- APP STREAMLIT ----
def main():
    st.set_page_config(page_title="Lmc Reparto", layout="wide")
    st.title("📷 Visor de Fotos de Reparto")

    if "session" not in st.session_state:
        st.session_state.session = None
    if "ciclos_disponibles" not in st.session_state:
        st.session_state.ciclos_disponibles = {}
    if "data_fotos" not in st.session_state:
        st.session_state.data_fotos = pd.DataFrame()

    # LOGIN
    if st.session_state.session is None:
        usuario = st.text_input("👤 Usuario SIGOF", max_chars=30)
        password = st.text_input("🔒 Contraseña SIGOF", type="password", max_chars=20)

        if st.button("Iniciar sesión"):
            if not usuario or not password:
                st.warning("⚠️ Ingrese usuario y contraseña.")
            else:
                session = requests.Session()
                defecto_iduunn, login_ok = login_and_get_defecto_iduunn(session, usuario, password)
                if not login_ok:
                    st.error("❌ Login fallido.")
                else:
                    st.session_state.session = session
                    df_ciclos = download_excel_from_drive(FILE_ID)
                    if df_ciclos is not None:
                        df_ciclos['id_unidad'] = pd.to_numeric(df_ciclos['id_unidad'], errors='coerce').fillna(-1).astype(int)
                        df_ciclos = df_ciclos[df_ciclos['id_unidad'] == defecto_iduunn]
                        st.session_state.ciclos_disponibles = {
                            f"{row['Id_ciclo']} {row['nombre_ciclo']}": str(row['Id_ciclo'])
                            for _, row in df_ciclos.iterrows()
                        }
                        st.success("✅ Login exitoso. Seleccione ciclos para ver fotos.")

    # DESCARGA Y PROCESO
    if st.session_state.ciclos_disponibles:
        opciones = list(st.session_state.ciclos_disponibles.keys())
        seleccionados = st.multiselect("Seleccione ciclos", options=opciones)

        if st.button("📥 Cargar Fotos"):
            if not seleccionados:
                st.warning("⚠️ Seleccione al menos un ciclo.")
            else:
                lista_df = []
                for nombre in seleccionados:
                    codigo = st.session_state.ciclos_disponibles[nombre]
                    contenido = descargar_archivo(st.session_state.session, codigo)
                    if contenido:
                        df_fotos = procesar_y_generar_urls(contenido)
                        if df_fotos is not None:
                            lista_df.append(df_fotos)
                if lista_df:
                    st.session_state.data_fotos = pd.concat(lista_df, ignore_index=True)

    # FILTROS Y VISUALIZACIÓN
    if not st.session_state.data_fotos.empty:
        df = st.session_state.data_fotos
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            ciclo_f = st.multiselect("Ciclo", sorted(df["Ciclo"].dropna().unique()))
        with col2:
            sector_f = st.multiselect("Sector", sorted(df["Sector"].dropna().unique()))
        with col3:
            ruta_f = st.multiselect("Ruta", sorted(df["Ruta"].dropna().unique()))
        with col4:
            lecturista_f = st.multiselect("Lecturista", sorted(df["Lecturista"].dropna().unique()))

        if ciclo_f:
            df = df[df["Ciclo"].isin(ciclo_f)]
        if sector_f:
            df = df[df["Sector"].isin(sector_f)]
        if ruta_f:
            df = df[df["Ruta"].isin(ruta_f)]
        if lecturista_f:
            df = df[df["Lecturista"].isin(lecturista_f)]

        # Mostrar imágenes
        for _, row in df.iterrows():
            st.image(row["URL_Foto"], caption=f"Suministro: {row['Suministro']}", use_container_width=True)

if __name__ == "__main__":
    main()
