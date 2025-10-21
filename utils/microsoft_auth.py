"""
Autenticación con Microsoft usando OAuth público.
Versión con popup window y Material Symbols.
"""
import streamlit as st
import requests
from typing import Optional, Dict, List
import os
import re
import secrets
import hashlib
import base64
from urllib.parse import urlencode, quote

# Intentar cargar .env solo si existe (desarrollo local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

# Función helper para obtener variables de entorno o secrets de Streamlit
def _get_config(key: str, default: str = "") -> str:
    """Obtiene config desde st.secrets (Streamlit Cloud) o variables de entorno (local)"""
    try:
        # Intentar primero desde Streamlit secrets
        return st.secrets.get(key, os.getenv(key, default))
    except:
        # Fallback a variables de entorno
        return os.getenv(key, default)

# Configuración OAuth
CLIENT_ID = _get_config("AZURE_CLIENT_ID", "")
CLIENT_SECRET = _get_config("AZURE_CLIENT_SECRET", "")
REDIRECT_URI = _get_config("REDIRECT_URI", "http://localhost:8501")
TENANT = "common"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
SCOPES = ["User.Read"]

# Dominios permitidos de la UVG
DOMINIOS_PERMITIDOS = ["@uvg.edu.gt"]

# Estudiantes con permiso admin por defecto
DEFAULT_ADMIN_STUDENTS = set(s for s in _get_config("MICROSOFT_ADMIN_STUDENTS", "25837").split(",") if s)


def _generate_pkce_pair():
    """Genera code_verifier y code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def get_auth_url() -> str:
    """Genera URL de autorización de Microsoft con validación."""
    
    # Validar que CLIENT_ID existe
    if not CLIENT_ID or CLIENT_ID == "":
        st.error("❌ CLIENT_ID no configurado")
        return ""
    
    # Validar que REDIRECT_URI existe
    if not REDIRECT_URI or REDIRECT_URI == "":
        st.error("❌ REDIRECT_URI no configurado")
        return ""
    
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'response_mode': 'query',
        'scope': ' '.join(SCOPES),
        'prompt': 'select_account',
    }

    # Generar state aleatorio
    state = secrets.token_urlsafe(16)
    params['state'] = state
    st.session_state['ms_oauth_state'] = state

    # Si no hay client secret, habilitar PKCE
    if not CLIENT_SECRET:
        code_verifier, code_challenge = _generate_pkce_pair()
        st.session_state['ms_code_verifier'] = code_verifier
        params['code_challenge'] = code_challenge
        params['code_challenge_method'] = 'S256'

    # Construir URL manualmente para evitar problemas de encoding
    auth_url = f"{AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params, quote_via=quote)}"
    
    return auth_url


def exchange_code_for_token(code: str) -> Optional[Dict]:
    """Intercambia código de autorización por token de acceso."""
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    
    data = {
        'client_id': CLIENT_ID,
        'scope': ' '.join(SCOPES),
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    # Si existe CLIENT_SECRET, enviarlo
    if CLIENT_SECRET:
        data['client_secret'] = CLIENT_SECRET
    else:
        # PKCE: recuperar code_verifier
        code_verifier = st.session_state.get('ms_code_verifier')
        if code_verifier:
            data['code_verifier'] = code_verifier

    try:
        response = requests.post(token_url, data=data, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else {}
            error_msg = error_data.get('error_description', response.text)
            st.error(f"❌ Error obteniendo token: {error_msg}")
            
            with st.expander("🔍 Información de debug"):
                st.code(f"""
Status Code: {response.status_code}
Error: {error_data.get('error', 'N/A')}
Description: {error_msg}
                """)
            return None
    except requests.exceptions.Timeout:
        st.error("❌ Timeout al conectar con Microsoft. Intenta de nuevo.")
        return None
    except requests.exceptions.ConnectionError:
        st.error("❌ Error de conexión. Verifica tu internet.")
        return None
    except Exception as e:
        st.error(f"❌ Error inesperado: {str(e)}")
        return None


def get_user_info(access_token: str) -> Optional[Dict]:
    """Obtiene información del usuario desde Microsoft Graph API"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers,
            timeout=10
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Error obteniendo información del usuario (Status: {response.status_code})")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión con Graph API: {str(e)}")
        return None


def validar_dominio(email: str) -> bool:
    """Valida que el email termine con un dominio de la UVG"""
    if not email:
        return False
    
    email_lower = email.lower()
    return any(email_lower.endswith(dominio) for dominio in DOMINIOS_PERMITIDOS)


