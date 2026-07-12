import os
import sys
from typing import List, Optional


from fastapi import FastAPI, Depends, HTTPException, Query
from sqlmodel import Session, create_engine, select, func, SQLModel


from models import RegistroBalance, Producto, Territorio

# =================================================================
# 1. CONFIGURACIÓN DE SEGURIDAD Y BASE DE DATOS 
# =================================================================

# Intentamos leer la variable de entorno obligatoria
DATABASE_URL = os.getenv("DATABASE_URL")

# Seguridad Estricta: El sistema no arranca si no hay configuración
if not DATABASE_URL:
    print("❌ ERROR CRÍTICO: La variable DATABASE_URL no está definida.")
    print("El sistema se cerrará por seguridad para evitar fugas de datos.")
    sys.exit(1)

# Creamos el motor de conexión 
engine = create_engine(DATABASE_URL, echo=False)

# =================================================================
# 2. INICIALIZACIÓN DE LA APP
# =================================================================

app = FastAPI(
    title="AlimenData Cuba API",
    description="Sistema Inteligente de Gestión y Distribución Alimentaria - Fase 1",
    version="1.0.0"
)

def get_session():
    with Session(engine) as session:
        yield session

# =================================================================
# 3. ENDPOINTS DE LA API (Fase 1: Analítica e Ingestión)
# =================================================================


@app.get("/", tags=["General"])
def health_check():
    """Verifica si la API está en línea."""
    return {
        "status": "online",
        "mensaje": "Bienvenido a AlimenData Cuba",
        "conexion_db": "Exitosa"
    }

@app.get("/territorios", response_model=List[Territorio], tags=["Territorios"])
def listar_territorios(session: Session = Depends(get_session)):
    """Lista la jerarquía territorial de Cuba cargada."""
    return session.exec(select(Territorio)).all()

@app.get("/productos", response_model=List[Producto], tags=["Productos"])
def listar_productos(session: Session = Depends(get_session)):
    """Lista el catálogo de productos disponibles."""
    return session.exec(select(Producto)).all()

@app.get("/analitica/estado-critico", tags=["Analítica"])
def obtener_estado_critico(session: Session = Depends(get_session)):
    statement = (
        select(
            Territorio.nombre.label("provincia"),
            func.sum(RegistroBalance.mermas).label("mermas_acumuladas"),
            func.sum(RegistroBalance.disponible).label("disponibilidad_total")
        )
        .join(RegistroBalance, Territorio.id == RegistroBalance.territorio_id)
        .where(Territorio.nivel == "Provincial")
        .group_by(Territorio.nombre)
    )
    
    results = session.exec(statement).all()
    
    reporte = []
    for res in results: 
        ratio = (res.mermas_acumuladas / res.disponibilidad_total) if res.disponibilidad_total > 0 else 0
        reporte.append({
            "provincia": res.provincia,
            "mermas_tn": round(res.mermas_acumuladas, 2),
            "disponible_tn": round(res.disponibilidad_total, 2),
            "ratio_perdida": f"{round(ratio * 100, 2)}%",
            "estado": "CRÍTICO" if ratio > 0.10 else "ESTABLE"
        })
    return reporte

