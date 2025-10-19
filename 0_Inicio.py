import streamlit as st
from utils.db import init_db
from utils.auth import login, is_logged, render_userbox, current_role

st.set_page_config(
    page_title="Inicio",
    page_icon=":material/home:",
    layout="wide"
)

init_db()
render_userbox()

st.title(":material/home: Inicio")

if not is_logged():
    st.subheader("Iniciar sesión")
    with st.form("login_form"):
        u = st.text_input("Usuario")
        p = st.text_input("Contraseña", type="password")
        ok = st.form_submit_button("Entrar")
        if ok:
            if login(u, p):
                st.success("Ingreso exitoso. Usa el menú lateral para navegar.")
                st.rerun()
            else:
                st.error("Usuario o contraseña incorrectos.")
else:
    st.success("Sesión activa.")
    rol = current_role()
    st.markdown(f"**Rol actual:** {rol}")
    st.markdown("""
    ### ¿Qué quieres hacer?
    - **Estudiante**: Ir a **:material/app_registration: Registros** y reportar horas (quedarán pendientes hasta validación).
    - **Empresa/Departamento**: Ir a **:material/check_box: Validación** para aprobar registros pendientes.
    - **Admin**: Gestionar catálogo (:material/group: Alumnos, :material/domain: Lugares) y supervisar el sistema.
    """)