import streamlit as st
from utils.db import insert_alumno, list_alumnos, soft_delete_alumno, restore_alumno
from utils.auth import require_login, render_userbox, current_user

st.set_page_config(
    page_title="Alumnos",
    page_icon=":material/group:",
    layout="wide"
)

render_userbox()
require_login()

st.title(":material/group: Alumnos")

# Formulario de alta
with st.form("form_alumno", clear_on_submit=True):
    col1, col2 = st.columns(2)
    with col1:
        nombre = st.text_input("Nombre")
    with col2:
        carrera = st.text_input("Carrera")
    submitted = st.form_submit_button(":material/add: Agregar alumno")
    if submitted:
        if not nombre or not carrera:
            st.warning("Completa nombre y carrera.")
        else:
            _id = insert_alumno(nombre, carrera, usuario=current_user())
            st.success(f"Alumno agregado con ID {_id}")

st.divider()

# Listado y borrado lógico / restauración
mostrar_inactivos = st.checkbox("Mostrar inactivos", value=False)
df = list_alumnos(incluir_inactivos=mostrar_inactivos)
st.subheader("Listado")
if df.empty:
    st.info("No hay alumnos.")
else:
    st.dataframe(df, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        sel_baja = st.multiselect(
            "Selecciona IDs para desactivar (borrado lógico)", 
            df[df['activo']==True]['id'].tolist()
        )
        if st.button(":material/delete: Desactivar seleccionados"):
            for i in sel_baja:
                soft_delete_alumno(int(i), usuario=current_user())
            st.success("Alumnos desactivados.")
            st.rerun()
    with c2:
        sel_rest = st.multiselect(
            "Selecciona IDs para restaurar", 
            df[df['activo']==False]['id'].tolist()
        )
        if st.button(":material/restore: Restaurar seleccionados"):
            for i in sel_rest:
                restore_alumno(int(i), usuario=current_user())
            st.success("Alumnos restaurados.")
            st.rerun()