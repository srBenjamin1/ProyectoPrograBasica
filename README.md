# Proyecto: Gestión de Horas de Extensión (Prototipo CLI)

## 📌 Descripción
Este proyecto es un **prototipo en Python** que permite gestionar las **horas de extensión universitaria** requeridas por los estudiantes.
Está diseñado como una **aplicación de consola** para registrar alumnos, lugares (empresas), actividades realizadas y validar dichas horas.

## 🎯 Objetivo
Facilitar el control de las horas de extensión, requisito obligatorio para los estudiantes, mediante un sistema simple que:
- Registre alumnos y lugares autorizados.
- Cree registros de actividades con horas trabajadas.
- Valide las horas por parte de un responsable.
- Consulte el estado de cumplimiento por semestre.

## 🛠️ Funcionalidades
- **Agregar alumno**: nombre y carrera.
- **Agregar lugar**: nombre de la empresa o institución.
- **Agregar registro**: actividad, fecha, horas, semestre, alumno y lugar.
- **Validar registro**: marcar como validado e indicar el validador.
- **Ver estado**: muestra horas totales, validadas y faltantes por alumno y semestre.
- **Ver pendientes**: lista registros sin validar.
- **Listar alumnos y lugares**.

## 📂 Estructura de datos
- `alumnos`: lista de diccionarios con `id`, `nombre`, `carrera`.
- `lugares`: lista de diccionarios con `id`, `nombre`.
- `registros`: lista de diccionarios con:
  - `id`, `alumno_id`, `lugar_id`, `actividad`, `fecha`, `horas`, `semestre`, `validado`, `validador`.

## ⚙️ Requisitos
- **Python 3.x**
- No requiere librerías externas (solo `input()` y estructuras básicas).

## ▶️ Ejecución
1. Clonar o descargar el archivo `Código Proyecto.py`.
2. Ejecutar en consola:
   ```bash
   python Ruta\ Proyecto.py
   ```
3. Seguir el menú interactivo:
```bash
--- MENU ---
1) Agregar alumno
2) Agregar lugar
3) Agregar registro
4) Validar
5) Ver estado
6) Ver pendientes
7) Ver alumnos
8) Ver lugares
0) Salir
```
##  💻 Estado actual
Prototipo funcional en memoria (los datos se pierden al cerrar).
Sin validación avanzada de entradas (fecha, horas, IDs).
Sin persistencia en disco ni interfaz gráfica.

## Cosas pendientes a agregar
Agregar validaciones robustas (fechas, números, IDs).
Implementar persistencia (JSON o base de datos).
Exportar reportes (CSV/Excel).
Migrar a interfaz web (Flask/FastAPI) o GUI.
Manejo de roles (estudiante, validador).
