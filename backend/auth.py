from datetime import datetime, timedelta
from typing import Optional, Generator
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlmodel import Session, select, create_engine
from models import Usuario
import os

# Configuración JWT
SECRET_KEY = "your-secret-key-change-in-production"  # Debe venir de variables de entorno
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# Configuración de base de datos
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL, echo=False)

def get_session() -> Generator[Session, None, None]:
    """Obtener sesión de base de datos"""
    with Session(engine) as session:
        yield session

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verificar contraseña de forma segura"""
    try:
        # Forzamos la verificación
        return pwd_context.verify(plain_password, hashed_password)
    except Exception as e:
        print(f"DEBUG AUTH: Error verificando password: {e}")
        return False
def get_password_hash(password: str) -> str:
    """Hashear contraseña"""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Crear token de acceso JWT"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def get_current_user(token: str = Depends(oauth2_scheme), session: Session = Depends(get_session)) -> Usuario:
    """Obtener usuario actual del token JWT"""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = session.exec(select(Usuario).where(Usuario.username == username)).first()
    if user is None:
        raise credentials_exception
    return user

def check_access_level(current_user: Usuario, required_level: str, territorio_id: Optional[int] = None) -> bool:
    """Verificar nivel de acceso del usuario"""
    # Nacional tiene acceso a todo
    if current_user.nivel_acceso == "Nacional":
        return True
    
    # Provincial tiene acceso a su provincia
    if current_user.nivel_acceso == "Provincial":
        if required_level == "Nacional":
            return False
        if territorio_id is None:
            return True
        return current_user.territorio_id == territorio_id
    
    # Municipal tiene acceso solo a su municipio
    if current_user.nivel_acceso == "Municipal":
        if required_level in ["Nacional", "Provincial"]:
            return False
        if territorio_id is None:
            return True
        return current_user.territorio_id == territorio_id
    
    return False
