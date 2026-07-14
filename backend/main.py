import os
import sys
from typing import List, Optional
from datetime import timedelta

from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlmodel import Session, create_engine, select, func, SQLModel

from models import RegistroBalance, Producto, Territorio, Usuario, PoblacionHistorica
from auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, check_access_level, ACCESS_TOKEN_EXPIRE_MINUTES
)
from repositories import (
    TerritorioRepository, 
    ProductoRepository, 
    UsuarioRepository, 
    RegistroBalanceRepository
)

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
# 3. ENDPOINTS DE AUTENTICACIÓN (Fase 2)
# =================================================================

@app.post("/token", tags=["Autenticación"])
def login(form_data: OAuth2PasswordRequestForm = Depends(), session: Session = Depends(get_session)):
    """Endpoint de login para obtener token JWT (Insensible a mayúsculas)"""
    repo = UsuarioRepository(session)
    
    user = repo.get_by_username(form_data.username)
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario o contraseña incorrectos",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Usuario desactivado"
        )
        
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/usuarios/registro", tags=["Autenticación"])
def registrar_usuario(
    username: str,
    email: str,
    password: str,
    nivel_acceso: str,
    territorio_nombre: Optional[str] = None,
    session: Session = Depends(get_session)
):
    """Endpoint de registro de nuevos usuarios (Normalización automática)"""
    repo_u = UsuarioRepository(session)
    repo_t = TerritorioRepository(session)

    # 1. Normalizar credenciales a minúsculas
    username_norm = username.strip().lower()
    email_norm = email.strip().lower()
    
    # 2. Normalizar nivel de acceso 
    nivel_norm = nivel_acceso.strip().title()

    # Verificar si el usuario ya existe
    if repo_u.get_by_username(username_norm):
        raise HTTPException(status_code=400, detail="El nombre de usuario ya existe")
    
    if repo_u.get_by_email(email_norm):
        raise HTTPException(status_code=400, detail="El email ya está registrado")
    
    if nivel_norm not in ["Nacional", "Provincial", "Municipal"]:
        raise HTTPException(status_code=400, detail="Nivel de acceso inválido")
    
    # 3. Obtener territorio con búsqueda insensible a mayúsculas
    territorio_id = None
    if nivel_norm in ["Provincial", "Municipal"]:
        if not territorio_nombre:
             raise HTTPException(status_code=400, detail="Debe especificar un territorio para este nivel")
        
        t = repo_t.get_by_nombre(territorio_nombre)
        if t:
            territorio_id = t.id
        else:
            raise HTTPException(status_code=400, detail=f"Territorio '{territorio_nombre}' no encontrado")
    
    # 4. Crear usuario con datos normalizados
    hashed_password = get_password_hash(password)
    new_user = Usuario(
        username=username_norm,
        email=email_norm,
        hashed_password=hashed_password,
        nivel_acceso=nivel_norm,
        territorio_id=territorio_id
    )
    
    repo_u.create(new_user)
    
    return {"message": "Usuario registrado exitosamente", "username": username_norm}


@app.post("/registros/operacion", tags=["CRUD Operativo"])
def crear_registro(
    registro: RegistroBalance, 
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    if current_user.nivel_acceso not in ["Nacional", "Provincial"]:
        raise HTTPException(status_code=403, detail="No autorizado")
    
    repo = RegistroBalanceRepository(session)
    return repo.create(registro)


@app.get("/analitica/proyecciones/{territorio_id}", tags=["Analítica Avanzada"])
def obtener_proyeccion_abastecimiento(territorio_id: int, session: Session = Depends(get_session)):
    """
    Analítica Avanzada: Predice disponibilidad basada en los últimos 3 años.
    """
    statement = (
        select(RegistroBalance)
        .where(RegistroBalance.territorio_id == territorio_id)
        .order_by(RegistroBalance.año.desc()).limit(3)
    )
    historico = session.exec(statement).all()
    
    if len(historico) < 2:
        return {"proyeccion": "Insuficiente información histórica"}
    
    # Cálculo simple de tendencia (Data Science básico)
    promedio = sum(r.disponible for r in historico) / len(historico)
    return {
        "año_proximo": 2024,
        "disponibilidad_estimada_tn": round(promedio * 1.03, 2),
        "nivel_riesgo": "Bajo" if promedio > 500 else "Alto"
    }
@app.get("/usuarios/me", tags=["Autenticación"])
def read_users_me(
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session) 
):
    """Obtener información completa del usuario actual incluyendo su territorio"""
    nombre_t = None
    
    # Si el usuario tiene un territorio asignado, buscamos su nombre
    if current_user.territorio_id:
        territorio = session.get(Territorio, current_user.territorio_id)
        if territorio:
            nombre_t = territorio.nombre

    return {
        "username": current_user.username,
        "email": current_user.email,
        "nivel_acceso": current_user.nivel_acceso,
        "territorio_id": current_user.territorio_id,
        "territorio_nombre": nombre_t,  
        "activo": current_user.activo
    }

