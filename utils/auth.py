"""
Autenticación local basada en la tabla usuarios.
Incluye renderizado de sidebar con logo y Material Icons.
"""
import os
from typing import Iterable, Optional
import streamlit as st
from utils.db import verify_user

SESSION_KEYS = ["auth", "user", "role", "alumno_id"]


def login(user: str, password: str) -> bool:
    """
    Verifica credenciales con verify_user(user, password).
    Si son válidas, establece variables de sesión y devuelve True.
    """
    info = verify_user(user, password)
    if info:
        st.session_state["auth"] = True
        st.session_state["user"] = info.get("username", user)
        st.session_state["role"] = info.get("role", "")
        st.session_state["alumno_id"] = info.get("alumno_id")
        return True
    return False


def logout() -> None:
    """
    Limpia el estado de sesión y recarga la app.
    """
    for k in SESSION_KEYS:
        if k in st.session_state:
            del st.session_state[k]
    st.rerun()


def is_logged() -> bool:
    """Retorna True si hay sesión autenticada."""
    return bool(st.session_state.get("auth"))


def current_role() -> str:
    """Rol actual del usuario o cadena vacía si no existe."""
    return st.session_state.get("role", "")


def current_user() -> str:
    """Usuario actual o cadena vacía si no existe."""
    return st.session_state.get("user", "")


def current_alumno_id() -> Optional[int]:
    """ID del alumno asociado (si procede)."""
    return st.session_state.get("alumno_id")


def has_role(roles: Iterable[str]) -> bool:
    """
    Retorna True si el usuario autenticado posee alguno de los roles indicados.
    """
    if not is_logged():
        return False
    r = current_role()
    return r in set(roles)


def require_login() -> None:
    """
    Si no hay sesión, muestra error y detiene la ejecución de la página actual.
    """
    if not is_logged():
        st.error("Debes iniciar sesión en la página de Inicio.")
        st.stop()


def _render_logo_in_sidebar() -> None:
    """
    Renderiza un logo en la barra lateral usando st.logo().
    Busca assets/logo.png para el logo principal y assets/icon.png para el icono.
    Compatible con la API de st.logo() según la documentación oficial.
    """
    logo_path = os.path.join("assets", "logo.png")
    icon_path = os.path.join("assets", "icon.png")
    
    # Verificar si existen los archivos
    logo_exists = os.path.exists(logo_path)
    icon_exists = os.path.exists(icon_path)
    
    if logo_exists:
        # st.logo() acepta:
        # - image: ruta al archivo o URL del logo principal
        # - link: URL opcional para hacer el logo clickeable
        # - icon_image: ruta al archivo o URL del icono (versión compacta)
        try:
            if icon_exists:
                # Usar ambos: logo principal e icono
                st.logo(
                    image=logo_path,
                    icon_image=icon_path
                )
            else:
                # Solo logo principal
                st.logo(image=logo_path)
        except Exception as e:
            # Fallback silencioso si hay algún problema
            st.sidebar.caption(f"⚠️ Error al cargar logo: {e}")


def render_userbox() -> None:
    """
    Renderiza el panel lateral (sidebar) con:
    - Logo (si existe)
    - Enlaces de navegación con iconos Material Symbols
    - Información de sesión al final
    - Botón de Cerrar sesión
    """
    # Renderizar logo antes del contenido
    _render_logo_in_sidebar()

    with st.sidebar:
        if is_logged():
            # Navegación con iconos según rol
            st.caption("NAVEGACIÓN")
            rol = current_role()
            
            # Mostrar páginas según el rol del usuario
            if rol == 'Admin':
                st.page_link("0_Inicio.py", label=":material/home: Inicio")
                st.page_link("pages/1_Alumnos.py", label=":material/group: Alumnos")
                st.page_link("pages/2_Lugares.py", label=":material/domain: Lugares")
                st.page_link("pages/3_Registros.py", label=":material/app_registration: Registros")
                st.page_link("pages/4_Validacion.py", label=":material/check_box: Validación")
                st.page_link("pages/5_Administradores.py", label=":material/admin_panel_settings: Administradores")
            elif rol == 'Estudiante':
                st.page_link("0_Inicio.py", label=":material/home: Inicio")
                st.page_link("pages/3_Registros.py", label=":material/app_registration: Mis Registros")
            elif rol in ['Empresa', 'Departamento', 'Docente']:
                st.page_link("0_Inicio.py", label=":material/home: Inicio")
                st.page_link("pages/3_Registros.py", label=":material/app_registration: Registros")
                st.page_link("pages/4_Validacion.py", label=":material/check_box: Validación")
            else:
                st.page_link("0_Inicio.py", label=":material/home: Inicio")
            
            st.divider()
            
            # Información de sesión al final
            st.caption("SESIÓN ACTIVA")
            
            # Usuario
            st.markdown(f"**:material/person: Usuario**")
            st.markdown(f"<div style='margin-left: 1.8rem; margin-top: -0.5rem; margin-bottom: 0.8rem;'>{current_user()}</div>", unsafe_allow_html=True)

            # Rol
            st.markdown(f"**:material/verified_user: Rol**")
            st.markdown(f"<div style='margin-left: 1.8rem; margin-top: -0.5rem; margin-bottom: 0.8rem;'>{current_role()}</div>", unsafe_allow_html=True)

            # alumno_id si existe
            alumno_id = current_alumno_id()
            if alumno_id is not None:
                st.markdown(f"**:material/school: Alumno ID**")
                st.markdown(f"<div style='margin-left: 1.8rem; margin-top: -0.5rem; margin-bottom: 0.8rem;'>{alumno_id}</div>", unsafe_allow_html=True)
            
            st.divider()
            
            # Botón de cerrar sesión
            if st.button(":material/logout: Cerrar sesión", key="logout_btn", use_container_width=True):
                logout()
        else:
            st.caption("No has iniciado sesión.")
            st.page_link("0_Inicio.py", label=":material/home: Ir a Inicio")