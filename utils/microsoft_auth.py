"""
Autenticación con Microsoft usando OAuth público.
Permite login con cualquier cuenta Microsoft, pero valida el dominio @uvg.edu.gt después.
No requiere acceso al Azure AD institucional.
"""
import streamlit as st
import requests
from typing import Optional, Dict, List
import os
import re
from dotenv import load_dotenv
import secrets
import hashlib
import base64

# Cargar variables de entorno desde .env (si existe)
load_dotenv()  # permite que AZURE_CLIENT_ID y REDIRECT_URI se llenen desde .env

# Configuración OAuth (debes registrar tu app en portal.azure.com)
CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "")  # Configura esto después de registrar tu app
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "")  # Si tu app es "confidential" pon el secret aquí
TENANT = "common"  # Permite cualquier cuenta Microsoft
AUTHORITY = f"https://login.microsoftonline.com/{TENANT}"
REDIRECT_URI = os.getenv("REDIRECT_URI", "http://localhost:8501")
SCOPES = ["User.Read"]

# Dominios permitidos de la UVG
DOMINIOS_PERMITIDOS = ["@uvg.edu.gt"]

# Estudiantes con permiso admin por defecto; configurable vía env: MICROSOFT_ADMIN_STUDENTS="25837,12345"
DEFAULT_ADMIN_STUDENTS = set(s for s in os.getenv("MICROSOFT_ADMIN_STUDENTS", "25837").split(",") if s)


def _generate_pkce_pair():
    """Genera code_verifier y code_challenge (S256)."""
    code_verifier = secrets.token_urlsafe(64)  # longitud segura
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode()).digest()
    ).rstrip(b"=").decode("ascii")
    return code_verifier, code_challenge


def get_auth_url() -> str:
    """Genera URL de autorización de Microsoft. Usa PKCE si no hay CLIENT_SECRET."""
    params = {
        'client_id': CLIENT_ID,
        'response_type': 'code',
        'redirect_uri': REDIRECT_URI,
        'response_mode': 'query',
        'scope': ' '.join(SCOPES),
    }

    # Generar state aleatorio y guardarlo para validación opcional
    state = secrets.token_urlsafe(16)
    params['state'] = state
    st.session_state['ms_oauth_state'] = state

    # Si no hay client secret, habilitar PKCE (public client)
    if not CLIENT_SECRET:
        code_verifier, code_challenge = _generate_pkce_pair()
        st.session_state['ms_code_verifier'] = code_verifier
        params['code_challenge'] = code_challenge
        params['code_challenge_method'] = 'S256'

    from urllib.parse import urlencode
    auth_url = f"{AUTHORITY}/oauth2/v2.0/authorize?{urlencode(params)}"
    return auth_url


def exchange_code_for_token(code: str) -> Optional[Dict]:
    """Intercambia código de autorización por token de acceso.
       Incluye client_secret si está configurado, o code_verifier si usamos PKCE.
    """
    token_url = f"{AUTHORITY}/oauth2/v2.0/token"
    
    data = {
        'client_id': CLIENT_ID,
        'scope': ' '.join(SCOPES),
        'code': code,
        'redirect_uri': REDIRECT_URI,
        'grant_type': 'authorization_code'
    }

    # Si existe CLIENT_SECRET (confidential client), enviarlo
    if CLIENT_SECRET:
        data['client_secret'] = CLIENT_SECRET
    else:
        # PKCE: recuperar code_verifier guardado previamente
        code_verifier = st.session_state.get('ms_code_verifier')
        if code_verifier:
            data['code_verifier'] = code_verifier

    try:
        response = requests.post(token_url, data=data)
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Error obteniendo token: {response.text}")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None


def get_user_info(access_token: str) -> Optional[Dict]:
    """Obtiene información del usuario desde Microsoft Graph API"""
    headers = {'Authorization': f'Bearer {access_token}'}
    
    try:
        response = requests.get(
            'https://graph.microsoft.com/v1.0/me',
            headers=headers
        )
        
        if response.status_code == 200:
            return response.json()
        else:
            st.error(f"❌ Error obteniendo información del usuario")
            return None
    except Exception as e:
        st.error(f"❌ Error de conexión: {str(e)}")
        return None


def validar_dominio(email: str) -> bool:
    """Valida que el email termine con un dominio de la UVG"""
    if not email:
        return False
    
    email_lower = email.lower()
    return any(email_lower.endswith(dominio) for dominio in DOMINIOS_PERMITIDOS)


