import streamlit as st
from utils.auth import require_login, render_userbox, has_role
import re

# Intentar importar funciones de Microsoft Auth
try:
    from utils.microsoft_auth import (
        get_admin_list, 
        add_admin_from_code, 
        remove_admin_by_code,
        is_current_user_admin
    )
    MICROSOFT_AVAILABLE = True
except ImportError:
    MICROSOFT_AVAILABLE = False

st.set_page_config(
    page_title="Administradores",
    page_icon=":material/admin_panel_settings:",
    layout="wide"
)

render_userbox()
require_login()

# Restringir solo a Admin
if not has_role({'Admin'}):
    st.error(":material/block: Solo administradores pueden acceder a esta página")
    st.stop()

st.title(":material/admin_panel_settings: Gestión de Administradores")

if not MICROSOFT_AVAILABLE:
    st.warning("⚠️ Microsoft Auth no está disponible. Esta página requiere autenticación con Microsoft.")
    st.stop()

st.markdown("""
Esta página permite gestionar qué estudiantes tienen permisos de **Administrador** en el sistema.

Los administradores pueden:
- ✅ Gestionar alumnos y lugares
- ✅ Validar registros
- ✅ Ver todas las funciones del sistema
- ✅ Agregar/remover otros administradores
""")

st.divider()

# Mostrar lista actual de administradores
st.markdown("### :material/supervisor_account: Administradores Actuales")

admin_codes = get_admin_list()

if admin_codes:
    st.info(f"📊 Total de administradores: **{len(admin_codes)}**")
    
    # Mostrar en tabla
    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        st.markdown("**Código de Estudiante**")
    with col2:
        st.markdown("**Email (aproximado)**")
    with col3:
        st.markdown("**Acción**")
    
    st.markdown("---")
    
    for code in admin_codes:
        col1, col2, col3 = st.columns([2, 2, 1])
        with col1:
            st.text(code)
        with col2:
            # Aproximar el formato de email
            st.text(f"xxx{code}@uvg.edu.gt")
        with col3:
            # No permitir que el admin actual se remueva a sí mismo
            current_email = st.session_state.get("email", "")
            current_code_match = re.search(r'(2\d+)', current_email)
            current_code = current_code_match.group(1) if current_code_match else None
            
            if code == current_code:
                st.caption("(Tú)")
            else:
                if st.button(":material/delete:", key=f"remove_{code}", help="Remover administrador"):
                    if remove_admin_by_code(code):
                        st.success(f"✅ Administrador {code} removido")
                        st.rerun()
                    else:
                        st.error("❌ Error al remover")
else:
    st.warning("⚠️ No hay administradores configurados")

st.divider()

# Agregar nuevos administradores
st.markdown("### :material/person_add: Agregar Nuevo Administrador")

tab1, tab2 = st.tabs([":material/tag: Por Código de Estudiante", ":material/mail: Por Email"])

with tab1:
    st.markdown("#### Agregar por código de estudiante")
    st.caption("Formato: 25837 o 2583 (se agregará el prefijo '2' automáticamente)")
    
    with st.form("form_add_by_code", clear_on_submit=True):
        codigo_input = st.text_input(
            ":material/badge: Código de Estudiante",
            placeholder="Ej: 25837 o 5837",
            help="Puedes ingresar con o sin el '2' inicial"
        )
        
        submit_code = st.form_submit_button(":material/add: Agregar Administrador", type="primary", use_container_width=True)
        
        if submit_code:
            if not codigo_input:
                st.warning("⚠️ Ingresa un código de estudiante")
            else:
                # Normalizar código
                digits = ''.join(ch for ch in codigo_input if ch.isdigit())
                if not digits:
                    st.error("❌ Código inválido. Solo ingresa números")
                else:
                    if not digits.startswith('2'):
                        digits = '2' + digits
                    
                    if add_admin_from_code(digits):
                        st.success(f"✅ Administrador {digits} agregado exitosamente")
                        st.balloons()
                        st.rerun()
                    else:
                        st.info(f"ℹ️ El código {digits} ya es administrador")

