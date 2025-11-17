import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from utils.db import get_con
from utils.auth import require_login, render_userbox, has_role

st.set_page_config(
    page_title="Dashboard",
    page_icon=":material/dashboard:",
    layout="wide"
)

render_userbox()
require_login()

st.title(":material/dashboard: Dashboard de Horas de Extensión")

# Verificar permisos (Admin, Departamento)
if not has_role({'Admin', 'Departamento', 'Docente'}):
    st.warning("⚠️ Esta página es solo para Administradores y Departamento")
    st.stop()

# Obtener conexión a la BD
con = get_con()

# Cargar datos
@st.cache_data(ttl=60)
def load_data():
    """Carga datos de registros con información de alumnos y lugares"""
    query = """
    SELECT 
        r.id,
        a.nombre AS alumno,
        l.nombre AS lugar,
        r.actividad,
        r.fecha,
        r.horas,
        r.anio,
        r.semestre,
        r.validado,
        r.validador
    FROM registros r
    JOIN alumnos a ON a.id = r.alumno_id
    JOIN lugares l ON l.id = r.lugar_id
    WHERE a.activo = TRUE AND l.activo = TRUE
    ORDER BY r.fecha DESC
    """
    df = con.execute(query).df()
    if not df.empty:
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['mes'] = df['fecha'].dt.to_period('M').astype(str)
        df['mes_num'] = df['fecha'].dt.month
        df['anio_completo'] = df['fecha'].dt.year
    return df

