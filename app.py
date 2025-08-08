import streamlit as st
import requests
from bs4 import BeautifulSoup
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

# ---- APP STREAMLIT ----
def main():
    st.set_page_config(page_title="Lmc Reparto", layout="centered")
    st.title("🤖 Galería de Fotos SIGOF Reparto")

    if "session" not in st.session_state:
        st.session_state.session = None
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
                _, login_ok = login_and_get_defecto_iduunn(session, usuario, password)
                if not login_ok:
                    st.error("❌ Login fallido.")
                else:
                    st.session_state.session = session
                    df_fotos = download_excel_from_drive(FILE_ID)
                    if df_fotos is not None:
                        st.session_state.fotos_df = df_fotos
                        st.success("✅ Datos cargados desde Excel.")

    # Mostrar galería si existe
    if not st.session_state.fotos_df.empty:
        st.subheader(f"Se encontraron {len(st.session_state.fotos_df)} fotos")
        cols = st.columns(4)  # 4 imágenes por fila
        for i, fila in st.session_state.fotos_df.iterrows():
            if "URL_Foto" in fila and pd.notna(fila["URL_Foto"]):
                col = cols[i % 4]
                col.image(fila["URL_Foto"], caption=f"Suministro: {fila['Suministro']}", use_container_width=True)

if __name__ == "__main__":
    main()
