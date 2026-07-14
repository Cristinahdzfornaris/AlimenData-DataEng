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

# Cargamos la lista completa (dicts con id y nombre)
productos_full = get_raw_data(f"{API}/productos")
# Creamos la lista de solo nombres para el selectbox
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

    c1, c2, c3, c4 = st.columns(4)


    disponible = df["disponible_tn"].sum()
    mermas = df["mermas_tn"].sum()


    ratio = (
        (mermas / disponible) * 100
        if disponible > 0
        else 0
    )


    c1.metric(
        "Disponible",
        f"{disponible:,.1f} tn"
    )


    c2.metric(
        "Mermas",
        f"{mermas:,.1f} tn"
    )


    c3.metric(
        "Ratio de Pérdida",
        f"{ratio:.1f}%"
    )


    c4.metric(
        "Estado",
        "⚠️ CRÍTICO"
        if ratio >= 15
        else "ESTABLE"
    )



    st.markdown("---")



    # ------------------------------------------------------
    # GRÁFICA DE DISPONIBILIDAD
    # ------------------------------------------------------

    col_a, col_b = st.columns([3,2])


    with col_a:


        st.subheader(
            "⚖️ Disponibilidad por territorio"
        )


        fig_bar = px.bar(
            df,
            x=label_eje,
            y="disponible_tn",
            color="estado",
            text_auto=".2s",
            title="Disponibilidad alimentaria"
        )


        st.plotly_chart(
            fig_bar,
            use_container_width=True
        )



    # ------------------------------------------------------
    # GRÁFICA DE MERMAS
    # ------------------------------------------------------

    with col_b:


        st.subheader(
            "📉 Distribución de pérdidas"
        )


        fig_pie = px.pie(
            df,
            values="mermas_tn",
            names=label_eje,
            hole=0.4,
            title="Cuota de pérdidas"
        )


        st.plotly_chart(
            fig_pie,
            use_container_width=True
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