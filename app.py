import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import urllib.parse

# --- CONFIGURACIÓN DE GOOGLE SHEETS ---
SHEET_ID = "1kBLQAdhYbnP8HTUgpr_rmmGEaOdyMU2tI97ogegrGxY"
SHEET_NAME = "Incorporaciones"

# --- AUTENTICACIÓN GOOGLE SHEETS ---
scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
credentials = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
gc = gspread.authorize(credentials)
worksheet = gc.open_by_key(SHEET_ID).worksheet(SHEET_NAME)

# --- FUNCIONES DE UTILIDAD ---
def cargar_datos():
    return pd.DataFrame(worksheet.get_all_records())

def guardar_datos(df):
    worksheet.clear()
    worksheet.update([df.columns.values.tolist()] + df.values.tolist())

def autenticar(usuario, contraseña):
    admin_df = gc.open_by_key(SHEET_ID).worksheet("ADMIN").get_all_records()
    credenciales = pd.DataFrame(admin_df)
    return not credenciales[
        (credenciales["Usuario"] == usuario) & (credenciales["Password"] == contraseña)
    ].empty

def cargar_basicos():
    try:
        basicos_df = gc.open_by_key(SHEET_ID).worksheet("Basicos").get_all_records()
        return sorted([row["Básicos"] for row in basicos_df if row["Básicos"]])
    except:
        return []

def cargar_ciudades():
    try:
        ciudades_df = gc.open_by_key(SHEET_ID).worksheet("Ciudades").get_all_records()
        return sorted([row["Ciudad"] for row in ciudades_df if row["Ciudad"]])
    except:
        return []

def generar_tabla_html(df, basico, fecha_texto, bus):
    html = "<table style='width:100%; border-collapse: collapse;'>"
    html += "<thead><tr style='background-color:#f0f0f0;'>"
    for col in ["Ciudad", "Nombre de Guía", "Correo EMV", "Correo Personal", "📧 Enviar Correo"]:
        html += f"<th style='border:1px solid #ddd; padding:8px;'>{col}</th>"
    html += "</tr></thead><tbody>"

    for _, row in df.iterrows():
        asunto = f"Incorporaciones - {row['Ciudad']} - {basico} {fecha_texto} - Bus {bus}".strip()
        asunto_encoded = urllib.parse.quote(asunto)
        correos = row["Correo EMV"]
        if row["Correo Personal"]:
            correos += f",{row['Correo Personal']}"
        link = f"<a href='mailto:{correos}?subject={asunto_encoded}'>📧 Enviar</a>"

        html += "<tr>"
        html += f"<td style='border:1px solid #ddd; padding:8px;'>{row['Ciudad']}</td>"
        html += f"<td style='border:1px solid #ddd; padding:8px;'>{row['Nombre de Guía']}</td>"
        html += f"<td style='border:1px solid #ddd; padding:8px;'>{row['Correo EMV']}</td>"
        html += f"<td style='border:1px solid #ddd; padding:8px;'>{row['Correo Personal'] or '-'}</td>"
        html += f"<td style='border:1px solid #ddd; padding:8px;'>{link}</td>"
        html += "</tr>"
    html += "</tbody></table>"
    return html

# --- ESTADO DE SESIÓN ---
if "login_autorizado" not in st.session_state:
    st.session_state["login_autorizado"] = False
if "forzar_rerun" not in st.session_state:
    st.session_state["forzar_rerun"] = False

# --- NAVEGACIÓN ---
pagina = st.sidebar.radio("Selecciona una opción:", ["📄 Visualización", "🛠️ Administración"])
st.session_state["pagina_actual"] = pagina

# --- REINICIO SEGURO TRAS OPERACIÓN ---
if st.session_state["forzar_rerun"]:
    st.session_state["forzar_rerun"] = False
    if st.session_state.get("pagina_actual") == "🛠️ Administración":
        st.experimental_rerun()

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Guías Incorporaciones", layout="wide")
st.title("📋 Guías - Incorporaciones de Pasajeros")