def determinar_rol(email: str) -> str:
    """Determina el rol basado en el formato del email:
       - Admin: si el student_id está en admins
       - Estudiante: letras + '2' + dígitos antes de @uvg.edu.gt
       - Docente: solo letras antes de @uvg.edu.gt
    """
    if not email:
        return "Estudiante"
    
    email_lower = email.lower()
    local = email_lower.split("@")[0]
    
    # Patrón estudiante: letras seguido de '2' y dígitos (capturamos el '2' también)
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
    if m:
        student_id = m.group(2)  # incluye el '2', e.g. "25837"
        admin_set = get_admin_students()
        if student_id in admin_set:
            return "Admin"
        return "Estudiante"
    
    # Patrón docente: solo letras
    if re.fullmatch(r'[a-zA-Z]+', local):
        return "Docente"
    
    # Fallback
    return "Estudiante"


# ---------- Gestión de administradores en memoria (solo para flujo Microsoft) ----------
def get_admin_students() -> set:
    """Devuelve el set de IDs de estudiantes con rol Admin (almacenado en session_state)."""
    if "microsoft_admin_students" not in st.session_state:
        st.session_state["microsoft_admin_students"] = set(DEFAULT_ADMIN_STUDENTS)
    return st.session_state["microsoft_admin_students"]


def is_current_user_admin() -> bool:
    """True si el usuario autenticado actual es Admin según session_state o su ID está en admins."""
    if not st.session_state.get("auth"):
        return False
    if st.session_state.get("role") == "Admin":
        return True
    email = st.session_state.get("email", "").lower()
    local = email.split("@")[0] if email else ""
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
    if m:
        student_id = m.group(2)
        return student_id in get_admin_students()
    return False


def add_admin_by_student_id(student_id: str) -> bool:
    """Agregar un student_id a la lista de admins. Acepta '25837' o '5837' y normaliza a '2...'."""
    if not is_current_user_admin():
        return False
    s = ''.join(ch for ch in str(student_id).strip() if ch.isdigit())
    if not s:
        return False
    # Asegurar que el ID tenga el prefijo '2'
    if not s.startswith('2'):
        s = '2' + s
    admins = get_admin_students()
    admins.add(s)
    st.session_state["microsoft_admin_students"] = admins
    return True


def add_admin_by_email(email: str) -> bool:
    """Extrae el ID desde un email tipo xxx2yyyy@uvg.edu.gt y lo agrega como admin."""
    if not is_current_user_admin():
        return False
    if not email or "@" not in email:
        return False
    local = email.lower().split("@")[0]
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
    if not m:
        return False
    return add_admin_by_student_id(m.group(2))


def microsoft_login_flow() -> bool:
    """
    Maneja el flujo completo de OAuth con Microsoft.
    Retorna True si hay una sesión activa, False si no.
    """
    # Verificar si ya hay sesión activa
    if st.session_state.get("auth"):
        return True
    
    # Verificar si hay código en la URL (callback de Microsoft)
    query_params = st.query_params
    
    if "code" in query_params:
        code = query_params["code"]
        
        with st.spinner("🔄 Verificando credenciales con Microsoft..."):
            # Intercambiar código por token
            token_result = exchange_code_for_token(code)
            
            if token_result and "access_token" in token_result:
                access_token = token_result["access_token"]
                
                # Obtener información del usuario
                user_info = get_user_info(access_token)
                
                if user_info:
                    # Extraer email (puede estar en 'mail' o 'userPrincipalName')
                    email = user_info.get("mail") or user_info.get("userPrincipalName", "")
                    display_name = user_info.get("displayName", "Usuario")
                    
                    # VALIDAR DOMINIO
                    if not validar_dominio(email):
                        st.error("❌ Acceso denegado")
                        st.error(f"Solo se permite acceso a usuarios con correo **@uvg.edu.gt**")
                        st.info(f"Tu correo: {email}")
                        st.warning("💡 Debes usar tu cuenta institucional de la UVG")
                        
                        # Limpiar query params
                        st.query_params.clear()
                        
                        # Botón para reintentar
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
                    st.session_state["alumno_id"] = None  # Se puede vincular después
                    
                    # Asegurar que el set de admins esté inicializado en session
                    _ = get_admin_students()
                    
                    # Limpiar URL
                    st.query_params.clear()
                    st.success(f"✅ Bienvenido, {display_name}!")
                    st.rerun()
                else:
                    st.error("❌ No se pudo obtener tu información de Microsoft")
            else:
                st.error("❌ No se pudo completar la autenticación")
        
        # Limpiar query params
        st.query_params.clear()
    
    return False


