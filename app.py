import pandas as pd
from io import BytesIO
import requests
from datetime import datetime
from zoneinfo import ZoneInfo

# CONFIG
headers = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "http://sigof.distriluz.com.pe/plus/usuario/login",
}

def descargar_archivo(session, codigo):
    """Descarga el archivo Excel desde SIGOF"""
    zona = ZoneInfo("America/Lima")
    hoy = datetime.now(zona).strftime("%Y-%m-%d")    
    url = f"http://sigof.distriluz.com.pe/plus/ComrepOrdenrepartos/ajax_reporte_excel_ordenes_historico/U/0/{codigo}/0/0/{hoy}/{hoy}/0/"
    response = session.get(url, headers=headers)

    if response.headers.get("Content-Type") == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
        return BytesIO(response.content), f"ciclo_{codigo}_{hoy}.xlsx"
    else:
        return None, None

def filtrar_y_concatenar(input_excel, output_excel="LmcSoloFotosReparto.xlsx"):
    """Filtra 'ver foto' en la columna Z y genera URLs en columna D"""
    # Cargar archivo original
    df = pd.read_excel(input_excel)

    # Verificar que tenga al menos 26 columnas (columna Z)
    if df.shape[1] < 26:
        raise ValueError("El archivo no tiene al menos 26 columnas (columna Z).")

    col_foto = df.columns[25]  # Columna Z (índice 25)
    
    # Filtrar filas con 'ver foto'
    df_filtrado = df[df[col_foto] == "ver foto"]

    if df_filtrado.empty:
        print("⚠️ No se encontraron filas con 'ver foto'.")
        return None

    # Tomar solo A, B, C
    df_final = df_filtrado.iloc[:, :3].copy()

    # Concatenación como en VBA (columna D)
    H1 = "https://d3jgwc2y5nosue.cloudfront.net/repartos/"
    J1 = "/"
    L1 = "/"
    N1 = "_"
    P1 = "_"
    R1 = ".png"

    urls = []
    for _, row in df_final.iterrows():
        col_a = str(row.iloc[0])  # Columna A
        col_b = str(row.iloc[1])  # Columna B
        col_c = str(row.iloc[2])  # Columna C

        if col_b.strip():
            primeros_dos = col_a[:2]
            url = f"{H1}{col_b}{J1}{primeros_dos}{L1}{col_b}{N1}{primeros_dos}{P1}{col_c}{R1}"
            urls.append(url)
        else:
            urls.append("")

    df_final["D"] = urls  # Columna D

    # Guardar en nuevo Excel
    df_final.to_excel(output_excel, index=False)
    print(f"✅ Archivo filtrado y URLs generadas en {output_excel}")
    return output_excel

# EJEMPLO DE USO
if __name__ == "__main__":
    session = requests.Session()
    # Aquí deberías loguearte primero con tu función login_and_get_defecto_iduunn()

    contenido, nombre_archivo = descargar_archivo(session, codigo="12345")
    if contenido:
        print(f"📥 Archivo descargado: {nombre_archivo}")
        filtrar_y_concatenar(contenido)
    else:
        print("❌ Error al descargar el archivo.")
