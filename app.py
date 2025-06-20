import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials

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

def enviar_correo(ciudad, correo_emv, correo_personal):
    asunto = f"Incorporaciones ({ciudad})"
    return f"mailto:{correo_emv},{correo_personal}?subject={asunto}"

# --- LOGIN ADMINISTRADOR ---
def autenticar(usuario, contraseña):
    admin_df = gc.open_by_key(SHEET_ID).worksheet("ADMIN").get_all_records()
    credenciales = pd.DataFrame(admin_df)
    return not credenciales[
        (credenciales["Usuario"] == usuario) & (credenciales["Password"] == contraseña)
    ].empty

# --- INTERFAZ ---
st.set_page_config(page_title="Guías Incorporaciones", layout="wide")
st.title("📋 Guías - Incorporaciones de Pasajeros")

# --- SELECCIÓN DE PÁGINA ---
pagina = st.sidebar.radio("Selecciona una opción:", ["📄 Visualización", "🛠️ Administración"])

# --- VISUALIZACIÓN PÚBLICA ---
if pagina == "📄 Visualización":
    st.subheader("Listado de Guías por Ciudad")
    if st.button("🔄 Actualizar Datos"):
        df = cargar_datos()
        st.success("Datos actualizados correctamente.")
    else:
        df = cargar_datos()

    if df.empty:
        st.warning("No hay datos disponibles.")
    else:
        for i, row in df.iterrows():
            with st.expander(f"{row['Ciudad']} - {row['Nombre de Guía']}"):
                st.markdown(f"**Correo EMV:** {row['Correo EMV']}")
                st.markdown(f"**Correo Personal:** {row['Correo Personal']}")
                mailto_link = enviar_correo(row['Ciudad'], row['Correo EMV'], row['Correo Personal'])
                st.markdown(f"[📧 Enviar correo]({mailto_link})")

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

        # --- EDICIÓN Y ELIMINACIÓN ---
        st.markdown("### ✏️ Editar o eliminar registros")
        selected_row = st.selectbox("Selecciona una fila para editar o eliminar", df.index)
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
            with col2:
                if st.button("🗑️ Eliminar Registro"):
                    df = df.drop(index=selected_row).reset_index(drop=True)
                    guardar_datos(df)
                    st.warning("Registro eliminado.")

    elif submitted:
        st.error("Credenciales incorrectas.")

