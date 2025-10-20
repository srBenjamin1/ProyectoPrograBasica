# Proyecto: Gestión de Horas de Extensión — Guía rápida para usuarios

Objetivo: que cualquier usuario pueda ejecutar la aplicación localmente con mínimos pasos.

## Resumen rápido
Esta es una app prototipo en Python que gestiona horas de extensión. Usa Streamlit para la interfaz y DuckDB para persistencia local. Opcionalmente puede usar login con Microsoft (OAuth). No se requieren conocimientos avanzados.

## Requisitos
- Python 3.8+ instalado
- Conexión a internet sólo si vas a usar autenticación Microsoft
- (Opcional) Cuenta Microsoft institucional para SSO

## Instalación y ejecución (paso a paso)

1) Clonar el repositorio
- Windows / macOS / Linux:
  ```bash
  git clone <tu-repo-url>
  cd ProyectoPrograBasica
  ```

2) Crear y activar un entorno virtual
- Windows (PowerShell):
  ```bash
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  ```
- Windows (cmd):
  ```bash
  python -m venv .venv
  .\.venv\Scripts\activate
  ```
- macOS / Linux:
  ```bash
  python3 -m venv .venv
  source .venv/bin/activate
  ```

3) Instalar dependencias
- Recomendado:
  ```bash
  pip install streamlit duckdb pandas python-dotenv requests
  ```

4) Configurar variables (archivo .env)
- Crea un archivo `.env` en la raíz del proyecto con los valores mínimos.
- Ejemplo mínimo (no incluyas secretos reales):
  ```env
  EXT_DB_PATH=data/extension.duckdb
  # Opcional (Microsoft OAuth)
  # AZURE_CLIENT_ID=tu-client-id
  # AZURE_CLIENT_SECRET=tu-secret  # opcional, si no hay se usa PKCE
  # REDIRECT_URI=http://localhost:8501
  # MICROSOFT_ADMIN_STUDENTS="25837"
  ```

- Si no configuras AZURE_CLIENT_ID, la app funcionará con login local (usuarios demo).

5) Ejecutar la aplicación
  ```bash
  python -m streamlit run 0_Inicio.py
  ```
- Abre el navegador en la URL que Streamlit muestre (por defecto http://localhost:8501)

## Usuarios demo (inicialización automática)
Al ejecutar por primera vez, la BD se inicializa con usuarios demo:
- admin / 1234 → Rol: Admin
- depto / 1234 → Rol: Departamento
- empresa / 1234 → Rol: Empresa
- estudiante / 1234 → Rol: Estudiante

Usa estos para acceder si no configuraste usuarios reales.

## Reiniciar o recrear la base de datos
- Para limpiar todo (borrar datos) elimina el archivo definido en EXT_DB_PATH (por defecto data/extension.duckdb), luego ejecuta Streamlit otra vez; la app recreará la BD y sembrará usuarios demo.
  ```bash
  rm data/extension.duckdb   (macOS/Linux)
  del data\extension.duckdb  (Windows)
  ```

O desde Python si prefieres:
  ```bash
  python -c "from utils.db import init_db; init_db()"
  ```

## Autenticación Microsoft (opcional)
- Si quieres usar "Iniciar sesión con Microsoft":
  1. Registra una app en Azure (App registrations) y copia el Client ID.
  2. Opcionalmente añade Client Secret si tu app es "confidential".
  3. Configura REDIRECT_URI (ej: http://localhost:8501) en la app de Azure y en tu `.env`.
  4. Añade AZURE_CLIENT_ID (y opcionalmente AZURE_CLIENT_SECRET) al `.env`.
- Si no lo configuras, el botón de Microsoft mostrará instrucciones en la UI.

## Solución de problemas comunes
- "streamlit: comando no encontrado": asegúrate de activar el entorno virtual o instala globalmente `pip install streamlit`.
- Puerto 8501 ocupado: Streamlit mostrará otro puerto en la salida o usa `streamlit run 0_Inicio.py --server.port 8502`.
- Errores al conectar con Microsoft: revisa REDIRECT_URI en Azure y que AZURE_CLIENT_ID esté correcto.
- Si ves credenciales antiguas o errores de sesión: reinicia la app o borra el archivo `.streamlit/` y vuelve a iniciar.

## Seguridad y buenas prácticas
- No subir `.env` con secretos a repositorios públicos.
- Para producción, guarda secretos en un servicio seguro (Secret Manager).
- Incrementa iteraciones PBKDF2 si vas a usar la app en entorno con usuarios reales.

## ¿Qué sigue?
- Validaciones de entrada más estrictas (fechas/horas).
- Interfaz administrativa para crear usuarios.
- Exportar reportes (CSV/Excel).

---