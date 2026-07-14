import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import unicodedata


# ==========================================================
# CONFIGURACIÓN
# ==========================================================

st.set_page_config(
    page_title="AlimenData Cuba | Dashboard Full",
    page_icon="🇨🇺",
    layout="wide"
)


API = "http://backend:8000"


# ==========================================================
# FUNCIONES
# ==========================================================

def normalizar(texto):

    if not texto:
        return ""

    texto = str(texto).strip().lower()

    return ''.join(
        c for c in unicodedata.normalize(
            'NFD',
            texto
        )
        if unicodedata.category(c) != 'Mn'
    )



def get_auth_header():

    return {
        "Authorization":
        f"Bearer {st.session_state.get('token','')}"
    }



def safe_get(url):

    try:

        r = requests.get(
            url,
            headers=get_auth_header(),
            timeout=10
        )

        if r.status_code == 200:

            data = r.json()

            if (
                isinstance(data,list)
                and len(data)>0
                and isinstance(data[0],dict)
                and "nombre" in data[0]
            ):
                return [
                    x["nombre"]
                    for x in data
                ]

            return data

        return []

    except Exception:

        return []



# ==========================================================
# ESTILO
# ==========================================================

st.markdown(
"""
<style>

.main-header{
font-size:2.2rem;
font-weight:700;
color:#1e3a5f;
}

.stMetric{
background:white;
padding:15px;
border-radius:10px;
}

</style>
""",
unsafe_allow_html=True
)



# ==========================================================
# LOGIN
# ==========================================================

if "token" not in st.session_state:
    st.session_state.token=None


if "user" not in st.session_state:
    st.session_state.user=None



if not st.session_state.token:


    st.markdown(
        "<h1 class='main-header'>🇨🇺 AlimenData Cuba</h1>",
        unsafe_allow_html=True
    )


    with st.form("login"):

        usuario = st.text_input(
            "Usuario"
        )

        password = st.text_input(
            "Contraseña",
            type="password"
        )


        entrar = st.form_submit_button(
            "Entrar"
        )


        if entrar:

            response = requests.post(
                f"{API}/token",
                data={
                    "username":usuario,
                    "password":password
                }
            )


            if response.status_code==200:


                st.session_state.token = (
                    response.json()["access_token"]
                )


                st.session_state.user = requests.get(
                    f"{API}/usuarios/me",
                    headers=get_auth_header()
                ).json()


                st.rerun()


            else:

                st.error(
                    "Usuario o contraseña incorrectos"
                )


    st.stop()


prods_raw = safe_get(f"{API}/productos")
def get_raw_data(url):
    r = requests.get(url, headers=get_auth_header())
    return r.json() if r.status_code == 200 else []

productos_full = get_raw_data(f"{API}/productos")
lista_nombres_productos = [p['nombre'] for p in productos_full]
# ==========================================================
# USUARIO
# ==========================================================


user = st.session_state.user


st.sidebar.markdown(
    f"""
    ### 👤 {user['username']}
    
    Nivel:
    **{user['nivel_acceso']}**
    """
)


if st.sidebar.button(
    "Cerrar sesión"
):

    st.session_state.token=None
    st.session_state.user=None
    st.rerun()



st.sidebar.divider()

st.sidebar.subheader(
    "🎛️ Filtros"
)



# ==========================================================
# CONTROL RBAC
# ==========================================================


nivel_usuario = user["nivel_acceso"]


territorio_usuario = user.get(
    "territorio_nombre",
    ""
)



# -----------------------------
# PROVINCIAS
# -----------------------------


todas_provincias = safe_get(
    f"{API}/territorios/lista/Provincial"
)



if nivel_usuario=="Nacional":


    provincias = st.sidebar.multiselect(
        "Provincias",
        todas_provincias,
        default=todas_provincias[:1]
    )



elif nivel_usuario=="Provincial":


    provincias=[
        territorio_usuario
    ]


    st.sidebar.info(
        f"Provincia asignada:\n{territorio_usuario}"
    )



elif nivel_usuario=="Municipal":

    provincias=[]

else:

    provincias=[]

# ==========================================================
# MUNICIPIOS
# ==========================================================


municipios=[]


if nivel_usuario=="Municipal":


    municipios=[
        territorio_usuario
    ]


    st.sidebar.info(
        f"Municipio asignado:\n{territorio_usuario}"
    )



else:


    opciones_municipios=[]


    for provincia in provincias:


        lista = safe_get(
            f"{API}/territorios/lista/Municipal"
            f"?padre_nombre={provincia}"
        )


        for m in lista:

            opciones_municipios.append(
                f"{m} ({provincia})"
            )



    if opciones_municipios:


        municipios = st.sidebar.multiselect(
            "Municipios",
            opciones_municipios
        )