# --- VISUALIZACIÓN PÚBLICA ---
if pagina == "📄 Visualización":
    st.subheader("Listado de Guías por Ciudad")

    basicos = cargar_basicos()
    if not basicos:
        st.error("No se pudieron cargar los Básicos desde la hoja 'Basicos'.")
    else:
        basico = st.selectbox("Selecciona el Básico del viaje", basicos)
        fecha_texto = st.text_input("Fecha del viaje (formato: DD/MM)")
        bus = st.text_input("Bus (Ejemplo: 1)")

        df = cargar_datos()
        if df.empty:
            st.warning("No hay datos disponibles.")
        else:
            ciudades = ["TODAS"] + sorted(df["Ciudad"].unique())
            ciudad_seleccionada = st.selectbox("Filtrar por Ciudad:", ciudades)

            if ciudad_seleccionada != "TODAS":
                df = df[df["Ciudad"] == ciudad_seleccionada]

            html_tabla = generar_tabla_html(df, basico, fecha_texto, bus)
            st.markdown(html_tabla, unsafe_allow_html=True)

# --- ADMINISTRACIÓN ---
elif pagina == "🛠️ Administración":
    st.subheader("Acceso de Administrador")

    if not st.session_state["login_autorizado"]:
        with st.form("login_form"):
            usuario = st.text_input("Usuario")
            password = st.text_input("Contraseña", type="password")
            submitted = st.form_submit_button("Ingresar")

        if submitted and autenticar(usuario, password):
            st.session_state["login_autorizado"] = True
            st.session_state["forzar_rerun"] = True
        elif submitted:
            st.error("Credenciales incorrectas.")

    if st.session_state["login_autorizado"]:
        if st.button("🔒 Cerrar sesión"):
            st.session_state["login_autorizado"] = False
            st.experimental_rerun()

        df = cargar_datos()

        st.markdown("### ➕ Agregar nuevo registro")
        with st.form("add_form"):
            ciudades_disponibles = cargar_ciudades()
            ciudades_seleccionadas = st.multiselect("Selecciona Ciudad(es)", ciudades_disponibles)
            guia = st.text_input("Nombre de Guía")
            correo_emv = st.text_input("Correo EMV")
            correo_personal = st.text_input("Correo Personal")
            agregar = st.form_submit_button("Guardar")

        if agregar and ciudades_seleccionadas:
            nuevos_registros = pd.DataFrame([
                {
                    "Ciudad": ciudad,
                    "Nombre de Guía": guia,
                    "Correo EMV": correo_emv,
                    "Correo Personal": correo_personal
                }
                for ciudad in ciudades_seleccionadas
            ])
            df = pd.concat([df, nuevos_registros], ignore_index=True)
            guardar_datos(df)
            st.success("Registro(s) agregado(s) correctamente.")
            st.session_state["forzar_rerun"] = True

        st.markdown("### ✏️ Editar o eliminar registros")
        selected_row = st.selectbox(
            "Selecciona una fila para editar o eliminar",
            df.index,
            format_func=lambda i: f"{df.loc[i, 'Ciudad']} - {df.loc[i, 'Nombre de Guía']}"
        )

        if selected_row is not None:
            row = df.loc[selected_row]
            ciudad_e = st.text_input("Ciudad", value=row["Ciudad"], key="edit_ciudad")
            guia_e = st.text_input("Nombre de Guía", value=row["Nombre de Guía"], key="edit_guia")
            correo_emv_e = st.text_input("Correo EMV", value=row["Correo EMV"], key="edit_emv")
            correo_personal_e = st.text_input("Correo Personal", value=row["Correo Personal"], key="edit_pers")

            col1, col2 = st.columns(2)
            with col1:
                if st.button("💾 Guardar Cambios"):
                    df.at[selected_row, "Ciudad"] = ciudad_e
                    df.at[selected_row, "Nombre de Guía"] = guia_e
                    df.at[selected_row, "Correo EMV"] = correo_emv_e
                    df.at[selected_row, "Correo Personal"] = correo_personal_e
                    guardar_datos(df)
                    st.success("Registro actualizado.")
                    st.session_state["forzar_rerun"] = True
            with col2:
                if st.button("🗑️ Eliminar Registro"):
                    df = df.drop(index=selected_row).reset_index(drop=True)
                    guardar_datos(df)
                    st.warning("Registro eliminado.")
                    st.session_state["forzar_rerun"] = True