@app.get("/analitica/estado-critico-producto", tags=["Analítica"])
def obtener_estado_critico_producto(
    producto_nombre: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """
    Análisis de mermas por provincia filtrado por producto específico.
    Si producto_nombre es None o "Todos", retorna el análisis general.
    """
    # Base query
    statement = (
        select(
            Territorio.nombre.label("provincia"),
            func.sum(RegistroBalance.mermas).label("mermas_acumuladas"),
            func.sum(RegistroBalance.disponible).label("disponibilidad_total")
        )
        .join(RegistroBalance, Territorio.id == RegistroBalance.territorio_id)
        .where(Territorio.nivel == "Provincial")
    )
    
    # Filtrar por producto si se especifica
    if producto_nombre and producto_nombre != "Todos":
        statement = statement.join(Producto, Producto.id == RegistroBalance.producto_id).where(Producto.nombre == producto_nombre)
    
    statement = statement.group_by(Territorio.nombre)
    
    results = session.exec(statement).all()
    
    reporte = []
    for res in results:
        ratio = (res.mermas_acumuladas / res.disponibilidad_total) if res.disponibilidad_total > 0 else 0
        
        reporte.append({
            "provincia": res.provincia,
            "mermas_tn": round(res.mermas_acumuladas, 2),
            "disponible_tn": round(res.disponibilidad_total, 2),
            "ratio_perdida": f"{round(ratio * 100, 2)}%",
            "estado": "CRÍTICO" if ratio > 0.15 else "ESTABLE"
        })
    
    return reporte

@app.get("/analitica/municipios-provincia", tags=["Analítica"])
def obtener_municipios_provincia(
    provincia_nombre: str,
    session: Session = Depends(get_session)
):
    """
    Desglose de mermas por municipio para una provincia específica.
    """
    # Obtener el ID de la provincia
    provincia = session.exec(select(Territorio).where(Territorio.nombre == provincia_nombre).where(Territorio.nivel == "Provincial")).first()
    
    if not provincia:
        raise HTTPException(status_code=404, detail="Provincia no encontrada")
    
    # Consultar municipios de esa provincia
    statement = (
        select(
            Territorio.nombre.label("municipio"),
            func.sum(RegistroBalance.mermas).label("mermas_acumuladas"),
            func.sum(RegistroBalance.disponible).label("disponibilidad_total")
        )
        .join(RegistroBalance, Territorio.id == RegistroBalance.territorio_id)
        .where(Territorio.nivel == "Municipal")
        .where(Territorio.padre_id == provincia.id)
        .group_by(Territorio.nombre)
    )
    
    results = session.exec(statement).all()
    
    reporte = []
    for res in results:
        ratio = (res.mermas_acumuladas / res.disponibilidad_total) if res.disponibilidad_total > 0 else 0
        
        reporte.append({
            "municipio": res.municipio,
            "mermas_tn": round(res.mermas_acumuladas, 2),
            "disponible_tn": round(res.disponibilidad_total, 2),
            "ratio_perdida": f"{round(ratio * 100, 2)}%",
            "estado": "CRÍTICO" if ratio > 0.15 else "ESTABLE"
        })
    
    return reporte

@app.get("/analitica/historico-serie", tags=["Analítica"])
def obtener_serie_temporal(
    producto_id: int, 
    provincia_id: int, 
    session: Session = Depends(get_session)
):
    """
    REQUISITO FASE 1: Procesar series temporales históricas (15 años).
    Devuelve la evolución de disponibilidad por año para un producto y territorio.
    """
    statement = (
        select(RegistroBalance.año, RegistroBalance.disponible, RegistroBalance.mermas)
        .where(RegistroBalance.producto_id == producto_id)
        .where(RegistroBalance.territorio_id == provincia_id)
        .order_by(RegistroBalance.año)
    )
    
    return session.exec(statement).all()

@app.get("/territorios/lista/{nivel}", tags=["Territorios"])
def obtener_lista_por_nivel(nivel: str, padre_nombre: Optional[str] = None, session: Session = Depends(get_session)):
    """Devuelve nombres de territorios según nivel (Provincial/Municipal)."""
    statement = select(Territorio).where(Territorio.nivel == nivel)
    if padre_nombre:
        
        padre = session.exec(select(Territorio).where(Territorio.nombre == padre_nombre)).first()
        if padre:
            statement = statement.where(Territorio.padre_id == padre.id)
    
    results = session.exec(statement).all()
    return [t.nombre for t in results]
@app.get("/territorios/municipios/{provincia_nombre}", tags=["Territorios"])
def obtener_nombres_municipios(provincia_nombre: str, session: Session = Depends(get_session)):
    """Devuelve la lista de nombres de municipios de una provincia específica."""
    statement = (
        select(Territorio.nombre)
        .join(Territorio, Territorio.id == Territorio.padre_id, isouter=True, aliased=True)
        .where(Territorio.nivel == "Municipal")
    )
    
    prov = session.exec(select(Territorio).where(Territorio.nombre == provincia_nombre).where(Territorio.nivel == "Provincial")).first()
    if not prov:
        return []
    
    municipios = session.exec(select(Territorio.nombre).where(Territorio.padre_id == prov.id)).all()
    return municipios


@app.get("/analitica/series-comparadas", tags=["Analítica"])
def obtener_series_comparadas(
    nombres: List[str] = Query(...), 
    nivel: str = "Provincial",
    producto_nombre: Optional[str] = "Todos",
    session: Session = Depends(get_session)
):
    # Log para depuración 
    print(f"DEBUG: Recibido nombres={nombres}, nivel={nivel}, producto={producto_nombre}")

    statement = (
        select(
            RegistroBalance.año,
            Territorio.nombre.label("territorio"),
            func.sum(RegistroBalance.mermas).label("mermas")
        )
        .join(Territorio, RegistroBalance.territorio_id == Territorio.id)
        .where(Territorio.nombre.in_(nombres))
        .where(Territorio.nivel == nivel)
    )
    
    if producto_nombre and producto_nombre != "Todos":
        statement = statement.join(Producto, RegistroBalance.producto_id == Producto.id).where(Producto.nombre == producto_nombre)
        
    statement = statement.group_by(RegistroBalance.año, Territorio.nombre).order_by(RegistroBalance.año)
    
    results = session.exec(statement).all()
    
    
    return [{"año": r.año, "territorio": r.territorio, "mermas": r.mermas} for r in results]

# =================================================================
# 4. MANEJO DE ERRORES GLOBALES
# =================================================================

@app.middleware("http")
async def db_session_middleware(request, call_next):
    """Middleware para asegurar que el sistema no colapse ante errores de DB."""
    try:
        return await call_next(request)
    except Exception as e:
        print(f"❌ ERROR DE SISTEMA: {str(e)}")
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=500,
            content={"detail": f"Error interno del servidor: {str(e)}"}
        )