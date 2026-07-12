
# AlimenData Cuba - Sistema Inteligente de Gestión y Distribución Alimentaria

Sistema integral de ingeniería de datos diseñado para la optimización logística, el control de inventarios y el análisis de equidad distributiva per cápita en el territorio cubano.

## 🏗️ Arquitectura del Sistema

El proyecto implementa una arquitectura de **Microservicios desacoplados** orquestados mediante **Docker Compose**, comunicados a través de una red interna privada (`alimen_network`):

- **Frontend (Visualización)**: Streamlit. Ofrece un tablero de Business Intelligence interactivo con comparativas territoriales y matrices de riesgo.
- **Backend (REST API)**: FastAPI + SQLModel. Gestiona la lógica analítica, el procesamiento de series temporales y la capa de persistencia.
- **Database (Persistencia)**: PostgreSQL 15. Motor relacional con integridad transaccional (ACID) y volumen de datos persistente.

## 🚀 Despliegue Rápido

### Requisitos Previos
- Docker y Docker Compose instalados.
- Archivo de datos semilla en `data/cuba_fao_data.csv`.

### 1. Configuración de Variables de Entorno
Cree un archivo `.env` en la raíz del proyecto basado en `.env.example`:

```env
DB_USER=alimen_user
DB_PASSWORD=secure_password
DB_NAME=alimen_data
DATABASE_URL=postgresql://alimen_user:secure_password@db:5432/alimen_data
SECRET_KEY=clave_segura_para_tokens
```

### 2. Iniciar Infraestructura
```bash
docker-compose up --build -d
```
*Este comando construye las imágenes, levanta los contenedores y ejecuta las migraciones de Alembic automáticamente para inicializar el esquema de la base de datos.*

### 3. Ingestión de Datos (Pipeline ETL)
Una vez que los servicios estén activos, ejecute el pipeline de datos para procesar el histórico y la jerarquía territorial:
```bash
docker-compose exec backend env PYTHONPATH=/app python scripts/etl_fao.py
```

## 📊 Capacidades Analíticas e Interfaz

El sistema ofrece un panel de control avanzado que permite:
- **Jerarquía Territorial**: Navegación desde el nivel Nacional hasta el detalle Municipal (168 municipios incluidos).
- **Análisis de Equidad**: Cálculo automático del consumo per cápita basado en datos demográficos.
- **Series Temporales**: Visualización de 15 años de historial (2008-2023) con técnicas de imputación estadística para datos faltantes.
- **Comparativas Multi-selección**: Permite comparar simultáneamente múltiples provincias o municipios.
- **Matrices de Riesgo**: Mapas de calor (Heatmaps) que identifican años y territorios con pérdidas críticas.

## 📁 Estructura del Repositorio

```
AlimenData-Cuba/
├── backend/
│   ├── alembic/              # Control de versiones de la estructura DB
│   ├── scripts/              # Pipeline ETL e inicialización
│   ├── main.py               # Lógica de la API y Endpoints analíticos
│   ├── models.py             # Definición del esquema (ORM SQLModel)
│   └── requirements.txt
├── frontend/
│   ├── app.py                # Dashboard interactivo
│   └── requirements.txt
├── data/
│   └── cuba_fao_data.csv     # Dataset fuente de FAOSTAT
├── docker-compose.yml        # Orquestador de microservicios
├── .env.example              # Plantilla de configuración segura
└── .gitignore                # Protección de credenciales y binarios
```

## 🔒 Estándares de Ingeniería y Cumplimiento

Para garantizar la calidad y seguridad, el proyecto cumple con las siguientes directrices:
- **Seguridad (Directriz 1.1 y 3.1)**: Prohibido el uso de SQL Nativo; uso estricto de ORM. Credenciales gestionadas fuera del código mediante `.env`.
- **Versionado de Datos (Directriz 1.2)**: Inicialización de base de datos exclusivamente mediante migraciones formales con **Alembic**.
- **DataOps (Directriz 3.2)**: Implementación de **Healthchecks** en la base de datos para asegurar la disponibilidad de servicios y resiliencia del sistema.
- **Optimización**: Almacenamiento optimizado e indexado para series temporales masivas sin exceder los límites de carga local.

## 📝 Resumen de Implementación (Fase 1)

- [x] **Modelo de Datos**: Normalizado en 3NF con jerarquía `padre_id`.
- [x] **Pipeline ETL**: Limpieza, filtrado de 20 rubros principales y aumentación de datos históricos.
- [x] **Analítica Dinámica**: Endpoints que calculan ratios de mermas y estados de alerta en tiempo real.
- [x] **Visualización**: Dashboard interactivo con Plotly y Streamlit.

