"""
Módulo de acceso a datos (DuckDB) para la app de horas de extensión.
Incluye:
- Esquema de BD (alumnos, lugares, registros, usuarios, auditoria)
- Borrado lógico (campo "activo") en alumnos y lugares
- Funciones CRUD y de consulta
- Bitácora de auditoría (auditoria)
- Autenticación con cuentas locales (hash PBKDF2)
"""
import os
import json
import hmac
import hashlib
import base64
from datetime import date, datetime
from typing import Optional, Tuple, Dict, Any

import duckdb
import pandas as pd

DB_PATH = os.getenv("EXT_DB_PATH", os.path.join("data", "extension.duckdb"))

# Asegurar carpeta
os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)

# Conexión única por proceso
_con = None

# ------------------ Utilidades internas ------------------

def _pbkdf2_hash(password: str, salt: bytes = None, iterations: int = 100_000) -> Dict[str, Any]:
    """Devuelve diccionario con salt, iteraciones y hash (base64)."""
    if salt is None:
        salt = os.urandom(16)
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iterations)
    return {
        'salt_b64': base64.b64encode(salt).decode('ascii'),
        'iters': iterations,
        'hash_b64': base64.b64encode(dk).decode('ascii')
    }


def _pbkdf2_verify(password: str, salt_b64: str, iters: int, hash_b64: str) -> bool:
    salt = base64.b64decode(salt_b64.encode('ascii'))
    expected = base64.b64decode(hash_b64.encode('ascii'))
    dk = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, iters)
    return hmac.compare_digest(dk, expected)


