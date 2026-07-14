#!/bin/sh

echo "🏗️ FASE 3: Aplicando Estructura (Alembic)..."
alembic upgrade head

echo "📊 FASE 3: Verificando integridad de datos..."
# Usamos una forma más simple de verificar sin depender de psql si falla
# Intentaremos correr el ETL y el propio script de idempotencia se encargará
python scripts/etl_fao.py
python scripts/etl_poblacion_onei.py

echo "🚀 Arrancando API REST..."
exec uvicorn main:app --host 0.0.0.0 --port 8000