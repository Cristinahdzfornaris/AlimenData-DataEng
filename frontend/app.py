import streamlit as st
import requests
import pandas as pd
import plotly.express as px
from plotly.graph_objects import Figure

st.set_page_config(
    page_title="AlimenData Cuba | Sistema de Gestión Alimentaria",
    page_icon="🇨🇺",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1e3a5f;
        margin-bottom: 1rem;
    }
    .sub-header {
        font-size: 1.3rem;
        font-weight: 600;
        color: #2c5282;
        margin-top: 1.5rem;
        margin-bottom: 0.8rem;
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .info-box {
        background-color: #ebf8ff;
        border-left: 4px solid #4299e1;
        padding: 1rem;
        border-radius: 4px;
        margin: 1rem 0;
    }
    .stButton>button {
        background-color: #4299e1;
        color: white;
        border-radius: 8px;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
</style>
""", unsafe_allow_html=True)

def safe_get(url):
    """Función segura para obtener datos del API"""
    try:
        r = requests.get(url, timeout=10)
        return r.json() if r.status_code == 200 else []
    except:
        return []


st.markdown("""
<div style="display: flex; align-items: center; justify-content: space-between; margin-bottom: 2rem;">
    <div>
        <h1 class="main-header">🇨🇺 AlimenData Cuba</h1>
        <p style="color: #718096; font-size: 1.1rem;">Sistema Inteligente de Gestión y Distribución Alimentaria</p>
    </div>
</div>
""", unsafe_allow_html=True)

st.markdown("---")

# --- 1. CARGA DE FILTROS ---
lista_provincias = safe_get("http://backend:8000/territorios/lista/Provincial")
productos_db = safe_get("http://backend:8000/productos")
lista_productos = [p["nombre"] for p in productos_db] if productos_db else []

# --- 2. BARRA LATERAL: FILTROS MULTI-SELECCIÓN ---
st.sidebar.markdown("### 🎛️ Panel de Configuración")
st.sidebar.markdown("---")

# Filtro de Producto
st.sidebar.markdown("**📦 Selección de Producto**")
prod_sel = st.sidebar.selectbox(
    "Producto a analizar",
    ["Todos"] + lista_productos,
    help="Seleccione un producto específico o 'Todos' para análisis general"
)

# Filtro de Provincias
st.sidebar.markdown("**📍 Selección de Territorios**")
prov_sels = st.sidebar.multiselect(
    "Provincias a comparar",
    lista_provincias,
    default=lista_provincias[:2] if lista_provincias else [],
    help="Seleccione múltiples provincias para comparación"
)

# Filtro de Municipios (condicional)
mun_sels = []
if prov_sels:
    st.sidebar.markdown("**🏘️ Análisis Municipal**")
    todos_municipios = []
    for p in prov_sels:
        muns = safe_get(f"http://backend:8000/territorios/lista/Municipal?padre_nombre={p}")
        todos_municipios.extend([f"{m} ({p})" for m in muns])
    
    if todos_municipios:
        mun_sels = st.sidebar.multiselect(
            "Municipios específicos",
            todos_municipios,
            help="Seleccione municipios para análisis detallado"
        )

# --- 3. LÓGICA DE DATOS PARA COMPARACIÓN ---
full_data = []

if not mun_sels:
    # Análisis a nivel provincial
    if prod_sel == "Todos":
        raw_data = safe_get("http://backend:8000/analitica/estado-critico")
    else:
        raw_data = safe_get(f"http://backend:8000/analitica/estado-critico-producto?producto_nombre={prod_sel}")
    
    if raw_data:
        full_data = [d for d in raw_data if d["provincia"] in prov_sels]
        label_eje = "provincia"
else:
    # Análisis a nivel municipal
    for p in prov_sels:
        m_data = safe_get(f"http://backend:8000/analitica/municipios-provincia?provincia_nombre={p}")
        for item in m_data:
            nombre_compuesto = f"{item['municipio']} ({p})"
            if nombre_compuesto in mun_sels:
                item["municipio_full"] = nombre_compuesto
                full_data.append(item)
    label_eje = "municipio_full"

# --- 4. RENDERIZADO DE DASHBOARD ---
if full_data:
    df = pd.DataFrame(full_data)
    
   
    st.markdown("### 📊 Indicadores Clave de Desempeño")
    
    col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
    
    with col_kpi1:
        st.metric(
            "Mermas Totales",
            f"{df['mermas_tn'].sum():,.1f} tn",
            delta=f"{df['mermas_tn'].sum() / df['disponible_tn'].sum() * 100:.1f}% del disponible"
        )
    
    with col_kpi2:
        st.metric(
            "Disponibilidad",
            f"{df['disponible_tn'].sum():,.1f} tn",
            delta="Total del grupo"
        )
    
    with col_kpi3:
        criticas = len(df[df['estado'] == 'CRÍTICO'])
        st.metric(
            "Zonas Críticas",
            criticas,
            delta=f"de {len(df)} territorios"
        )
    
    with col_kpi4:
        avg_ratio = df['ratio_perdida'].str.replace('%', '').astype(float).mean()
        st.metric(
            "Ratio Promedio",
            f"{avg_ratio:.2f}%",
            delta="Pérdida media"
        )
    
    st.markdown("---")
    
    # Gráficos Principales
    col_izq, col_der = st.columns([3, 2])
    
    with col_izq:
        st.markdown("### ⚖️ Comparativa de Pérdidas por Territorio")
        fig_bar = px.bar(
            df, 
            x=label_eje, 
            y="mermas_tn", 
            color="estado",
            text_auto='.2s',
            color_discrete_map={"CRÍTICO": "#E53E3E", "ESTABLE": "#38A169"},
            labels={"mermas_tn": "Toneladas", label_eje: "Territorio"},
            title="Pérdidas por Territorio"
        )
        fig_bar.update_layout(
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            height=400
        )
        st.plotly_chart(fig_bar, on_select="ignore")
    
    with col_der:
        st.markdown("### 📉 Eficiencia de Distribución")
        fig_scatter = px.scatter(
            df, 
            x="disponible_tn", 
            y="mermas_tn", 
            size="mermas_tn", 
            color="estado",
            hover_name=label_eje, 
            log_x=True,
            color_discrete_map={"CRÍTICO": "#E53E3E", "ESTABLE": "#38A169"},
            labels={"disponible_tn": "Disponible (tn)", "mermas_tn": "Mermas (tn)"},
            title="Relación Disponibilidad vs Mermas"
        )
        fig_scatter.update_layout(height=400)
        st.plotly_chart(fig_scatter, on_select="ignore")
    
    # Matriz de Estado
    st.markdown("---")
    st.markdown("###  Matriz de Estado Territorial")
    
    try:
        styled_df = df.style.background_gradient(
            cmap='YlOrRd', 
            subset=['mermas_tn']
        ).format({
            'mermas_tn': '{:,.2f}',
            'disponible_tn': '{:,.2f}',
            'ratio_perdida': '{}'
        })
        st.dataframe(styled_df, use_container_width=True, height=300)
    except:
        st.dataframe(df[[label_eje, "mermas_tn", "ratio_perdida", "estado"]], use_container_width=True)
    
    # Análisis de Series Temporales
    st.markdown("---")
    st.markdown("###  Análisis de Series Temporales")
    
    nombres_para_consulta = mun_sels if mun_sels else prov_sels
    nombres_limpios = [n.split(" (")[0] for n in nombres_para_consulta]
    
    if nombres_limpios:
        base_url = "http://backend:8000/analitica/series-comparadas"
        query_params = "&".join([f"nombres={n}" for n in nombres_limpios])
        full_url = f"{base_url}?{query_params}&nivel={'Municipal' if mun_sels else 'Provincial'}&producto_nombre={prod_sel}"
        
        try:
            res_series = requests.get(full_url, timeout=10)
            
            if res_series.status_code == 200:
                datos_json = res_series.json()
                if datos_json:
                    df_series = pd.DataFrame(datos_json)
                    
                    tab_tendencias, tab_calor = st.tabs(["📈 Tendencias", "🔥 Mapa de Calor"])
                    
                    with tab_tendencias:
                        st.markdown("**Evolución de Mermas por Año**")
                        fig_line = px.line(
                            df_series, 
                            x="año", 
                            y="mermas", 
                            color="territorio",
                            markers=True, 
                            labels={"mermas": "Toneladas", "año": "Año", "territorio": "Territorio"},
                            title="Tendencia Histórica de Pérdidas"
                        )
                        fig_line.update_layout(
                            hovermode='x unified',
                            height=450
                        )
                        st.plotly_chart(fig_line, on_select="ignore")
                    
                    with tab_calor:
                        st.markdown("**Matriz de Intensidad de Pérdidas**")
                        df_pivot = df_series.pivot_table(
                            index="territorio", 
                            columns="año", 
                            values="mermas", 
                            aggfunc='sum'
                        )
                        fig_heat = px.imshow(
                            df_pivot, 
                            color_continuous_scale="YlOrRd",
                            labels=dict(x="Año", y="Territorio", color="Mermas (tn)"),
                            title="Intensidad de Pérdidas por Año y Territorio"
                        )
                        fig_heat.update_layout(height=450)
                        st.plotly_chart(fig_heat, on_select="ignore")
                else:
                    st.warning(f"⚠️ No se encontraron registros históricos para: {', '.join(nombres_limpios)}")
            else:
                st.error(f"❌ Error del servidor (Código {res_series.status_code})")
                
        except Exception as e:
            st.error(f"❌ Error de conexión: {e}")
    else:
        st.info("ℹ️ Seleccione al menos una provincia o municipio para ver la evolución histórica.")

else:
    
    st.markdown("""
    <div class="info-box">
        <h3>🎯 Comience su Análisis</h3>
        <p>Utilice el panel de configuración en la barra lateral para seleccionar:</p>
        <ul>
            <li>📦 Producto a analizar</li>
            <li>📍 Provincias a comparar</li>
            <li>🏘️ Municipios específicos (opcional)</li>
        </ul>
    </div>
    """, unsafe_allow_html=True)
    
    col_welcome1, col_welcome2 = st.columns(2)
    
    with col_welcome1:
        st.info("""
        **📊 Capacidades del Sistema**
        
        - Análisis de mermas por territorio
        - Comparación multi-territorial
        - Series temporales (15 años)
        - Alertas de estado crítico
        - Matrices de riesgo visual
        """)
    
    