def determinar_rol(email: str) -> str:
    """Determina el rol basado en el formato del email"""
    if not email:
        return "Estudiante"
    
    email_lower = email.lower()
    local = email_lower.split("@")[0]
    
    # Patrón estudiante: letras seguido de '2' y dígitos
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
    if m:
        student_id = m.group(2)
        admin_set = get_admin_students()
        if student_id in admin_set:
            return "Admin"
        return "Estudiante"
    
    # Patrón docente: solo letras
    if re.fullmatch(r'[a-zA-Z]+', local):
        return "Docente"
    
    return "Estudiante"


def get_admin_students() -> set:
    """Devuelve el set de IDs de estudiantes con rol Admin."""
    if "microsoft_admin_students" not in st.session_state:
        st.session_state["microsoft_admin_students"] = set(DEFAULT_ADMIN_STUDENTS)
    return st.session_state["microsoft_admin_students"]


def microsoft_login_flow() -> bool:
    """Maneja el flujo completo de OAuth con Microsoft."""
    # Verificar si ya hay sesión activa
    if st.session_state.get("auth"):
        return True
    
    # Verificar si hay código en la URL (callback de Microsoft)
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params["code"]
        
        # Si viene de popup, cerrar ventana automáticamente
        if st.session_state.get("ms_popup_login"):
            st.markdown("""
            <script>
                // Cerrar ventana popup
                window.close();
                // Si no se puede cerrar (no es popup), redirigir
                setTimeout(function() {
                    if (!window.closed) {
                        window.location.href = window.location.origin;
                    }
                }, 500);
            </script>
            """, unsafe_allow_html=True)
        
        with st.spinner("🔄 Verificando credenciales con Microsoft..."):
            # Intercambiar código por token
            token_result = exchange_code_for_token(code)
            
            if token_result and "access_token" in token_result:
                access_token = token_result["access_token"]
                
                # Obtener información del usuario
                user_info = get_user_info(access_token)
                
                if user_info:
                    # Extraer email
                    email = user_info.get("mail") or user_info.get("userPrincipalName", "")
                    display_name = user_info.get("displayName", "Usuario")
                    
                    # VALIDAR DOMINIO
                    if not validar_dominio(email):
                        st.error("❌ Acceso denegado")
                        st.error(f"Solo se permite acceso a usuarios con correo **@uvg.edu.gt**")
                        st.info(f"Tu correo: {email}")
                        st.warning("💡 Debes usar tu cuenta institucional de la UVG")
                        
                        st.query_params.clear()
                        
                        if st.button("🔄 Intentar de nuevo"):
                            st.rerun()
                        
                        st.stop()
                    
                    # DOMINIO VÁLIDO - Crear sesión
                    st.session_state["auth"] = True
                    st.session_state["user"] = email
                    st.session_state["display_name"] = display_name
                    st.session_state["email"] = email
                    st.session_state["role"] = determinar_rol(email)
                    st.session_state["auth_method"] = "Microsoft"
                    st.session_state["alumno_id"] = None
                    
                    # Inicializar admins
                    _ = get_admin_students()
                    
                    # Limpiar URL y estado de popup
                    st.query_params.clear()
                    if "ms_popup_login" in st.session_state:
                        del st.session_state["ms_popup_login"]
                    
                    st.success(f"✅ Bienvenido, {display_name}!")
                    st.rerun()
                else:
                    st.error("❌ No se pudo obtener tu información de Microsoft")
            else:
                st.error("❌ No se pudo completar la autenticación")
        
        st.query_params.clear()
    
    return False