def render_microsoft_login_button():
    """Renderiza un botón elegante para login con Microsoft"""
    
    # Verificar si CLIENT_ID está configurado
    if not CLIENT_ID:
        st.error("⚠️ Microsoft OAuth no está configurado")
        st.info("Configura AZURE_CLIENT_ID en las variables de entorno")
        with st.expander("📖 Ver instrucciones de configuración"):
            st.markdown("""
            1. Ve a https://portal.azure.com
            2. Azure Active Directory → App registrations → New registration
            3. Copia el **Client ID**
            4. Configura Redirect URI: `http://localhost:8501`
            5. Agrega permiso: Microsoft Graph → User.Read
            6. Crea archivo `.env` con: `AZURE_CLIENT_ID=tu-client-id`
            """)
        return
    
    auth_url = get_auth_url()
    
    # Botón estilizado
    st.markdown(f"""
    <div style="text-align: center; padding: 30px 20px;">
        <a href="{auth_url}" target="_self" style="text-decoration: none;">
            <button style="
                background: linear-gradient(135deg, #0078d4 0%, #005a9e 100%);
                color: white;
                padding: 16px 48px;
                border: none;
                border-radius: 8px;
                cursor: pointer;
                font-size: 18px;
                font-weight: 600;
                box-shadow: 0 4px 12px rgba(0, 120, 212, 0.3);
                transition: all 0.3s ease;
                display: inline-flex;
                align-items: center;
                gap: 12px;
            " onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 20px rgba(0, 120, 212, 0.4)'"
               onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(0, 120, 212, 0.3)'">
                <svg width="24" height="24" viewBox="0 0 21 21" fill="none" xmlns="http://www.w3.org/2000/svg">
                    <rect width="10" height="10" fill="white"/>
                    <rect y="11" width="10" height="10" fill="white"/>
                    <rect x="11" width="10" height="10" fill="white"/>
                    <rect x="11" y="11" width="10" height="10" fill="white"/>
                </svg>
                Iniciar sesión con Microsoft
            </button>
        </a>
    </div>
    """, unsafe_allow_html=True)
    
    # Información
    st.info("🎓 Solo usuarios con correo **@uvg.edu.gt**")
    
    # Expandible con más info
    with st.expander("ℹ️ ¿Por qué usar mi cuenta de Microsoft?"):
        st.markdown("""
        ### Ventajas de usar Microsoft OAuth:
        
        - ✅ **Seguro**: No guardamos tu contraseña
        - ✅ **Conveniente**: Single Sign-On con tu cuenta institucional  
        - ✅ **Verificado**: Garantiza que eres parte de la UVG
        - ✅ **Privado**: Solo accedemos a tu nombre y email
        
        ### ¿Qué permisos solicitamos?
        
        - 📧 **User.Read**: Para obtener tu nombre y correo electrónico
        
        ### ¿Es seguro?
        
        Sí. Usamos OAuth 2.0, el estándar de la industria para autenticación.
        Microsoft gestiona toda la autenticación y nosotros solo recibimos
        un token que nos permite leer tu información básica.
        """)


def _normalize_student_id_from_input(value: str) -> Optional[str]:
    """Normaliza entradas variadas a la forma que usamos: '2' + dígitos (ej. '25837').
       Acepta:
         - emails tipo 'jua25837@uvg.edu.gt' -> extrae '25837'
         - cadenas numéricas '25837' o '5837' -> asegura prefijo '2'
         - cadenas ya en forma '2xxxxx' -> devuelve tal cual
       Retorna None si no se puede extraer un ID válido.
    """
    if not value:
        return None
    v = value.strip().lower()
    # Si viene con @, extraer la parte local
    if "@" in v:
        local = v.split("@", 1)[0]
        m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', local)
        if m:
            return m.group(2)
        # por si alguien pasa '25837@...' local numérico
        m2 = re.fullmatch(r'(2?\d+)', local)
        if m2:
            s = m2.group(1)
            if not s.startswith("2"):
                s = "2" + s
            return s
        return None
    # Si es solo dígitos o empieza con 2
    digits = ''.join(ch for ch in v if ch.isdigit())
    if digits:
        if not digits.startswith("2"):
            digits = "2" + digits
        return digits
    # Si viene en formato local con letras+2digits
    m = re.fullmatch(r'([a-zA-Z]+)(2\d+)', v)
    if m:
        return m.group(2)
    return None


def add_admins_from_codes(codes: List[str]) -> int:
    """Agrega una lista de códigos/emails como administradores en session_state.
       Retorna la cantidad de IDs añadidos (nuevos).
       Uso típico (desde cualquier módulo): utils.microsoft_auth.add_admins_from_codes(["jua25837@uvg.edu.gt"])
    """
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
    """Conveniencia para agregar un solo código/email. Retorna True si se añadió."""
    return add_admins_from_codes([code]) == 1