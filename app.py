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
FILE_ID = "1w8QdgVmttfyf5Oe0abfTFC1ijHVj6NQtEZb8UtzJKAY"  # ID del Excel en Google Drive
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

def filtrar_y_generar_df(input_excel_bytes):
    """Filtra 'ver foto' y genera URLs de las fotos."""
    df = pd.read_excel(input_excel_bytes)

    if df.shape[1] < 26:
        st.error("❌ El archivo no tiene la columna Z (26 columnas).")
        return None

    col_foto = df.columns[25]
    df_filtrado = df[df[col_foto] == "ver foto"]

    if df_filtrado.empty:
        st.warning("⚠️ No se encontraron filas con 'ver foto'.")
        return None

    df_final = df_filtrado.iloc[:, :3].copy()

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
    df_final.rename(columns={
        df_final.columns[0]: "Ciclo",
        df_final.columns[1]: "Sector",
        df_final.columns[2]: "Suministro"
    }, inplace=True)
    return df_final

# ---- APP STREAMLIT ----
def main():
    st.set_page_config(page_title="Lmc Reparto", layout="centered")
    st.title("🤖 Galería de Fotos SIGOF Reparto")

    if "session" not in st.session_state:
        st.session_state.session = None
    if "ciclos_df" not in st.session_state:
        st.session_state.ciclos_df = pd.DataFrame()
    if "fotos_df" not in st.session_state:
        st.session_state.fotos_df = pd.DataFrame()

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
                    df_ciclos = download_excel_from_drive(FILE_ID)
                    if df_ciclos is not None:
                        # Filtrar por unidad detectada en login
                        df_ciclos['id_unidad'] = pd.to_numeric(df_ciclos['id_unidad'], errors='coerce').fillna(-1).astype(int)
                        df_ciclos = df_ciclos[df_ciclos['id_unidad'] == defecto_iduunn]
                        st.session_state.ciclos_df = df_ciclos
                        st.session_state.session = session
                        st.success("✅ Login exitoso. Ahora seleccione ciclo y sector.")

    # FILTRO CICLO → SECTOR
    if not st.session_state.ciclos_df.empty:
        ciclos_unicos = sorted(st.session_state.ciclos_df['Id_ciclo'].unique().tolist())
        ciclo_seleccionado = st.selectbox("Seleccione ciclo", options=ciclos_unicos)

        if ciclo_seleccionado:
            df_filtrado_ciclo = st.session_state.ciclos_df[st.session_state.ciclos_df['Id_ciclo'] == ciclo_seleccionado]
            sectores_unicos = sorted(df_filtrado_ciclo['sector'].dropna().unique().tolist())
            sectores_seleccionados = st.multiselect("Seleccione sectores", options=sectores_unicos)

            if st.button("📷 Mostrar Fotos"):
                if not sectores_seleccionados:
                    st.warning("⚠️ Seleccione al menos un sector.")
                else:
                    all_df = []
                    contenido = descargar_archivo(st.session_state.session, ciclo_seleccionado)
                    if contenido:
                        df_fotos = filtrar_y_generar_df(contenido)
                        if df_fotos is not None:
                            df_fotos = df_fotos[df_fotos['Sector'].isin(sectores_seleccionados)]
                            all_df.append(df_fotos)
                    else:
                        st.warning(f"⚠️ Error al descargar ciclo {ciclo_seleccionado}")

                    if all_df:
                        st.session_state.fotos_df = pd.concat(all_df, ignore_index=True)

    # Mostrar galería si existe
    if not st.session_state.fotos_df.empty:
        st.subheader(f"Se encontraron {len(st.session_state.fotos_df)} fotos")
        cols = st.columns(4)  # 4 imágenes por fila
        for i, fila in st.session_state.fotos_df.iterrows():
            col = cols[i % 4]
            if fila["URL_Foto"]:
                col.image(fila["URL_Foto"], caption=f"Suministro: {fila['Suministro']}", use_container_width=True)

if __name__ == "__main__":
    main()
