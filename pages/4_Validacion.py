# ============== pages/4_Validacion.py ==============
import streamlit as st
from utils.db import list_registros, validar_registro
from utils.auth import require_login, render_userbox, has_role, current_user

st.set_page_config(
    page_title="Validación",
    page_icon=":material/check_box:",
    layout="wide"
)

render_userbox()
require_login()

# Restringir a Empresa/Departamento/Admin
if not has_role({'Empresa','Departamento','Admin'}):
    st.error("No tienes permiso para esta página.")
    st.stop()

st.title(":material/check_box: Validación de Registros")

pend = list_registros(pendientes=True)
if pend.empty:
    st.info("No hay registros pendientes.")
else:
    st.dataframe(pend, use_container_width=True)
    ids = st.multiselect("Selecciona IDs a validar", pend["id"].tolist())
    validador = st.text_input("Validador (nombre)", value=current_user())
    if st.button(":material/check_circle: Validar seleccionados"):
        if not ids:
            st.warning("Selecciona al menos un registro.")
        else:
            for rid in ids:
                validar_registro(int(rid), validador)
            st.success("Registros validados.")
            st.rerun()