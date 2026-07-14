from sqlmodel import SQLModel, Field, Relationship
from typing import List, Optional
from datetime import datetime

class Territorio(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str = Field(index=True)
    nivel: str = Field(index=True)  
    tipo_entidad: str = Field(default="Punto de Venta")

    padre_id: Optional[int] = Field(
        default=None,
        foreign_key="territorio.id"
    )

    padre: Optional["Territorio"] = Relationship(
        back_populates="hijos",
        sa_relationship_kwargs={
            "remote_side": "Territorio.id"
        }
    )

    hijos: List["Territorio"] = Relationship(
        back_populates="padre"
    )

    registros: List["RegistroBalance"] = Relationship(
        back_populates="territorio"
    )

    poblacion: List["PoblacionHistorica"] = Relationship(
        back_populates="territorio"
    )
class Producto(SQLModel, table=True):

    id: Optional[int] = Field(default=None, primary_key=True)

    nombre: str
    categoria: str

    registros: List["RegistroBalance"] = Relationship(
        back_populates="producto"
    )
class RegistroBalance(SQLModel, table=True):

    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    año: int

    producto_id: int = Field(
        foreign_key="producto.id"
    )

    territorio_id: int = Field(
        foreign_key="territorio.id"
    )


    mermas: float = 0.0
    importacion: float = 0.0
    disponible: float = 0.0
    consumo_per_capita: float = 0.0


    producto: Optional["Producto"] = Relationship(
        back_populates="registros"
    )


    territorio: Optional["Territorio"] = Relationship(
        back_populates="registros"
    )

class Usuario(SQLModel, table=True):

    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    username: str = Field(
        unique=True,
        index=True
    )

    email: str = Field(
        unique=True,
        index=True
    )

    hashed_password: str

    nivel_acceso: str

    territorio_id: Optional[int] = Field(
        default=None,
        foreign_key="territorio.id"
    )

    activo: bool = True

    creado_en: datetime = Field(
        default_factory=datetime.utcnow
    )


    territorio: Optional["Territorio"] = Relationship()
class PoblacionHistorica(SQLModel, table=True):

    id: Optional[int] = Field(
        default=None,
        primary_key=True
    )

    año: int

    territorio_id: int = Field(
        foreign_key="territorio.id"
    )

    poblacion_total: int = 0
    poblacion_urbana: int = 0
    poblacion_rural: int = 0

    hombres: int = 0
    mujeres: int = 0


    territorio: Optional["Territorio"] = Relationship(
        back_populates="poblacion"
    )