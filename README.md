# Proyecto: Gestión de Horas de Extensión (Prototipo — Streamlit + DuckDB)

## 📌 Descripción
Este proyecto es un prototipo en Python para gestionar las **horas de extensión universitaria**. Ha evolucionado de una utilidad de consola a una aplicación web ligera usando **Streamlit** con persistencia en **DuckDB**. Incluye además soporte opcional de autenticación con Microsoft (OAuth / PKCE).

## 🧩 Tecnologías principales
- Python 3.x
- Streamlit (interfaz web)
- DuckDB (base de datos embebida, archivo en data/extension.duckdb)
- Requests (para llamadas a Microsoft Graph cuando se usa OAuth)
- Dotenv (lectura de variables de entorno)
- PBKDF2-HMAC-SHA256 para hashing de contraseñas locales

## 📂 Estructura relevante (resumen)
- 0_Inicio.py — Pantalla principal y gestión de sesión en Streamlit.
- utils/db.py — Acceso a datos con DuckDB:
  - Tablas: alumnos, lugares, registros, auditoria, usuarios.
  - Borrado lógico (campo `activo`) en alumnos y lugares.
  - Auditoría de cambios (tabla `auditoria`).
  - Usuarios locales con hash PBKDF2.
- utils/microsoft_auth.py — Flujo OAuth opcional con Microsoft (PKCE si no hay client secret), validación de dominio `@uvg.edu.gt`, utilidades para administrar admins en sesión.
- .env — Variables de configuración (AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, REDIRECT_URI, EXT_DB_PATH, MICROSOFT_ADMIN_STUDENTS).

## 🎯 Funcionalidades actuales
- Interfaz web con Streamlit para:
  - Registrar alumnos y lugares.
  - Crear registros de actividades (actividad, fecha, horas, año, semestre).
  - Validar registros (marcar validados y registrar validador).
  - Consultar estado por alumno/semestre (total, validadas, faltantes).
  - Listar pendientes, alumnos y lugares.
  - Gestión básica de usuarios locales (login) y sesión.
- Persistencia en DuckDB con esquemas y secuencias.
- Auditoría de operaciones (INSERT/UPDATE/DELETE/VALIDAR) con before/after en JSON.
- Login local con contraseñas hasheadas (PBKDF2) y verificación segura.
- Soporte opcional: Login con Microsoft (requiere configurar AZURE_CLIENT_ID y REDIRECT_URI). El flujo valida que el correo pertenezca al dominio `@uvg.edu.gt` y determina rol según el formato del correo y una lista de estudiantes-admins en session_state o .env.

## ⚙️ Requisitos
- Python 3.8+
- Instalar dependencias (ejemplo):
  pip install streamlit duckdb pandas python-dotenv requests

## ▶️ Ejecución (desarrollo)
1. Asegúrate de tener las dependencias instaladas.
2. Configura variables en `.env` (ver sección abajo).
3. Ejecuta la app:
   streamlit run 0_Inicio.py
4. Abre el navegador en la URL que Streamlit muestre (por defecto http://localhost:8501).

## 🔐 Variables de entorno (.env)
- EXT_DB_PATH: ruta al archivo DuckDB (ej: data/extension.duckdb)
- AZURE_CLIENT_ID: Client ID para Microsoft OAuth (opcional)
- AZURE_CLIENT_SECRET: Client Secret (opcional; si no existe se usa PKCE)
- REDIRECT_URI: URI de redirección registrada (ej: http://localhost:8501)
- MICROSOFT_ADMIN_STUDENTS: lista CSV de IDs de estudiante que serán admins por defecto (ej: "25837")

Ejemplo (ya incluido en proyecto):
EXT_DB_PATH=data/extension.duckdb
AZURE_CLIENT_ID=...
REDIRECT_URI=http://localhost:8501
MICROSOFT_ADMIN_STUDENTS="25837"

## 🔎 Notas de seguridad y despliegue
- No incluir secretos reales (.env) en repositorios públicos.
- Si usas AZURE_CLIENT_SECRET trátalo como secreto (Secret Manager / variables de entorno en CI/CD).
- Las contraseñas locales están hasheadas con PBKDF2; para mayor seguridad ajustar iteraciones y políticas.
- DuckDB crea un archivo en disco; hacer backups si es necesario.
- El flujo de Microsoft implementado valida dominio `@uvg.edu.gt` pero no integra con Azure AD Enterprise (es flujo público con Graph API).

## 🛠️ Limitaciones y tareas pendientes
- Validación robusta de entradas (fechas, IDs, límites de horas).
- Interfaz administrativa para gestionar usuarios y vincular alumnos a cuentas.
- Persistir la lista de admins de Microsoft en BD o un servicio, actualmente está en session_state.
- Exportar reportes (CSV/Excel) y paginación en listados grandes.
- Tests automatizados y CI/CD.
- Considerar migración a un servidor backend (FastAPI/Flask) si la app crece.

## 🧪 Usuarios demo
La base de datos se inicializa con usuarios demo si la tabla `usuarios` está vacía:
- admin / 1234 → Rol: Admin
- depto / 1234 → Rol: Departamento
- empresa / 1234 → Rol: Empresa
- estudiante / 1234 → Rol: Estudiante

---

Si quieres, puedo también:
- Actualizar el README con ejemplos de endpoints SQL o consultas frecuentes.
- Añadir instrucciones de despliegue en Docker o en un servidor (Streamlit Sharing / Heroku / Azure).
