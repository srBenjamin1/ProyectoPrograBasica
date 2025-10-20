import streamlit as st
from utils.db import init_db
from utils.auth import login, is_logged, render_userbox, current_role, logout
import os

# Intentar importar Microsoft Auth (opcional)
try:
    from utils.microsoft_auth import microsoft_login_flow, render_microsoft_login_button, add_admins_from_codes
    MICROSOFT_AVAILABLE = True
except ImportError:
    MICROSOFT_AVAILABLE = False

st.set_page_config(
    page_title="Inicio",
    page_icon=":material/home:",
    layout="wide"
)

# Agregar administradores desde .env al iniciar (opcional, no requiere UI)
if MICROSOFT_AVAILABLE:
    admins_env = os.getenv("MICROSOFT_ADMIN_STUDENTS", "")
    if admins_env:
        codes = [c.strip() for c in admins_env.split(",") if c.strip()]
        # esto añadirá a session_state["microsoft_admin_students"] los IDs normalizados
        add_admins_from_codes(codes)

init_db()
render_userbox()

st.title(":material/home: Inicio")

# Manejar flujo de Microsoft OAuth si está disponible
if MICROSOFT_AVAILABLE:
    microsoft_login_flow()

if not is_logged():
    st.markdown("## 🔐 Bienvenido al Sistema de Gestión de Horas de Extensión")
    
    # Tabs para diferentes métodos de login
    if MICROSOFT_AVAILABLE:
        tab1, tab2 = st.tabs([
            "🎓 Cuenta UVG (Recomendado)", 
            "🔑 Cuenta Local"
        ])
    else:
        tab2 = st.container()
        tab1 = None
    
    # Tab 1: Microsoft OAuth
    if MICROSOFT_AVAILABLE and tab1:
        with tab1:
            st.markdown("### Inicia sesión con tu cuenta institucional")
            st.caption("Usa tu correo @uvg.edu.gt")
            
            render_microsoft_login_button()
            
            st.divider()
            st.warning("⚠️ **Importante**: Solo usuarios con correo institucional de la UVG")
    
    # Tab 2: Login Local
    with tab2:
        if MICROSOFT_AVAILABLE:
            st.markdown("### Login con cuenta local")
            st.caption("Para administradores y usuarios especiales")
        else:
            st.markdown("### Iniciar sesión")
        
        with st.form("login_form"):
            u = st.text_input("👤 Usuario", placeholder="Ingresa tu usuario")
            p = st.text_input("🔒 Contraseña", type="password", placeholder="Ingresa tu contraseña")
            ok = st.form_submit_button("🚀 Entrar", use_container_width=True)
            
            if ok:
                if login(u, p):
                    st.success("✅ Ingreso exitoso. Usa el menú lateral para navegar.")
                    st.rerun()
                else:
                    st.error("❌ Usuario o contraseña incorrectos.")
        
        with st.expander("ℹ️ Usuarios demo disponibles"):
            st.code("""
Usuario: admin      | Contraseña: 1234 | Rol: Admin
Usuario: depto      | Contraseña: 1234 | Rol: Departamento
Usuario: empresa    | Contraseña: 1234 | Rol: Empresa
Usuario: estudiante | Contraseña: 1234 | Rol: Estudiante
            """)

else:
    # Usuario ya autenticado
    rol = current_role()
    auth_method = st.session_state.get("auth_method", "Local")
    
    st.success("✅ Sesión activa")
    
    col1, col2 = st.columns([3, 1])
    
    with col1:
        if auth_method == "Microsoft":
            st.info(f"👤 **{st.session_state.get('display_name')}**")
            st.caption(f"📧 {st.session_state.get('email')}")
            st.caption(f"🔐 Autenticado con Microsoft")
        else:
            st.info(f"👤 **{st.session_state.get('user')}**")
            st.caption(f"🔑 Autenticación local")
        
        st.markdown(f"**🎭 Rol:** {rol}")
    
    with col2:
        if st.button("🚪 Cerrar Sesión", type="primary", use_container_width=True):
            logout()
    
    st.divider()
    
    st.markdown("### 🎯 ¿Qué puedes hacer?")
    
    # Mostrar opciones según el rol
    if rol == 'Estudiante':
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="padding: 20px; background-color: #e8f5e9; border-radius: 10px; border-left: 4px solid #4caf50;">
                <h4>📝 Registrar Horas</h4>
                <p>Ve a <b>Registros</b> para reportar tus horas de extensión</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="padding: 20px; background-color: #e3f2fd; border-radius: 10px; border-left: 4px solid #2196f3;">
                <h4>📊 Ver Estado</h4>
                <p>Consulta tus horas validadas y pendientes</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif rol in ['Empresa', 'Departamento']:
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("""
            <div style="padding: 20px; background-color: #e3f2fd; border-radius: 10px; border-left: 4px solid #2196f3;">
                <h4>✅ Validar Registros</h4>
                <p>Ve a <b>Validación</b> para aprobar registros pendientes</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="padding: 20px; background-color: #fff3e0; border-radius: 10px; border-left: 4px solid #ff9800;">
                <h4>📈 Ver Registros</h4>
                <p>Consulta todos los registros del sistema</p>
            </div>
            """, unsafe_allow_html=True)
    
    elif rol == 'Admin':
        col1, col2, col3 = st.columns(3)
        with col1:
            st.markdown("""
            <div style="padding: 20px; background-color: #e8f5e9; border-radius: 10px; border-left: 4px solid #4caf50;">
                <h4>👥 Alumnos</h4>
                <p>Gestionar catálogo de alumnos</p>
            </div>
            """, unsafe_allow_html=True)
        with col2:
            st.markdown("""
            <div style="padding: 20px; background-color: #e3f2fd; border-radius: 10px; border-left: 4px solid #2196f3;">
                <h4>🏢 Lugares</h4>
                <p>Gestionar empresas y lugares</p>
            </div>
            """, unsafe_allow_html=True)
        with col3:
            st.markdown("""
            <div style="padding: 20px; background-color: #fff3e0; border-radius: 10px; border-left: 4px solid #ff9800;">
                <h4>✅ Validación</h4>
                <p>Aprobar registros pendientes</p>
            </div>
            """, unsafe_allow_html=True)