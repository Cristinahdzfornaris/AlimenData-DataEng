from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional

class Territorio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    nivel: str # Nacional, Provincial, Municipal
    padre_id: Optional[int] = Field(default=None, foreign_key="territorio.id")

class Producto(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    categoria: str

class RegistroBalance(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    año: int
    producto_id: int = Field(foreign_key="producto.id")
    territorio_id: int = Field(foreign_key="territorio.id")
    mermas: float = 0.0
    importacion: float = 0.0
    disponible: float = 0.0
    consumo_per_capita: float = 0.0  # kg/persona/año