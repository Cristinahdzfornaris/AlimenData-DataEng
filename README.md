
---

# AlimenData Cuba 🇨🇺
### Sistema Inteligente de Gestión y Distribución Alimentaria (Fase 3 - Final)

**AlimenData** es una plataforma integral de ingeniería de datos diseñada para la optimización logística, el control de inventarios operativos y el análisis de equidad distributiva en Cuba. El sistema integra datos históricos globales (FAO) con estadísticas demográficas oficiales (ONEI) y permite la gestión de inventarios en tiempo real para el ciclo operativo 2024.

## 🚀 Despliegue Automático (Directriz 3.1)
El sistema está diseñado bajo principios de **DataOps** para funcionar con un único comando. No se requiere configuración manual de la base de datos ni ejecución externa de scripts.

```bash
# Iniciar todo el ecosistema (Migraciones + ETL + API + Dashboard)
docker-compose up --build
```

---

## 🏗️ Arquitectura de Microservicios
La solución se estructura en tres contenedores independientes y desacoplados:

1.  **Backend (FastAPI + SQLModel):** API REST protegida que gestiona la lógica de negocio y la capa de persistencia.
2.  **Frontend (Streamlit):** Interfaz de Business Intelligence con soporte para operaciones CRUD.
3.  **Database (PostgreSQL 15):** Motor relacional con integridad transaccional (ACID).

---

## 🛠️ Cumplimiento de Directrices de Ingeniería

### 1. Persistencia y Seguridad (Fase 1 y 2)
*   **Prohibición de SQL Nativo:** Se implementó **SQLModel** como ORM. No existe rastro de SQL embebido en el código.
*   **Patrón Repositorio:** Se aisló completamente la lógica de la base de datos en una capa de persistencia (`repositories.py`), garantizando un código limpio y mantenible.
*   **Control de Versiones DB:** Gestión estricta mediante **Alembic**. Todo el esquema se construye a partir de archivos de migración versionados.
*   **Seguridad:** Autenticación mediante **JWT (JSON Web Tokens)** y almacenamiento de credenciales con hashing de alta seguridad (**BCrypt**).

### 2. Integración y Equidad (Fase 2)
*   **Ingestión Cruzada (FAO + ONEI):** El sistema realiza un "join" lógico entre los balances alimentarios y la población residente oficial por municipio (Serie 2006-2022).
*   **Indicador de Equidad:** Se calcula automáticamente el **Consumo Per Cápita (Kg/persona/año)**, permitiendo identificar brechas distributivas territoriales.

### 3. DataOps y Operatividad (Fase 3)
*   **Despliegue Idempotente:** El script `start.sh` automatiza las migraciones y la carga de datos inicial solo si la base de datos está vacía, evitando duplicidad de información.
*   **CRUD Interactivo:** Los administradores pueden registrar entradas físicas y mermas para el año **2024**, permitiendo una analítica que combina el histórico con la operación actual.
*   **RBAC (Control de Acceso Territorial):** 
    *   **Nacional:** Visión macro y estratégica de todo el país.
    *   **Provincial:** Gestión exclusiva de su Almacén Central y red de municipios subordinados.

---

## 📊 Capacidades del Dashboard
*   **Mapas de Calor:** Identificación de años críticos y zonas con mayores pérdidas.
*   **Tendencias de 15 años:** Evolución temporal de 20 productos clave.
*   **Gestión Operativa:** Formulario para registro manual de movimientos de almacén.
*   **KPIs en Tiempo Real:** Visualización instantánea de disponibilidad y ratios de pérdida.

---

## 📁 Estructura del Repositorio
```text
AlimenData-Cuba/
├── backend/
│   ├── alembic/            # Historial de migraciones (ADN de la DB)
│   ├── scripts/            # Pipelines ETL (FAO y ONEI)
│   ├── auth.py             # Motor de seguridad JWT
│   ├── main.py             # Endpoints y lógica de API
│   ├── models.py           # Modelos de datos estructurados
│   ├── repositories.py     # Capa de persistencia (Pattern)
│   └── start.sh            # Receta de automatización DataOps
├── frontend/
│   └── app.py              # Interfaz de usuario y analítica
├── data/                   # Semillas de datos (FAO/ONEI)
├── .env.example            # Plantilla para variables de entorno
└── docker-compose.yml      # Orquestador de la infraestructura
```

---

## ⚙️ Configuración (Variables de Entorno)
Para el despliegue, el sistema utiliza un archivo `.env` (parametrizado fuera del código):
*   `DATABASE_URL`: Conexión segura a PostgreSQL.
*   `SECRET_KEY`: Clave maestra para la firma de tokens JWT.
*   `DB_USER/DB_PASSWORD`: Credenciales de acceso al motor.

---