with tab2:
    st.markdown("#### Agregar por email institucional")
    st.caption("Formato: usuario25837@uvg.edu.gt")
    
    with st.form("form_add_by_email", clear_on_submit=True):
        email_input = st.text_input(
            ":material/mail: Email Institucional",
            placeholder="Ej: jua25837@uvg.edu.gt",
            help="El email debe tener el formato: letras + código + @uvg.edu.gt"
        )
        
        submit_email = st.form_submit_button(":material/add: Agregar Administrador", type="primary", use_container_width=True)
        
        if submit_email:
            if not email_input:
                st.warning("⚠️ Ingresa un email")
            else:
                # Extraer código del email
                email_lower = email_input.lower().strip()
                
                # Validar formato
                if not email_lower.endswith("@uvg.edu.gt"):
                    st.error("❌ El email debe terminar en @uvg.edu.gt")
                else:
                    local = email_lower.split("@")[0]
                    # Buscar patrón: letras + 2 + dígitos
                    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
                    
                    if not m:
                        st.error("❌ Email inválido. Debe tener el formato: letras + código (ej: jua25837@uvg.edu.gt)")
                    else:
                        codigo = m.group(2)
                        if add_admin_from_code(codigo):
                            st.success(f"✅ Administrador {codigo} ({email_input}) agregado exitosamente")
                            st.balloons()
                            st.rerun()
                        else:
                            st.info(f"ℹ️ El usuario {email_input} ya es administrador")

st.divider()

# Agregar múltiples administradores
with st.expander(":material/group_add: Agregar Múltiples Administradores"):
    st.markdown("#### Agregar varios administradores a la vez")
    st.caption("Ingresa múltiples códigos separados por comas")
    
    with st.form("form_add_multiple"):
        codigos_multiples = st.text_area(
            ":material/list: Códigos (separados por comas)",
            placeholder="Ej: 25837, 25498, 26123",
            help="Puedes pegar una lista de códigos separados por comas, saltos de línea o espacios",
            height=100
        )
        
        submit_multiple = st.form_submit_button(":material/playlist_add: Agregar Todos", type="secondary", use_container_width=True)
        
        if submit_multiple:
            if not codigos_multiples:
                st.warning("⚠️ Ingresa al menos un código")
            else:
                # Separar por comas, saltos de línea y espacios
                import re
                codigos = re.split(r'[,\s\n]+', codigos_multiples.strip())
                
                added_count = 0
                already_admin = 0
                errors = []
                
                for codigo in codigos:
                    codigo = codigo.strip()
                    if not codigo:
                        continue
                    
                    # Normalizar
                    digits = ''.join(ch for ch in codigo if ch.isdigit())
                    if not digits:
                        errors.append(f"Inválido: {codigo}")
                        continue
                    
                    if not digits.startswith('2'):
                        digits = '2' + digits
                    
                    if add_admin_from_code(digits):
                        added_count += 1
                    else:
                        already_admin += 1
                
                # Mostrar resultados
                if added_count > 0:
                    st.success(f"✅ {added_count} administrador(es) agregado(s)")
                if already_admin > 0:
                    st.info(f"ℹ️ {already_admin} código(s) ya eran administradores")
                if errors:
                    st.error(f"❌ Errores: {', '.join(errors)}")
                
                if added_count > 0:
                    st.balloons()
                    st.rerun()

st.divider()

# Información adicional
with st.expander(":material/info: Información Importante"):
    st.markdown("""
    ### Sobre los Administradores
    
    **¿Cómo funciona?**
    - Los administradores se identifican por su **código de estudiante** (ej: 25837)
    - Cuando un estudiante con código de admin inicia sesión con Microsoft, automáticamente obtiene rol de Admin
    - Los administradores predeterminados se configuran en las variables de entorno
    
    **Formato del Código:**
    - Debe empezar con '2' (ej: 25837, 25498)
    - Si ingresas sin el '2' (ej: 5837), se agregará automáticamente
    
    **Formato del Email:**
    - Debe seguir el patrón: `letras + código + @uvg.edu.gt`
    - Ejemplo válido: `jua25837@uvg.edu.gt`
    - El sistema extrae automáticamente el código `25837`
    
    **Persistencia:**
    - Los administradores agregados aquí solo persisten durante la sesión
    - Para hacerlos permanentes, agrégalos en la variable de entorno `MICROSOFT_ADMIN_STUDENTS` en Streamlit Secrets
    
    **Seguridad:**
    - Solo administradores actuales pueden agregar/remover otros administradores
    - No puedes removerte a ti mismo
    - Se requiere autenticación con cuenta @uvg.edu.gt
    """)

# Footer con estadísticas
st.divider()
col1, col2, col3 = st.columns(3)
with col1:
    st.metric(":material/people: Admins Activos", len(admin_codes))
with col2:
    current_user = st.session_state.get("display_name", "Usuario")
    st.metric(":material/person: Usuario Actual", current_user)
with col3:
    st.metric(":material/verified_user: Rol", "Administrador")