def _serialize_for_json(obj: Any) -> Any:
    """
    Convierte objetos no serializables a formatos JSON compatibles.
    Maneja Timestamp de pandas, datetime, date, etc.
    """
    if isinstance(obj, dict):
        return {k: _serialize_for_json(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [_serialize_for_json(item) for item in obj]
    elif isinstance(obj, (pd.Timestamp)):
        return obj.isoformat()
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, (pd.Series)):
        return _serialize_for_json(obj.to_dict())
    elif isinstance(obj, (pd.DataFrame)):
        return obj.to_dict('records')
    elif pd.isna(obj):
        return None
    else:
        return obj


def get_con():
    global _con
    if _con is None:
        _con = duckdb.connect(DB_PATH)
        _con.execute("PRAGMA threads=4;")
        init_db(_con)
    return _con


# ------------------ Inicialización de BD ------------------

def init_db(con=None):
    """Crea tablas si no existen y semilla usuarios DEMO si están vacías."""
    con = con or get_con()

    # Alumnos con borrado lógico
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS alumnos (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR NOT NULL,
            carrera VARCHAR NOT NULL,
            activo BOOLEAN NOT NULL DEFAULT TRUE
        );
        """
    )

    # Lugares con borrado lógico
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS lugares (
            id INTEGER PRIMARY KEY,
            nombre VARCHAR NOT NULL,
            activo BOOLEAN NOT NULL DEFAULT TRUE
        );
        """
    )

    # Registros (hechos); no se borran por FK, se recomienda no eliminarlos para conservar historia
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS registros (
            id INTEGER PRIMARY KEY,
            alumno_id INTEGER NOT NULL,
            lugar_id INTEGER NOT NULL,
            actividad VARCHAR NOT NULL,
            fecha DATE NOT NULL,
            horas DECIMAL(10,2) NOT NULL CHECK (horas > 0),
            anio INTEGER NOT NULL,
            semestre INTEGER NOT NULL CHECK (semestre IN (1,2)),
            validado BOOLEAN NOT NULL DEFAULT FALSE,
            validador VARCHAR,
            FOREIGN KEY (alumno_id) REFERENCES alumnos(id),
            FOREIGN KEY (lugar_id) REFERENCES lugares(id)
        );
        """
    )

    # Auditoría de cambios (bitácora)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS auditoria (
            id BIGINT PRIMARY KEY,
            ts TIMESTAMP NOT NULL,
            usuario VARCHAR,
            accion VARCHAR NOT NULL,          -- INSERT/UPDATE/DELETE/VALIDAR
            tabla VARCHAR NOT NULL,           -- alumnos/lugares/registros
            entity_id BIGINT,                -- id de la entidad afectada
            before_json VARCHAR,             -- estado previo (JSON)
            after_json VARCHAR               -- estado posterior (JSON)
        );
        """
    )

    # Usuarios locales (login)
    con.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY,
            username VARCHAR UNIQUE NOT NULL,
            role VARCHAR NOT NULL,           -- Estudiante/Empresa/Departamento/Admin
            alumno_id INTEGER,               -- (opcional) link al alumno si rol = Estudiante
            salt_b64 VARCHAR NOT NULL,
            iters INTEGER NOT NULL,
            hash_b64 VARCHAR NOT NULL,
            FOREIGN KEY (alumno_id) REFERENCES alumnos(id)
        );
        """
    )

    # Crear o reiniciar secuencias basándose en el MAX(id) existente
    _init_sequence(con, 'seq_alumnos', 'alumnos')
    _init_sequence(con, 'seq_lugares', 'lugares')
    _init_sequence(con, 'seq_registros', 'registros')
    _init_sequence(con, 'seq_auditoria', 'auditoria')
    _init_sequence(con, 'seq_usuarios', 'usuarios')

    # Semilla de usuarios si está vacío
    n_users = con.execute("SELECT COUNT(*) FROM usuarios").fetchone()[0]
    if n_users == 0:
        # Crea 4 usuarios demo (contraseña 1234). Para Estudiante no asignamos alumno aún.
        for uname, role in [("estudiante","Estudiante"),("empresa","Empresa"),("depto","Departamento"),("admin","Admin")]:
            h = _pbkdf2_hash("1234")
            con.execute(
                "INSERT INTO usuarios (id, username, role, alumno_id, salt_b64, iters, hash_b64) VALUES (nextval('seq_usuarios'),?,?,?,?,?,?)",
                [uname, role, None, h['salt_b64'], h['iters'], h['hash_b64']]
            )


def _init_sequence(con, seq_name: str, table_name: str) -> None:
    """
    Crea o reinicia una secuencia basándose en el MAX(id) de la tabla.
    Esto previene conflictos de primary key.
    """
    # Verificar si la secuencia existe
    try:
        # Intentar eliminar la secuencia si existe
        con.execute(f"DROP SEQUENCE IF EXISTS {seq_name};")
    except Exception:
        # Si falla, continuar (la secuencia no existe o no se puede eliminar)
        pass
    
    # Obtener el máximo ID actual de la tabla
    try:
        max_id = con.execute(f"SELECT COALESCE(MAX(id), 0) FROM {table_name}").fetchone()[0]
    except Exception:
        max_id = 0
    
    # Crear secuencia comenzando desde max_id + 1
    start_value = max_id + 1
    try:
        con.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq_name} START {start_value};")
    except Exception:
        # Si la secuencia ya existe, intentar resetearla
        try:
            con.execute(f"ALTER SEQUENCE {seq_name} RESTART WITH {start_value};")
        except Exception:
            # Si todo falla, simplemente continuar
            pass


# ------------------ Auditoría ------------------

def _audit(accion: str, tabla: str, entity_id: int, before: Optional[dict], after: Optional[dict], usuario: Optional[str]):
    con = get_con()
    # Serializar los objetos antes de convertir a JSON
    before_serialized = _serialize_for_json(before) if before else None
    after_serialized = _serialize_for_json(after) if after else None
    
    con.execute(
        "INSERT INTO auditoria (id, ts, usuario, accion, tabla, entity_id, before_json, after_json) VALUES (nextval('seq_auditoria'), ?, ?, ?, ?, ?, ?, ?)",
        [
            datetime.now(), 
            usuario, 
            accion, 
            tabla, 
            entity_id, 
            json.dumps(before_serialized) if before_serialized else None, 
            json.dumps(after_serialized) if after_serialized else None
        ]
    )


# ------------------ Helpers de IDs ------------------

def _next_id(seq_name: str) -> int:
    con = get_con()
    return con.execute(f"SELECT nextval('{seq_name}')").fetchone()[0]


# ------------------ CRUD Alumnos (con borrado lógico) ------------------

def insert_alumno(nombre: str, carrera: str, usuario: Optional[str] = None) -> int:
    con = get_con()
    new_id = _next_id('seq_alumnos')
    con.execute("INSERT INTO alumnos (id, nombre, carrera, activo) VALUES (?, ?, ?, TRUE)", [new_id, nombre.strip(), carrera.strip()])
    _audit('INSERT','alumnos', new_id, None, {"id": new_id, "nombre": nombre, "carrera": carrera, "activo": True}, usuario)
    return new_id


def list_alumnos(incluir_inactivos: bool = False) -> pd.DataFrame:
    con = get_con()
    if incluir_inactivos:
        return con.execute("SELECT id, nombre, carrera, activo FROM alumnos ORDER BY id").df()
    else:
        return con.execute("SELECT id, nombre, carrera, activo FROM alumnos WHERE activo = TRUE ORDER BY id").df()


def soft_delete_alumno(alumno_id: int, usuario: Optional[str] = None) -> None:
    con = get_con()
    before = con.execute("SELECT id, nombre, carrera, activo FROM alumnos WHERE id=?", [alumno_id]).fetchone()
    if not before:
        return
    before_d = {"id": before[0], "nombre": before[1], "carrera": before[2], "activo": before[3]}
    con.execute("UPDATE alumnos SET activo = FALSE WHERE id = ?", [alumno_id])
    after_d = dict(before_d)
    after_d['activo'] = False
    _audit('DELETE','alumnos', alumno_id, before_d, after_d, usuario)


def restore_alumno(alumno_id: int, usuario: Optional[str] = None) -> None:
    con = get_con()
    before = con.execute("SELECT id, nombre, carrera, activo FROM alumnos WHERE id=?", [alumno_id]).fetchone()
    if not before:
        return
    before_d = {"id": before[0], "nombre": before[1], "carrera": before[2], "activo": before[3]}
    con.execute("UPDATE alumnos SET activo = TRUE WHERE id = ?", [alumno_id])
    after_d = dict(before_d)
    after_d['activo'] = True
    _audit('UPDATE','alumnos', alumno_id, before_d, after_d, usuario)


# ------------------ CRUD Lugares (con borrado lógico) ------------------

def insert_lugar(nombre: str, usuario: Optional[str] = None) -> int:
    con = get_con()
    new_id = _next_id('seq_lugares')
    con.execute("INSERT INTO lugares (id, nombre, activo) VALUES (?, ?, TRUE)", [new_id, nombre.strip()])
    _audit('INSERT','lugares', new_id, None, {"id": new_id, "nombre": nombre, "activo": True}, usuario)
    return new_id


def list_lugares(incluir_inactivos: bool = False) -> pd.DataFrame:
    con = get_con()
    if incluir_inactivos:
        return con.execute("SELECT id, nombre, activo FROM lugares ORDER BY id").df()
    else:
        return con.execute("SELECT id, nombre, activo FROM lugares WHERE activo = TRUE ORDER BY id").df()


def soft_delete_lugar(lugar_id: int, usuario: Optional[str] = None) -> None:
    con = get_con()
    before = con.execute("SELECT id, nombre, activo FROM lugares WHERE id=?", [lugar_id]).fetchone()
    if not before:
        return
    before_d = {"id": before[0], "nombre": before[1], "activo": before[2]}
    con.execute("UPDATE lugares SET activo = FALSE WHERE id = ?", [lugar_id])
    after_d = dict(before_d)
    after_d['activo'] = False
    _audit('DELETE','lugares', lugar_id, before_d, after_d, usuario)


def restore_lugar(lugar_id: int, usuario: Optional[str] = None) -> None:
    con = get_con()
    before = con.execute("SELECT id, nombre, activo FROM lugares WHERE id=?", [lugar_id]).fetchone()
    if not before:
        return
    before_d = {"id": before[0], "nombre": before[1], "activo": before[2]}
    con.execute("UPDATE lugares SET activo = TRUE WHERE id = ?", [lugar_id])
    after_d = dict(before_d)
    after_d['activo'] = True
    _audit('UPDATE','lugares', lugar_id, before_d, after_d, usuario)


# ------------------ Registros ------------------

def insert_registro(alumno_id: int, lugar_id: int, actividad: str, fecha: date, horas: float, anio: int, semestre: int, usuario: Optional[str] = None) -> int:
    con = get_con()
    new_id = _next_id('seq_registros')
    con.execute(
        """
        INSERT INTO registros
        (id, alumno_id, lugar_id, actividad, fecha, horas, anio, semestre, validado, validador)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, FALSE, NULL)
        """,
        [new_id, alumno_id, lugar_id, actividad.strip(), str(fecha), float(horas), int(anio), int(semestre)]
    )
    _audit('INSERT','registros', new_id, None, {
        "id": new_id, "alumno_id": alumno_id, "lugar_id": lugar_id,
        "actividad": actividad, "fecha": str(fecha), "horas": float(horas),
        "anio": int(anio), "semestre": int(semestre), "validado": False, "validador": None
    }, usuario)
    return new_id


def list_registros(pendientes: bool = False, alumno_id: Optional[int] = None,
                   anio: Optional[int] = None, semestre: Optional[int] = None, incluir_inactivos: bool = False) -> pd.DataFrame:
    con = get_con()
    where = []
    params = []
    if pendientes:
        where.append("r.validado = FALSE")
    if alumno_id is not None:
        where.append("r.alumno_id = ?")
        params.append(alumno_id)
    if anio is not None:
        where.append("r.anio = ?")
        params.append(anio)
    if semestre is not None:
        where.append("r.semestre = ?")
        params.append(semestre)
    if not incluir_inactivos:
        where.append("a.activo = TRUE AND l.activo = TRUE")
    where_sql = (" WHERE " + " AND ".join(where)) if where else ""
    sql = f"""
        SELECT r.id, a.nombre AS alumno, l.nombre AS lugar, r.actividad, r.fecha,
               r.horas, r.anio, r.semestre, r.validado, r.validador,
               r.alumno_id, r.lugar_id
        FROM registros r
        JOIN alumnos a ON a.id = r.alumno_id
        JOIN lugares l ON l.id = r.lugar_id
        {where_sql}
        ORDER BY r.fecha DESC, r.id DESC
    """
    return con.execute(sql, params).df()


def validar_registro(registro_id: int, validador: str, usuario: Optional[str] = None) -> None:
    con = get_con()
    before = con.execute("SELECT * FROM registros WHERE id=?", [registro_id]).fetchdf()
    con.execute("UPDATE registros SET validado = TRUE, validador = ? WHERE id = ?", [validador.strip(), registro_id])
    after = con.execute("SELECT * FROM registros WHERE id=?", [registro_id]).fetchdf()
    
    # Convertir DataFrames a dicts y serializar
    before_dict = before.iloc[0].to_dict() if not before.empty else None
    after_dict = after.iloc[0].to_dict() if not after.empty else None
    
    _audit('VALIDAR','registros', registro_id, before_dict, after_dict, usuario)


def estado_alumno(alumno_id: int, anio: int, semestre: int) -> Tuple[float, float]:
    con = get_con()
    row = con.execute(
        """
        SELECT 
          COALESCE(SUM(horas), 0) AS total,
          COALESCE(SUM(CASE WHEN validado THEN horas ELSE 0 END), 0) AS validadas
        FROM registros
        WHERE alumno_id = ? AND anio = ? AND semestre = ?
        """,
        [alumno_id, anio, semestre]
    ).fetchone()
    return float(row[0]), float(row[1])


# ------------------ Usuarios locales (login) ------------------

def create_user(username: str, password: str, role: str, alumno_id: Optional[int] = None) -> int:
    """Crea usuario local con hash PBKDF2. Devuelve id."""
    con = get_con()
    new_id = _next_id('seq_usuarios')
    h = _pbkdf2_hash(password)
    con.execute(
        "INSERT INTO usuarios (id, username, role, alumno_id, salt_b64, iters, hash_b64) VALUES (?,?,?,?,?,?,?)",
        [new_id, username.strip().lower(), role, alumno_id, h['salt_b64'], h['iters'], h['hash_b64']]
    )
    _audit('INSERT','usuarios', new_id, None, {"username": username, "role": role, "alumno_id": alumno_id}, username)
    return new_id


def verify_user(username: str, password: str) -> Optional[dict]:
    """Verifica credenciales y devuelve dict con info del usuario si es válido."""
    con = get_con()
    row = con.execute("SELECT id, username, role, alumno_id, salt_b64, iters, hash_b64 FROM usuarios WHERE username = ?", [username.strip().lower()]).fetchone()
    if not row:
        return None
    ok = _pbkdf2_verify(password, row[4], int(row[5]), row[6])
    if not ok:
        return None
    return {"id": row[0], "username": row[1], "role": row[2], "alumno_id": row[3]}