try:
    df = load_data()
    
    if df.empty:
        st.info("📊 No hay datos para mostrar. Agrega registros primero.")
        st.stop()
    
    # Métricas principales
    st.markdown("### :material/analytics: Métricas Generales")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        total_horas = df['horas'].sum()
        st.metric(
            ":material/schedule: Total de Horas",
            f"{total_horas:,.1f}",
            help="Suma de todas las horas registradas"
        )
    
    with col2:
        total_registros = len(df)
        st.metric(
            ":material/assignment: Total Registros",
            f"{total_registros:,}",
            help="Cantidad total de registros"
        )
    
    with col3:
        horas_validadas = df[df['validado'] == True]['horas'].sum()
        st.metric(
            ":material/verified: Horas Validadas",
            f"{horas_validadas:,.1f}",
            help="Horas que han sido validadas"
        )
    
    with col4:
        pendientes = len(df[df['validado'] == False])
        st.metric(
            ":material/pending: Pendientes",
            f"{pendientes:,}",
            delta=f"-{pendientes}" if pendientes > 0 else "✓",
            delta_color="inverse",
            help="Registros pendientes de validación"
        )
    
    st.divider()
    
    # Filtros
    with st.expander(":material/filter_alt: Filtros", expanded=False):
        col1, col2, col3 = st.columns(3)
        
        with col1:
            anios_disponibles = sorted(df['anio'].unique())
            anio_filtro = st.multiselect(
                "Año",
                options=anios_disponibles,
                default=anios_disponibles,
                help="Filtra por año académico"
            )
        
        with col2:
            semestres_disponibles = sorted(df['semestre'].unique())
            semestre_filtro = st.multiselect(
                "Semestre",
                options=semestres_disponibles,
                default=semestres_disponibles
            )
        
        with col3:
            validado_filtro = st.selectbox(
                "Estado",
                options=["Todos", "Validados", "Pendientes"]
            )
        
        # Aplicar filtros
        df_filtrado = df.copy()
        if anio_filtro:
            df_filtrado = df_filtrado[df_filtrado['anio'].isin(anio_filtro)]
        if semestre_filtro:
            df_filtrado = df_filtrado[df_filtrado['semestre'].isin(semestre_filtro)]
        if validado_filtro == "Validados":
            df_filtrado = df_filtrado[df_filtrado['validado'] == True]
        elif validado_filtro == "Pendientes":
            df_filtrado = df_filtrado[df_filtrado['validado'] == False]
    
    # Visualizaciones en tabs
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        ":material/person: Por Estudiante",
        ":material/business: Por Lugar",
        ":material/calendar_month: Por Mes",
        ":material/check_circle: Validaciones",
        ":material/bar_chart: Distribución"
    ])
    
    # --- TAB 1: Por Estudiante ---
    with tab1:
        st.markdown("### :material/school: Total de Horas por Estudiante")
        
        horas_por_alumno = df_filtrado.groupby('alumno')['horas'].sum().sort_values(ascending=False)
        
        if not horas_por_alumno.empty:
            fig = px.bar(
                x=horas_por_alumno.values,
                y=horas_por_alumno.index,
                orientation='h',
                labels={'x': 'Horas Totales', 'y': 'Estudiante'},
                title='Horas Acumuladas por Estudiante',
                color=horas_por_alumno.values,
                color_continuous_scale='Blues'
            )
            fig.update_layout(
                height=max(400, len(horas_por_alumno) * 30),
                showlegend=False,
                xaxis_title="Horas",
                yaxis_title="Estudiante"
            )
            st.plotly_chart(fig, use_container_width=True)
            
            # Top 5
            st.markdown("#### :material/star: Top 5 Estudiantes")
            top5 = horas_por_alumno.head(5).reset_index()
            top5.columns = ['Estudiante', 'Horas']
            top5.index = top5.index + 1
            st.dataframe(top5, use_container_width=True)
        else:
            st.info("No hay datos para mostrar con los filtros seleccionados")
    
    # --- TAB 2: Por Lugar ---
    with tab2:
        st.markdown("### :material/location_on: Análisis por Lugar")
        
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### Promedio de Horas por Lugar")
            prom_lugar = df_filtrado.groupby('lugar')['horas'].mean().sort_values(ascending=False)
            
            if not prom_lugar.empty:
                fig = px.bar(
                    x=prom_lugar.values,
                    y=prom_lugar.index,
                    orientation='h',
                    labels={'x': 'Promedio de Horas', 'y': 'Lugar'},
                    color=prom_lugar.values,
                    color_continuous_scale='Greens'
                )
                fig.update_layout(
                    height=max(300, len(prom_lugar) * 25),
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.markdown("#### Total de Horas por Lugar")
            total_lugar = df_filtrado.groupby('lugar')['horas'].sum().sort_values(ascending=False)
            
            if not total_lugar.empty:
                fig = px.pie(
                    values=total_lugar.values,
                    names=total_lugar.index,
                    title='Distribución de Horas Totales'
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
        
        # Tabla de lugares
        st.markdown("#### :material/table: Resumen por Lugar")
        resumen_lugar = df_filtrado.groupby('lugar').agg({
            'horas': ['sum', 'mean', 'count']
        }).round(2)
        resumen_lugar.columns = ['Total Horas', 'Promedio', 'Cantidad Registros']
        resumen_lugar = resumen_lugar.sort_values('Total Horas', ascending=False)
        st.dataframe(resumen_lugar, use_container_width=True)
    
    # --- TAB 3: Por Mes ---
    with tab3:
        st.markdown("### :material/calendar_today: Registros por Mes")
        
        registros_mes = df_filtrado.groupby('mes').agg({
            'id': 'count',
            'horas': 'sum'
        }).reset_index()
        registros_mes.columns = ['Mes', 'Cantidad Registros', 'Total Horas']
        
        if not registros_mes.empty:
            col1, col2 = st.columns(2)
            
            with col1:
                fig = px.line(
                    registros_mes,
                    x='Mes',
                    y='Cantidad Registros',
                    markers=True,
                    title='Cantidad de Registros por Mes'
                )
                fig.update_traces(line_color='#FF6B6B', line_width=3)
                fig.update_layout(hovermode='x unified')
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                fig = px.bar(
                    registros_mes,
                    x='Mes',
                    y='Total Horas',
                    title='Horas Totales por Mes',
                    color='Total Horas',
                    color_continuous_scale='Oranges'
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Tendencia
            st.markdown("#### :material/trending_up: Tendencia")
            fig = go.Figure()
            fig.add_trace(go.Scatter(
                x=registros_mes['Mes'],
                y=registros_mes['Cantidad Registros'],
                name='Registros',
                mode='lines+markers',
                line=dict(color='#4ECDC4', width=3)
            ))
            fig.add_trace(go.Scatter(
                x=registros_mes['Mes'],
                y=registros_mes['Total Horas'],
                name='Horas',
                mode='lines+markers',
                line=dict(color='#FF6B6B', width=3),
                yaxis='y2'
            ))
            fig.update_layout(
                title='Evolución de Registros y Horas',
                yaxis=dict(title='Cantidad Registros'),
                yaxis2=dict(title='Total Horas', overlaying='y', side='right'),
                hovermode='x unified',
                height=400
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No hay datos para mostrar")
    
    # --- TAB 4: Validaciones ---
    with tab4:
        st.markdown("### :material/fact_check: Estado de Validaciones")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Pie chart de validaciones
            conteo_val = df_filtrado['validado'].value_counts()
            labels = ['Validados' if k else 'Pendientes' for k in conteo_val.index]
            
            fig = px.pie(
                values=conteo_val.values,
                names=labels,
                title='Proporción de Validaciones',
                color_discrete_sequence=['#2ECC71', '#E74C3C']
            )
            fig.update_traces(textposition='inside', textinfo='percent+label+value')
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Horas validadas vs pendientes
            horas_val = df_filtrado.groupby('validado')['horas'].sum()
            labels_horas = ['Validadas' if k else 'Pendientes' for k in horas_val.index]
            
            fig = go.Figure(data=[
                go.Bar(
                    x=labels_horas,
                    y=horas_val.values,
                    marker_color=['#2ECC71', '#E74C3C'],
                    text=horas_val.values.round(1),
                    textposition='auto'
                )
            ])
            fig.update_layout(
                title='Horas: Validadas vs Pendientes',
                yaxis_title='Horas',
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
        # Tasa de validación por estudiante
        st.markdown("#### :material/person_check: Tasa de Validación por Estudiante")
        val_por_alumno = df_filtrado.groupby('alumno').agg({
            'validado': lambda x: (x.sum() / len(x) * 100),
            'horas': 'sum'
        }).round(2)
        val_por_alumno.columns = ['% Validado', 'Total Horas']
        val_por_alumno = val_por_alumno.sort_values('% Validado', ascending=False)
        
        fig = px.scatter(
            val_por_alumno.reset_index(),
            x='Total Horas',
            y='% Validado',
            hover_data=['alumno'],
            size='Total Horas',
            color='% Validado',
            color_continuous_scale='RdYlGn',
            title='Relación entre Horas Totales y Tasa de Validación'
        )
        fig.update_layout(height=500)
        st.plotly_chart(fig, use_container_width=True)
    
    # --- TAB 5: Distribución ---
    with tab5:
        st.markdown("### :material/align_horizontal_left: Distribución de Horas")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Histograma
            fig = px.histogram(
                df_filtrado,
                x='horas',
                nbins=20,
                title='Distribución de Horas por Registro',
                labels={'horas': 'Horas', 'count': 'Frecuencia'},
                color_discrete_sequence=['#9B59B6']
            )
            fig.update_layout(showlegend=False)
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Box plot
            fig = px.box(
                df_filtrado,
                y='horas',
                title='Distribución de Horas (Box Plot)',
                color_discrete_sequence=['#3498DB']
            )
            fig.update_layout(showlegend=False, yaxis_title='Horas')
            st.plotly_chart(fig, use_container_width=True)
        
        # Estadísticas descriptivas
        st.markdown("#### :material/calculate: Estadísticas Descriptivas")
        col1, col2, col3, col4, col5 = st.columns(5)
        
        with col1:
            st.metric("Media", f"{df_filtrado['horas'].mean():.2f}")
        with col2:
            st.metric("Mediana", f"{df_filtrado['horas'].median():.2f}")
        with col3:
            st.metric("Mínimo", f"{df_filtrado['horas'].min():.2f}")
        with col4:
            st.metric("Máximo", f"{df_filtrado['horas'].max():.2f}")
        with col5:
            st.metric("Desv. Est.", f"{df_filtrado['horas'].std():.2f}")
        
        # Distribución por semestre
        st.markdown("#### :material/school: Horas por Semestre")
        horas_semestre = df_filtrado.groupby('semestre')['horas'].sum().reset_index()
        
        fig = px.bar(
            horas_semestre,
            x='semestre',
            y='horas',
            title='Total de Horas por Semestre',
            labels={'semestre': 'Semestre', 'horas': 'Total Horas'},
            color='horas',
            color_continuous_scale='Viridis'
        )
        fig.update_xaxes(type='category')
        st.plotly_chart(fig, use_container_width=True)
    
    # Botón de exportar
    st.divider()
    st.markdown("### :material/download: Exportar Datos")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        csv_data = df_filtrado.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label=":material/table: Exportar Datos Filtrados (CSV)",
            data=csv_data,
            file_name=f"dashboard_datos_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )
    
    with col2:
        resumen = {
            'Total Horas': df_filtrado['horas'].sum(),
            'Total Registros': len(df_filtrado),
            'Promedio Horas': df_filtrado['horas'].mean(),
            'Horas Validadas': df_filtrado[df_filtrado['validado'] == True]['horas'].sum(),
            'Pendientes': len(df_filtrado[df_filtrado['validado'] == False])
        }
        resumen_df = pd.DataFrame([resumen])
        resumen_csv = resumen_df.to_csv(index=False).encode('utf-8-sig')
        st.download_button(
            label=":material/summarize: Exportar Resumen",
            data=resumen_csv,
            file_name=f"dashboard_resumen_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv",
            use_container_width=True
        )

except Exception as e:
    st.error(f"Error al cargar los datos: {str(e)}")
    st.info("Asegúrate de que haya registros en la base de datos.")