# =================================================================
# 4. ENDPOINTS DE LA API (Fase 1: Analítica e Ingestión)
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
def listar_territorios(
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):
    """
    Devuelve territorios según el nivel de acceso del usuario.
    """

    # Usuario nacional ve todo
    if current_user.nivel_acceso == "Nacional":

        return session.exec(
            select(Territorio)
        ).all()


    # Usuario provincial ve su provincia y municipios hijos
    elif current_user.nivel_acceso == "Provincial":

        territorios = session.exec(
            select(Territorio)
            .where(
                (Territorio.id == current_user.territorio_id) |
                (Territorio.padre_id == current_user.territorio_id)
            )
        ).all()

        return territorios


    # Usuario municipal solo ve su municipio
    elif current_user.nivel_acceso == "Municipal":

        territorio = session.get(
            Territorio,
            current_user.territorio_id
        )

        if territorio:
            return [territorio]

        return []


    return []

@app.get("/productos", response_model=List[Producto], tags=["Productos"])
def listar_productos(session: Session = Depends(get_session)):
    repo = ProductoRepository(session)
    return repo.get_all()

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

@app.get("/analitica/municipios-provincia")
def obtener_municipios_provincia(
    provincia_nombre:str,
    producto_nombre:str="Todos",
    session:Session=Depends(get_session)
):

    provincia=session.exec(

        select(Territorio)

        .where(Territorio.nombre==provincia_nombre)

        .where(Territorio.nivel=="Provincial")

    ).first()

    if not provincia:

        raise HTTPException(404)

    statement=(

        select(

            Territorio.nombre,

            func.sum(RegistroBalance.disponible),

            func.sum(RegistroBalance.mermas)

        )

        .join(
            RegistroBalance,
            Territorio.id==RegistroBalance.territorio_id
        )

        .where(Territorio.padre_id==provincia.id)

        .where(Territorio.nivel=="Municipal")

    )

    if producto_nombre!="Todos":

        statement=(

            statement

            .join(
                Producto,
                Producto.id==RegistroBalance.producto_id
            )

            .where(
                Producto.nombre==producto_nombre
            )

        )

    statement=statement.group_by(Territorio.nombre)

    datos=session.exec(statement).all()

    respuesta=[]

    for r in datos:

        ratio=0

        if r[1]>0:

            ratio=r[2]/r[1]

        respuesta.append({

            "municipio":r[0],

            "disponible_tn":round(r[1],2),

            "mermas_tn":round(r[2],2),

            "ratio_perdida":round(ratio*100,2),

            "estado":"CRÍTICO" if ratio>0.15 else "ESTABLE"

        })

    return respuesta

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

@app.get("/territorios/lista/{nivel}")
def obtener_lista_por_nivel(
    nivel: str,
    padre_nombre: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user),
    session: Session = Depends(get_session)
):

    repo = TerritorioRepository(session)


    # MUNICIPAL
    if current_user.nivel_acceso == "Municipal":

        territorio = session.get(
            Territorio,
            current_user.territorio_id
        )

        return [territorio] if territorio else []


    # PROVINCIAL
    if current_user.nivel_acceso == "Provincial":

        if nivel == "Municipal":

            return repo.get_by_padre(
                current_user.territorio_id
            )

        return [
            session.get(
                Territorio,
                current_user.territorio_id
            )
        ]


    # NACIONAL
    return repo.get_by_nivel(nivel)
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


@app.get("/analitica/municipio-individual")
def obtener_municipio_individual(
    territorio_id:int,
    producto_nombre:str="Todos",
    session:Session=Depends(get_session)
):


    statement = (
        select(
            Territorio.nombre,
            func.sum(RegistroBalance.disponible).label("disponible"),
            func.sum(RegistroBalance.mermas).label("mermas")
        )
        .join(
            RegistroBalance,
            Territorio.id==RegistroBalance.territorio_id
        )
        .where(
            Territorio.id==territorio_id
        )
        .where(
            Territorio.nivel=="Municipal"
        )
    )


    if producto_nombre!="Todos":

        statement = (
            statement
            .join(
                Producto,
                Producto.id==RegistroBalance.producto_id
            )
            .where(
                Producto.nombre==producto_nombre
            )
        )


    statement = statement.group_by(
        Territorio.nombre
    )


    resultado=session.exec(statement).all()


    return [
        {
            "municipio":r[0],
            "disponible_tn":round(r[1],2),
            "mermas_tn":round(r[2],2)
        }
        for r in resultado
    ]
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