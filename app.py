import streamlit as st
import pandas as pd
import requests
from io import BytesIO

# ======== CONFIGURACIÓN LOGIN =========
USUARIO = "admin"       # tu usuario
PASSWORD = "1234"       # tu contraseña

# ======== FUNCIÓN DE LOGIN =========
def login():
    st.title("🔐 Iniciar sesión")
    usuario = st.text_input("Usuario")
    password = st.text_input("Contraseña", type="password")
    if st.button("Ingresar"):
        if usuario == USUARIO and password == PASSWORD:
            st.session_state["autenticado"] = True
            st.experimental_rerun()
        else:
            st.error("❌ Usuario o contraseña incorrectos")

# ======== FUNCIÓN PARA GENERAR URL_Foto =========
def generar_urls(df):
    base_url = "https://d3jgwc2y5nosue.cloudfront.net/repartos/"
    urls = []
    for _, row in df.iterrows():
        if pd.notna(row["suministro"]) and pd.notna(row["idciclo"]) and pd.notna(row["ruta"]):
            primeros_dos = str(row["idciclo"])[:2]
            url = f"{base_url}{row['suministro']}/{primeros_dos}/{row['suministro']}_{primeros_dos}_{row['ruta']}.png"
            urls.append(url)
        else:
            urls.append(None)
    df["URL_Foto"] = urls
    return df

# ======== FUNCIÓN PRINCIPAL =========
def app():
    st.title("📸 Visualizador de Fotos por Filtros")

    # Cargar el archivo Excel (simulación de descarga)
    excel_url = "URL_O_RUTA_DEL_EXCEL"  # Reemplazar con tu ruta real
    response = requests.get(excel_url)
    df = pd.read_excel(BytesIO(response.content))

    # Verificar columnas necesarias
    columnas_necesarias = {"idciclo", "sector", "ruta", "lecturista", "suministro"}
    if not columnas_necesarias.issubset(df.columns):
        st.error(f"❌ El archivo Excel debe contener las columnas: {', '.join(columnas_necesarias)}")
        return

    # Generar URLs
    df = generar_urls(df)

    # Filtros
    ciclos = sorted(df["idciclo"].dropna().unique())
    sectores = sorted(df["sector"].dropna().unique())
    rutas = sorted(df["ruta"].dropna().unique())
    lecturistas = sorted(df["lecturista"].dropna().unique())

    ciclo_sel = st.selectbox("Seleccione Ciclo", ["Todos"] + list(ciclos))
    sector_sel = st.selectbox("Seleccione Sector", ["Todos"] + list(sectores))
    ruta_sel = st.selectbox("Seleccione Ruta", ["Todos"] + list(rutas))
    lecturista_sel = st.selectbox("Seleccione Lecturista", ["Todos"] + list(lecturistas))

    # Aplicar filtros
    df_filtrado = df.copy()
    if ciclo_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["idciclo"] == ciclo_sel]
    if sector_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["sector"] == sector_sel]
    if ruta_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["ruta"] == ruta_sel]
    if lecturista_sel != "Todos":
        df_filtrado = df_filtrado[df_filtrado["lecturista"] == lecturista_sel]

    # Mostrar imágenes
    st.subheader(f"Se encontraron {len(df_filtrado)} registros")
    for _, row in df_filtrado.iterrows():
        if pd.notna(row["URL_Foto"]):
            st.image(row["URL_Foto"], caption=f"Suministro: {row['suministro']}", use_column_width=True)

# ======== FLUJO PRINCIPAL =========
if "autenticado" not in st.session_state:
    st.session_state["autenticado"] = False

if not st.session_state["autenticado"]:
    login()
else:
    app()