# ==========================================================
# PRODUCTOS
# ==========================================================


productos = safe_get(
    f"{API}/productos"
)


producto = st.sidebar.selectbox(
    "📦 Producto",
    ["Todos"] + productos
)



# ==========================================================
# CONSULTA ANALÍTICA
# ==========================================================


datos=[]


if nivel_usuario=="Municipal":

    territorio_id = user["territorio_id"]


    url = (
    f"{API}/analitica/municipio-individual"
    f"?territorio_id={territorio_id}"
    f"&producto_nombre={producto}"
    )

    datos = safe_get(url)



elif municipios:


    nombres=[
        x.split(" (")[0]
        for x in municipios
    ]


    for provincia in provincias:


        url=(
            f"{API}/analitica/municipios-provincia"
            f"?provincia_nombre={provincia}"
            f"&producto_nombre={producto}"
        )


        resultado=safe_get(url)


        for item in resultado:


            if item["municipio"] in nombres:

                item["territorio_display"] = (
                    f"{item['municipio']} (Municipio - {provincia})"
                )

                item["nivel"] = "Municipal"

                datos.append(item)



else:


    url=(
        f"{API}/analitica/estado-critico-producto"
        f"?producto_nombre={producto}"
    )


    resultado=safe_get(url)


    provincias_norm=[
        normalizar(x)
        for x in provincias
    ]


    datos=[]

    for x in resultado:

        if normalizar(x["provincia"]) in provincias_norm:

            x["territorio_display"] = (
                f"{x['provincia']} (Provincia)"
            )

            x["nivel"] = "Provincial"

            datos.append(x)




# ==========================================================
# VISUALIZACIÓN
# ==========================================================


st.markdown(
f"""
<h1 class='main-header'>
🇨🇺 Gestión Alimentaria - {producto}
</h1>
""",
unsafe_allow_html=True
)



if datos:

    df = pd.DataFrame(datos)
    if "estado" not in df.columns:

        df["estado"] = df.apply(
            lambda x:
                "CRÍTICO"
                if x["disponible_tn"] > 0 
                and (x["mermas_tn"] / x["disponible_tn"]) > 0.15
                else "ESTABLE",
            axis=1
        )


    # ------------------------------------------------------
    # DEFINIR NOMBRE DEL EJE
    # ------------------------------------------------------

    # Nombre único para gráficas y tablas

    if "territorio_display" not in df.columns:

        if "municipio" in df.columns:

            df["territorio_display"] = (
                df["municipio"] +
                " (Municipio)"
            )

        elif "provincia" in df.columns:

            df["territorio_display"] = (
                df["provincia"] +
                " (Provincia)"
            )


    label_eje = "territorio_display"



    # ------------------------------------------------------
    # KPIs
    # ------------------------------------------------------

    # --- RENDERIZADO DEL DASHBOARD ---

    if not df.empty:
        total_disp = df['disponible_tn'].sum()
        total_merm = df['mermas_tn'].sum()
        ratio_total = (total_merm / total_disp * 100) if total_disp > 0 else 0
        eficiencia_rotacion = (total_disp / (total_disp + total_merm) * 100) if (total_disp + total_merm) > 0 else 0

        st.markdown("### 📊 Indicadores de Inteligencia Logística")
        
        col_a, col_b, col_c, col_d = st.columns(4)
        
        with col_a:
            st.metric(
                label="📦 Disponibilidad Total", 
                value=f"{total_disp:,.1f} tn",
                help="Suma total de productos en los nodos seleccionados."
            )
        
        with col_b:
            alerta_estado = "CRÍTICO" if ratio_total > 15 else "ESTABLE"
            color_alerta = "normal" if alerta_estado == "ESTABLE" else "inverse"
            st.metric(
                label="🚨 Alerta de Suministro", 
                value=alerta_estado,
                delta=f"{ratio_total:.1f}% mermas",
                delta_color=color_alerta,
                help="Se dispara automáticamente si las mermas superan el 15% del total."
            )
            
        with col_c:
 
            st.metric(
                label="🔄 Eficiencia de Rotación", 
                value=f"{eficiencia_rotacion:.1f}%",
                delta="Flujo Óptimo" if eficiencia_rotacion > 85 else "Flujo Lento",
                help="Mide qué tan efectiva es la red para mover el producto sin pérdidas."
            )
            
        with col_d:
            st.metric(
                label="📅 Ciclo Estacional", 
                value="Analizado",
                delta="Serie 15 años",
                help="Indica que los datos están siendo contrastados con el patrón histórico 2006-2022."
            )

        st.markdown("---")
    


    # ------------------------------------------------------
    # EVOLUCIÓN HISTÓRICA 15 AÑOS
    # ------------------------------------------------------

    st.subheader(
        "📈 Evolución Histórica (2006 - 2022)"
    )


    if "nivel" in df.columns and df["nivel"].iloc[0] == "Municipal":

        nombres_hist = [
            x.split(" (")[0]
            for x in municipios
        ]

        nivel_hist = "Municipal"


    else:

        nombres_hist = provincias

        nivel_hist = "Provincial"



    if nombres_hist:


        query = "&".join(
            [
                f"nombres={x}"
                for x in nombres_hist
            ]
        )


        url_hist = (
            f"http://backend:8000/"
            f"analitica/series-comparadas?"
            f"{query}"
            f"&nivel={nivel_hist}"
            f"&producto_nombre={producto}"
        )


        hist_res = safe_get(
            url_hist
        )



        if hist_res:


            df_hist = pd.DataFrame(
                hist_res
            )



            tab1, tab2 = st.tabs(
                [
                    "📉 Tendencia temporal",
                    "🔥 Matriz de intensidad"
                ]
            )



            # -------- Línea temporal ---------

            with tab1:


                fig_line = px.line(
                    df_hist,
                    x="año",
                    y="mermas",
                    color="territorio",
                    markers=True,
                    title="Evolución de mermas por año"
                )


                st.plotly_chart(
                    fig_line,
                    use_container_width=True
                )



            # -------- Heatmap ---------

            with tab2:


                tabla = df_hist.pivot_table(
                    index="territorio",
                    columns="año",
                    values="mermas",
                    aggfunc="sum"
                )


                fig_heat = px.imshow(
                    tabla,
                    title="Mapa de calor de pérdidas",
                    aspect="auto"
                )


                st.plotly_chart(
                    fig_heat,
                    use_container_width=True
                )



        else:

            st.warning(
                "No existen datos históricos para este territorio."
            )



    # ------------------------------------------------------
    # TABLA
    # ------------------------------------------------------

    with st.expander(
        "🔍 Ver datos completos"
    ):

        st.dataframe(
            df,
            use_container_width=True
        )



