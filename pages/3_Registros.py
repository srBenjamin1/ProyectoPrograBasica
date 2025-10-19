import streamlit as st
from datetime import date
from utils.db import list_alumnos, list_lugares, insert_registro, list_registros
from utils.auth import require_login, render_userbox, current_role, current_alumno_id, current_user

st.set_page_config(
    page_title="Registros",
    page_icon=":material/app_registration:",
    layout="wide"
)

render_userbox()
require_login()

st.title(":material/app_registration: Registros")

rol = current_role()
# Cargar catálogos
alumnos = list_alumnos()
lugares = list_lugares()

if alumnos.empty or lugares.empty:
    st.warning("Debes tener al menos un alumno y un lugar para crear registros.")
else:
    with st.form("form_registro", clear_on_submit=True):
        c1, c2 = st.columns(2)
        if rol == 'Estudiante':
            aid = current_alumno_id()
            if not aid:
                st.error("Tu cuenta no está vinculada a un alumno. Contacta al administrador.")
                st.stop()
            # Mostrar sólo su propio alumno (bloqueado)
            alumno_label = alumnos[alumnos['id']==aid]['nombre'].iloc[0] if (alumnos['id']==aid).any() else f"ID {aid}"
            c1.text_input("Alumno", value=f"{aid} - {alumno_label}", disabled=True)
            alumno_id = aid
        else:
            with c1:
                alumno_row = st.selectbox(
                    "Alumno", 
                    alumnos.to_dict("records"), 
                    format_func=lambda r: f"{r['id']} - {r['nombre']}"
                )
                alumno_id = alumno_row['id']
        with c2:
            lugar_row = st.selectbox(
                "Lugar", 
                lugares.to_dict("records"), 
                format_func=lambda r: f"{r['id']} - {r['nombre']}"
            )
        actividad = st.text_input("Actividad")
        c3, c4, c5 = st.columns(3)
        with c3:
            fecha = st.date_input("Fecha", value=date.today())
        with c4:
            horas = st.number_input("Horas", min_value=0.0, step=0.5, format="%.2f")
        with c5:
            anio = st.number_input("Año", min_value=2000, max_value=2100, value=date.today().year, step=1)
        semestre = st.selectbox("Semestre", [1, 2], index=0)
        submitted = st.form_submit_button(":material/add: Agregar registro")
        if submitted:
            if not actividad:
                st.warning("Escribe una actividad.")
            elif horas <= 0:
                st.warning("Horas debe ser mayor a 0.")
            else:
                rid = insert_registro(
                    alumno_id, lugar_row['id'], actividad, fecha, horas, 
                    anio, semestre, usuario=current_user()
                )
                st.success(f"Registro agregado con ID {rid} (pendiente de validación)")
                st.rerun()

st.divider()

st.subheader("Listado de registros")
show_pend = st.checkbox("Ver solo pendientes", value=False)
# Si es estudiante, filtrar por su alumno
if current_role() == 'Estudiante':
    sel_al = str(current_alumno_id())
else:
    sel_al = st.selectbox(
        "Filtrar por alumno (opcional)", 
        ["Todos"] + alumnos["id"].astype(str).tolist()
    ) if not alumnos.empty else "Todos"

sel_anio = st.number_input("Año (opcional)", min_value=0, max_value=9999, value=0, step=1)
sel_sem = st.selectbox("Semestre (opcional)", ["-", 1, 2], index=0)

kwargs = {}
if show_pend:
    kwargs['pendientes'] = True
if sel_al != "Todos":
    kwargs['alumno_id'] = int(sel_al)
if sel_anio != 0:
    kwargs['anio'] = int(sel_anio)
if sel_sem != "-":
    kwargs['semestre'] = int(sel_sem)

reg_df = list_registros(**kwargs)
if reg_df.empty:
    st.info("No hay registros con ese filtro.")
else:
    display_df = reg_df.drop(columns=["alumno_id", "lugar_id"], errors='ignore')
    st.dataframe(display_df, use_container_width=True)

    csv_bytes = display_df.to_csv(index=False).encode('utf-8-sig')
    default_name = f"registros_{sel_al}_{sel_anio}_{sel_sem if sel_sem!='-' else 'all'}.csv"
    st.download_button(
        label=":material/download: Exportar CSV (filtro actual)",
        data=csv_bytes,
        file_name=default_name,
        mime="text/csv",
        use_container_width=True
    )

    # Exportar TODO (ignora filtros)
    st.markdown("### :material/download: Exportar TODO")
    try:
        _all_df = list_registros()
        _all_display = _all_df.drop(columns=["alumno_id","lugar_id"], errors='ignore')
        if not _all_display.empty:
            st.download_button(
                label="Exportar TODO (CSV)",
                data=_all_display.to_csv(index=False).encode('utf-8-sig'),
                file_name="registros_TODO.csv",
                mime="text/csv",
                use_container_width=True
            )
        else:
            st.caption("No hay datos globales para exportar.")
    except Exception as e:
        st.caption(f"No se pudo generar el CSV global: {e}")