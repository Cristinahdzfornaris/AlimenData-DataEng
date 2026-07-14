from typing import List, Optional
from sqlmodel import Session, select
from models import Usuario, Territorio, Producto, RegistroBalance, PoblacionHistorica
from sqlmodel import Session, select, func
class BaseRepository:
    """Repositorio base con operaciones CRUD genéricas"""
    
    def __init__(self, session: Session, model):
        self.session = session
        self.model = model
    
    def get_by_id(self, id: int) -> Optional[object]:
        """Obtener entidad por ID"""
        return self.session.get(self.model, id)
    
    def get_all(self) -> List[object]:
        """Obtener todas las entidades"""
        return self.session.exec(select(self.model)).all()
    
    def create(self, entity: object) -> object:
        """Crear nueva entidad"""
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    def update(self, entity: object) -> object:
        """Actualizar entidad existente"""
        self.session.add(entity)
        self.session.commit()
        self.session.refresh(entity)
        return entity
    
    def delete(self, id: int) -> bool:
        """Eliminar entidad por ID"""
        entity = self.get_by_id(id)
        if entity:
            self.session.delete(entity)
            self.session.commit()
            return True
        return False

class UsuarioRepository(BaseRepository):
    """Repositorio específico para Usuario"""
    
    def __init__(self, session: Session):
        super().__init__(session, Usuario)
    
    def get_by_username(self, username: str) -> Optional[Usuario]:
        """Búsqueda insensible a mayúsculas"""
        return self.session.exec(
            select(Usuario).where(func.lower(Usuario.username) == username.lower())
        ).first()
    def get_by_email(self, email: str) -> Optional[Usuario]:
        """Obtener usuario por email"""
        return self.session.exec(select(Usuario).where(Usuario.email == email)).first()
    
    def get_by_nivel_acceso(self, nivel_acceso: str) -> List[Usuario]:
        """Obtener usuarios por nivel de acceso"""
        return self.session.exec(select(Usuario).where(Usuario.nivel_acceso == nivel_acceso)).all()
    
    def get_by_territorio(self, territorio_id: int) -> List[Usuario]:
        """Obtener usuarios por territorio"""
        return self.session.exec(select(Usuario).where(Usuario.territorio_id == territorio_id)).all()

class TerritorioRepository(BaseRepository):
    """Repositorio específico para Territorio"""
    
    def __init__(self, session: Session):
        super().__init__(session, Territorio)
    
    def get_by_nombre(self, nombre: str) -> Optional[Territorio]:
        """Búsqueda insensible a mayúsculas"""
        if not nombre: return None
        return self.session.exec(
            select(Territorio).where(func.lower(Territorio.nombre) == nombre.lower())
        ).first()
    
    def get_by_nivel(self, nivel: str) -> List[Territorio]:
        """Obtener territorios por nivel (Nacional, Provincial, Municipal)"""
        return self.session.exec(select(Territorio).where(Territorio.nivel == nivel)).all()
    
    def get_by_padre(self, padre_id: int) -> List[Territorio]:
        """Obtener territorios hijos por padre"""
        return self.session.exec(select(Territorio).where(Territorio.padre_id == padre_id)).all()
    
    def get_provincias(self) -> List[str]:
        """Obtener lista de nombres de provincias"""
        provincias = self.session.exec(select(Territorio).where(Territorio.nivel == "Provincial")).all()
        return [p.nombre for p in provincias]
    
    def get_municipios_por_provincia(self, provincia_nombre: str) -> List[str]:
        """Obtener municipios de una provincia específica"""
        provincia = self.get_by_nombre(provincia_nombre)
        if provincia:
            municipios = self.session.exec(select(Territorio).where(
                Territorio.nivel == "Municipal",
                Territorio.padre_id == provincia.id
            )).all()
            return [m.nombre for m in municipios]
        return []

class ProductoRepository(BaseRepository):
    """Repositorio específico para Producto"""
    
    def __init__(self, session: Session):
        super().__init__(session, Producto)
    
    def get_by_nombre(self, nombre: str) -> Optional[Producto]:
        """Obtener producto por nombre"""
        return self.session.exec(select(Producto).where(Producto.nombre == nombre)).first()
    
    def get_by_categoria(self, categoria: str) -> List[Producto]:
        """Obtener productos por categoría"""
        return self.session.exec(select(Producto).where(Producto.categoria == categoria)).all()

class RegistroBalanceRepository(BaseRepository):
    """Repositorio específico para RegistroBalance"""
    
    def __init__(self, session: Session):
        super().__init__(session, RegistroBalance)
    
    def get_by_año(self, año: int) -> List[RegistroBalance]:
        """Obtener registros por año"""
        return self.session.exec(select(RegistroBalance).where(RegistroBalance.año == año)).all()
    
    def get_by_territorio(self, territorio_id: int) -> List[RegistroBalance]:
        """Obtener registros por territorio"""
        return self.session.exec(select(RegistroBalance).where(RegistroBalance.territorio_id == territorio_id)).all()
    
    def get_by_producto(self, producto_id: int) -> List[RegistroBalance]:
        """Obtener registros por producto"""
        return self.session.exec(select(RegistroBalance).where(RegistroBalance.producto_id == producto_id)).all()
    
    def get_by_territorio_y_año(self, territorio_id: int, año: int) -> List[RegistroBalance]:
        """Obtener registros por territorio y año"""
        return self.session.exec(select(RegistroBalance).where(
            RegistroBalance.territorio_id == territorio_id,
            RegistroBalance.año == año
        )).all()

class PoblacionHistoricaRepository(BaseRepository):
    """Repositorio específico para PoblacionHistorica"""
    
    def __init__(self, session: Session):
        super().__init__(session, PoblacionHistorica)
    
    def get_by_año(self, año: int) -> List[PoblacionHistorica]:
        """Obtener población por año"""
        return self.session.exec(select(PoblacionHistorica).where(PoblacionHistorica.año == año)).all()
    
    def get_by_territorio(self, territorio_id: int) -> List[PoblacionHistorica]:
        """Obtener población por territorio"""
        return self.session.exec(select(PoblacionHistorica).where(PoblacionHistorica.territorio_id == territorio_id)).all()
    
    def get_by_territorio_y_año(self, territorio_id: int, año: int) -> Optional[PoblacionHistorica]:
        """Obtener población por territorio y año"""
        return self.session.exec(select(PoblacionHistorica).where(
            PoblacionHistorica.territorio_id == territorio_id,
            PoblacionHistorica.año == año
        )).first()
    
    def get_rango_anios(self) -> List[int]:
        """Obtener rango de años disponibles"""
        resultados = self.session.exec(select(PoblacionHistorica.año).distinct()).all()
        return sorted([r.año for r in resultados])
