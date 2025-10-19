import streamlit as st
from utils.db import insert_lugar, list_lugares, soft_delete_lugar, restore_lugar
from utils.auth import require_login, render_userbox, current_user

st.set_page_config(
    page_title="Lugares",
    page_icon=":material/domain:",
    layout="wide"
)

render_userbox()
require_login()

st.title(":material/domain: Lugares")

with st.form("form_lugar", clear_on_submit=True):
    nombre = st.text_input("Nombre del lugar / empresa")
    submitted = st.form_submit_button(":material/add: Agregar lugar")
    if submitted:
        if not nombre:
            st.warning("Escribe un nombre.")
        else:
            _id = insert_lugar(nombre, usuario=current_user())
            st.success(f"Lugar agregado con ID {_id}")

st.divider()

mostrar_inactivos = st.checkbox("Mostrar inactivos", value=False)
df = list_lugares(incluir_inactivos=mostrar_inactivos)
st.subheader("Listado")
if df.empty:
    st.info("No hay lugares.")
else:
    st.dataframe(df, use_container_width=True)
    c1, c2 = st.columns(2)
    with c1:
        sel_baja = st.multiselect(
            "Selecciona IDs para desactivar", 
            df[df['activo']==True]['id'].tolist()
        )
        if st.button(":material/delete: Desactivar seleccionados"):
            for i in sel_baja:
                soft_delete_lugar(int(i), usuario=current_user())
            st.success("Lugares desactivados.")
            st.rerun()
    with c2:
        sel_rest = st.multiselect(
            "Selecciona IDs para restaurar", 
            df[df['activo']==False]['id'].tolist()
        )
        if st.button(":material/restore: Restaurar seleccionados"):
            for i in sel_rest:
                restore_lugar(int(i), usuario=current_user())
            st.success("Lugares restaurados.")
            st.rerun()