def render_microsoft_login_button():
    """Renderiza botón con Material Symbols que abre popup para login"""
    
    # DEBUG: Mostrar configuración (solo en desarrollo)
    if st.sidebar.checkbox("🔍 Mostrar configuración OAuth (debug)", value=False):
        with st.sidebar.expander("Configuración actual"):
            st.code(f"""
CLIENT_ID: {CLIENT_ID[:20]}...{CLIENT_ID[-10:] if CLIENT_ID else 'NO CONFIGURADO'}
REDIRECT_URI: {REDIRECT_URI}
TENANT: {TENANT}
AUTHORITY: {AUTHORITY}
SCOPES: {', '.join(SCOPES)}
CLIENT_SECRET: {'Configurado ✓' if CLIENT_SECRET else 'No configurado (usando PKCE)'}
            """)
    
    # Verificar si CLIENT_ID está configurado
    if not CLIENT_ID:
        st.error("⚠️ Microsoft OAuth no está configurado")
        st.info("Configura AZURE_CLIENT_ID en Streamlit Secrets o variables de entorno")
        
        with st.expander("📖 Configuración requerida"):
            st.markdown("""
            **Para Streamlit Cloud:**
            1. Ve a Settings → Secrets
            2. Agrega:
            ```toml
            AZURE_CLIENT_ID = "tu-client-id-aqui"
            AZURE_CLIENT_SECRET = "tu-client-secret-aqui"
            REDIRECT_URI = "https://tu-app.streamlit.app"
            ```
            """)
        return
    
    # Generar URL de autenticación
    auth_url = get_auth_url()
    
    if not auth_url:
        st.error("❌ No se pudo generar la URL de autenticación")
        return
    
    # Marcar que se usará popup
    st.session_state["ms_popup_login"] = True
    
    # JavaScript para abrir popup
    popup_script = f"""
    <script>
    function openMicrosoftLogin() {{
        const width = 500;
        const height = 700;
        const left = (screen.width / 2) - (width / 2);
        const top = (screen.height / 2) - (height / 2);
        
        const popup = window.open(
            '{auth_url}',
            'Microsoft Login',
            `width=${{width}},height=${{height}},left=${{left}},top=${{top}},toolbar=no,menubar=no,scrollbars=yes,resizable=yes`
        );
        
        // Verificar si el popup se abrió
        if (popup) {{
            // Monitorear cuando el popup se cierre
            const checkPopup = setInterval(() => {{
                if (popup.closed) {{
                    clearInterval(checkPopup);
                    // Recargar la página principal para verificar login
                    window.location.reload();
                }}
            }}, 500);
        }} else {{
            alert('Por favor, permite ventanas emergentes para iniciar sesión con Microsoft');
        }}
        
        return false;
    }}
    </script>
    """
    
    st.markdown(popup_script, unsafe_allow_html=True)
    
    # Botón estilizado con Material Symbols
    st.markdown("""
    <style>
    .ms-login-button {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 12px;
        background: linear-gradient(135deg, #0078d4 0%, #005a9e 100%);
        color: white;
        padding: 14px 32px;
        border: none;
        border-radius: 8px;
        cursor: pointer;
        font-size: 16px;
        font-weight: 600;
        box-shadow: 0 4px 12px rgba(0, 120, 212, 0.3);
        transition: all 0.3s ease;
        text-decoration: none;
        width: 100%;
        max-width: 400px;
        margin: 20px auto;
    }
    
    .ms-login-button:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 20px rgba(0, 120, 212, 0.4);
        background: linear-gradient(135deg, #0086f0 0%, #006bb8 100%);
    }
    
    .ms-login-button:active {
        transform: translateY(0);
    }
    
    .ms-icon {
        font-size: 24px;
        vertical-align: middle;
    }
    </style>
    
    <div style="text-align: center; padding: 20px 0;">
        <button class="ms-login-button" onclick="openMicrosoftLogin()">
            <span class="material-symbols-outlined ms-icon">login</span>
            Iniciar sesión con Microsoft
        </button>
    </div>
    """, unsafe_allow_html=True)
    
    st.info("🎓 Solo usuarios con correo **@uvg.edu.gt**")
    
    with st.expander("ℹ️ ¿Por qué usar mi cuenta de Microsoft?"):
        st.markdown("""
        ### Ventajas:
        - ✅ **Seguro**: No guardamos tu contraseña
        - ✅ **Conveniente**: Single Sign-On
        - ✅ **Verificado**: Garantiza que eres de la UVG
        - ✅ **Privado**: Solo accedemos a tu nombre y email
        
        ### ¿Qué permisos solicitamos?
        - 📧 **User.Read**: Para obtener tu nombre y correo electrónico
        
        ### ¿Es seguro?
        Sí. Usamos OAuth 2.0, el estándar de la industria. Microsoft gestiona 
        toda la autenticación y nosotros solo recibimos tu información básica.
        """)


# Funciones auxiliares para gestión de admins
def _normalize_student_id_from_input(value: str) -> Optional[str]:
    """Normaliza entradas variadas a '2' + dígitos."""
    if not value:
        return None
    v = value.strip().lower()
    if "@" in v:
        local = v.split("@", 1)[0]
        m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
        if m:
            return m.group(2)
        m2 = re.fullmatch(r'(2?\d+)', local)
        if m2:
            s = m2.group(1)
            if not s.startswith("2"):
                s = "2" + s
            return s
        return None
    digits = ''.join(ch for ch in v if ch.isdigit())
    if digits:
        if not digits.startswith("2"):
            digits = "2" + digits
        return digits
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', v)
    if m:
        return m.group(2)
    return None


def add_admins_from_codes(codes: List[str]) -> int:
    """Agrega una lista de códigos/emails como administradores."""
    if "microsoft_admin_students" not in st.session_state:
        st.session_state["microsoft_admin_students"] = set(DEFAULT_ADMIN_STUDENTS)
    admins = st.session_state["microsoft_admin_students"]
    added = 0
    for code in codes:
        sid = _normalize_student_id_from_input(code)
        if sid and sid not in admins:
            admins.add(sid)
            added += 1
    st.session_state["microsoft_admin_students"] = admins
    return added


def add_admin_from_code(code: str) -> bool:
    """Conveniencia para agregar un solo código/email."""
    return add_admins_from_codes([code]) == 1