else:

    st.info(
        "💡 Utilice la barra lateral para seleccionar territorios y generar el análisis."
    )

# --- FASE 3: CRUD OPERATIVO ---

with st.expander("📝 Panel de Registro Operativo"):
    if user['nivel_acceso'] in ["Nacional", "Provincial"]:
        with st.form("crud_almacen"):
            st.write("### Nueva entrada de Inventario / Merma")
            c1, c2 = st.columns(2)
            
            # 1. Selección de Territorio (Solo para Nacionales)
            if user['nivel_acceso'] == "Nacional":
                # El admin nacional elige el almacén (provincia)
                todas_provs_nombres = safe_get(f"{API}/territorios/lista/Provincial")
                t_nom_reg = c1.selectbox("Seleccionar Almacén de Destino", todas_provs_nombres)
                res_t = requests.get(f"{API}/territorios", headers=get_auth_header()).json()
                target_id = next((t['id'] for t in res_t if t['nombre'] == t_nom_reg), 1)
            else:
                target_id = user['territorio_id']
                st.info(f"Registrando en su almacén: {user['territorio_nombre']}")

            # 2. Selección de Producto
            p_nom = c2.selectbox("Producto", lista_nombres_productos)
            p_id = next((p['id'] for p in productos_full if p['nombre'] == p_nom), 1)
            
            # 3. Cantidad y Tipo
            cant = c1.number_input("Cantidad (tn)", min_value=0.1)
            tipo = c2.radio("Tipo de Operación", ["Entrada de Inventario", "Merma/Pérdida"])
            
            if st.form_submit_button("💾 Confirmar y Guardar"):
                # Verificamos que el ID no sea nulo antes de enviar
                if target_id is None:
                    st.error("Error: No se pudo determinar el ID del territorio.")
                else:
                    nuevo_dato = {
                        "año": 2024,
                        "producto_id": p_id,
                        "territorio_id": target_id,
                        "disponible": cant if tipo == "Entrada de Inventario" else 0,
                        "mermas": cant if tipo == "Merma/Pérdida" else 0,
                        "importacion": 0.0,
                        "consumo_per_capita": 0.0
                    }
                    
                    res = requests.post(f"{API}/registros/operacion", json=nuevo_dato, headers=get_auth_header())
                    
                    if res.status_code == 200:
                        st.success(f"✅ ¡ÉXITO! Se guardó el registro en la base de datos.")
                        st.balloons()
                    else:
                        st.error(f"❌ Error del servidor: {res.text}")
    else:
        st.warning("Su perfil no tiene permisos de escritura.")