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

# --- INTERFAZ PRINCIPAL ---
st.set_page_config(page_title="Guías Incorporaciones", layout="wide")
st.title("📋 Guías - Incorporaciones de Pasajeros")

pagina = st.sidebar.radio("Selecciona una opción:", ["📄 Visualización", "🛠️ Administración"])

# --- VISUALIZACIÓN PÚBLICA ---
if pagina == "📄 Visualización":
    st.subheader("Listado de Guías por Ciudad")
    df = cargar_datos()

    if df.empty:
        st.warning("No hay datos disponibles.")
    else:
        # Filtro por ciudad
        ciudades = ["TODAS"] + sorted(df["Ciudad"].unique())
        ciudad_seleccionada = st.selectbox("Filtrar por Ciudad:", ciudades)

        if ciudad_seleccionada != "TODAS":
            df = df[df["Ciudad"] == ciudad_seleccionada]

        # Visualización como tarjetas con botón de envío de correo funcional
        st.markdown("### 📬 Contactar a los Guías")
        for idx, row in df.iterrows():
            correo_link = f"mailto:{row['Correo EMV']}"
            if row['Correo Personal']:
                correo_link += f",{row['Correo Personal']}"
            asunto = urllib.parse.quote(f"Incorporaciones ({row['Ciudad']})")
            link = f"[📧 Enviar correo]({correo_link}?subject={asunto})"

            st.markdown(
                f"""
                <div style='border:1px solid #CCC; border-radius:10px; padding:10px; margin-bottom:10px'>
                    <strong>Ciudad:</strong> {row['Ciudad']}  | 
                    <strong>Guía:</strong> {row['Nombre de Guía']}  | 
                    <strong>Correo EMV:</strong> {row['Correo EMV']}  | 
                    <strong>Correo Personal:</strong> {row['Correo Personal'] or '-'}  | 
                    {link}
                </div>
                """,
                unsafe_allow_html=True
            )

# --- ADMINISTRACIÓN ---
elif pagina == "🛠️ Administración":
    st.subheader("Acceso de Administrador")
    with st.form("login_form"):
        usuario = st.text_input("Usuario")
        password = st.text_input("Contraseña", type="password")
        submitted = st.form_submit_button("Ingresar")

    if submitted and autenticar(usuario, password):
        st.success("Acceso concedido.")
        df = cargar_datos()

        # --- FORMULARIO DE NUEVO REGISTRO ---
        st.markdown("### ➕ Agregar nuevo registro")
        with st.form("add_form"):
            ciudad = st.text_input("Ciudad")
            guia = st.text_input("Nombre de Guía")
            correo_emv = st.text_input("Correo EMV")
            correo_personal = st.text_input("Correo Personal")
            agregar = st.form_submit_button("Guardar")

        if agregar:
            nuevo_registro = pd.DataFrame([{
                "Ciudad": ciudad,
                "Nombre de Guía": guia,
                "Correo EMV": correo_emv,
                "Correo Personal": correo_personal
            }])
            df = pd.concat([df, nuevo_registro], ignore_index=True)
            guardar_datos(df)
            st.success("Registro agregado correctamente.")
            st.experimental_rerun()

        # --- EDICIÓN Y ELIMINACIÓN ---
        st.markdown("### ✏️ Editar o eliminar registros")
        selected_row = st.selectbox("Selecciona una fila para editar o eliminar", df.index, format_func=lambda i: f"{df.loc[i, 'Ciudad']} - {df.loc[i, 'Nombre de Guía']}")
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
                    st.experimental_rerun()
            with col2:
                if st.button("🗑️ Eliminar Registro"):
                    df = df.drop(index=selected_row).reset_index(drop=True)
                    guardar_datos(df)
                    st.warning("Registro eliminado.")
                    st.experimental_rerun()

    elif submitted:
        st.error("Credenciales incorrectas.")
