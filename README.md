
# AlimenData Cuba 🇨🇺
### Sistema Inteligente de Gestión y Distribución Alimentaria



AlimenData es una plataforma de ingeniería de datos diseñada para la gestión logística y el análisis de equidad distributiva de alimentos en Cuba. Integra datos históricos de la FAO con estadísticas demográficas oficiales de la ONEI (2006-2022).

## 🏗️ Arquitectura del Sistema (Fase 2)
El proyecto se basa en una arquitectura de **microservicios** desacoplados mediante Docker:
*   **Backend:** FastAPI con SQLModel (Python). Implementa el **Patrón Repositorio** para aislar la lógica de negocio de la base de datos.
*   **Frontend:** Dashboard analítico interactivo con Streamlit y Plotly.
*   **Database:** PostgreSQL 15 con persistencia de volúmenes.
*   **Seguridad:** Autenticación basada en **JWT (JSON Web Tokens)** y hashing de contraseñas con BCrypt.

## 🚀 Instalación y Despliegue

### 1. Requisitos
*   Docker y Docker Compose instalados.
*   Archivo de datos en `data/cuba_fao_data.csv` y `data/3.5-poblacion...xls`.

### 2. Inicio Rápido
```bash
# Levantar la infraestructura
docker-compose up --build -d

# Aplicar estructura de base de datos (Alembic)
docker-compose exec backend alembic upgrade head

# Ingestión de datos (ETL) - Ejecutar en este orden
docker-compose exec backend python scripts/etl_fao.py
docker-compose exec backend python scripts/etl_poblacion_onei.py
```

## 🔐 Control de Acceso (RBAC)
El sistema gestiona la visibilidad de los datos según el perfil del usuario:
*   **Nivel Nacional:** Acceso total a todas las provincias, municipios y comparativas de equidad país.
*   **Nivel Provincial:** Acceso restringido únicamente a los datos de su provincia y municipios subordinados (Principio de Privilegio Mínimo).
*   **Nivel Municipal:** Visualización exclusiva de los indicadores del punto de venta local.

## 📊 Capacidades Analíticas
*   **Indicador de Equidad:** Cálculo automático de Kg por habitante al año mediante ingestión cruzada de fuentes FAO/ONEI.
*   **Series Temporales:** Evolución de mermas y disponibilidad durante 15 años.
*   **Matrices de Riesgo:** Mapas de calor para detectar años e hitos críticos en la distribución.
*   **Drill-down:** Navegación desde el balance provincial hasta el detalle municipal.

## 📁 Estructura del Proyecto
```text
AlimenData/
├── backend/
│   ├── alembic/            # Versiones y migraciones DB
│   ├── scripts/            # Pipelines ETL (FAO y ONEI)
│   ├── auth.py             # Lógica de Seguridad JWT
│   ├── main.py             # Endpoints de la API REST
│   ├── models.py           # Modelos de Datos (SQLModel)
│   └── repositories.py     # Capa de Persistencia (Pattern)
├── frontend/
│   └── app.py              # Dashboard Streamlit
├── data/                   # Datasets CSV y Excel
└── docker-compose.yml      # Orquestador de contenedores
```

## 🛠️ Tecnologías Utilizadas
*   **Lenguaje:** Python 3.10
*   **Persistencia:** SQLModel, Alembic, PostgreSQL.
*   **ETL:** Pandas, Numpy, Unicodedata.
*   **API:** FastAPI, Jose (JWT), Passlib.
*   **Visualización:** Plotly Express.

---

### Notas de Ingeniería:
- **Idempotencia:** Los scripts ETL detectan datos existentes para evitar duplicados en ejecuciones repetidas.
- **Normalización:** El sistema es insensible a mayúsculas, tildes y espacios en el registro y búsqueda de territorios.
- **Schema Evolution:** El modelo de territorios incluye perfiles logísticos (Almacén Central / Punto de Venta) según los requerimientos de la Fase 1.

---
