import pandas as pd
import numpy as np
import os
import sys
from sqlmodel import Session, create_engine, select

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import RegistroBalance, Producto, Territorio

engine = create_engine(os.getenv("DATABASE_URL"))

def run_etl():
    print("🚀 Iniciando ETL de la FAO (Inventarios y Red Logística)...")
    df = pd.read_csv("/data/cuba_fao_data.csv")
    
    # OPTIMIZACIÓN: Filtrar solo elementos relevantes para reducir tamaño
    elementos_relevantes = ['Losses', 'Food', 'Import quantity', 'Export quantity', 'Total Population - Both sexes']
    df = df[df['Element'].isin(elementos_relevantes)]
    
    # OPTIMIZACIÓN: Limitar a productos principales (top 20 por frecuencia)
    top_productos = df['Item'].value_counts().head(20).index
    df = df[df['Item'].isin(top_productos)]
    
    df = df[df['Year'] >= 2008]
    
    # Completar años faltantes con imputación ligera
    años_presentes = sorted(df['Year'].unique())
    años_objetivo = range(2008, 2024)
    años_faltantes = [y for y in años_objetivo if y not in años_presentes]
    
    if años_faltantes:
        extras = []
        for año in años_faltantes:
            for item in df['Item'].unique():
                for elem in df['Element'].unique():
                    subset = df[(df['Item']==item) & (df['Element']==elem)]
                    if not subset.empty:
                        val = subset['Value'].mean()
                        extras.append({'Year': año, 'Item': item, 'Element': elem, 'Value': val * np.random.uniform(0.98, 1.02)})
        if extras:
            df = pd.concat([df, pd.DataFrame(extras)], ignore_index=True)

    provincias = [
        "Pinar del Río", "Artemisa", "La Habana", "Mayabeque", "Matanzas",
        "Cienfuegos", "Villa Clara", "Sancti Spíritus", "Ciego de Ávila",
        "Camagüey", "Las Tunas", "Holguín", "Granma", "Santiago de Cuba",
        "Guantánamo", "Isla de la Juventud"
    ]
    
    municipios_por_provincia = {
        "Pinar del Río": ["Pinar del Río", "Consolación del Sur", "Guane", "La Palma", "Los Palacios", "Mantua", "Minas de Matahambre", "San Juan y Martínez", "San Luis", "Sandino", "Viñales"],
        "Artemisa": ["Alquízar", "Artemisa", "Bauta", "Caimito", "Guanajay", "Güira de Melena", "Mariel", "San Antonio de los Baños", "Bahía Honda", "Candelaria", "San Cristóbal"],
        "La Habana": ["Arroyo Naranjo", "Boyeros", "Centro Habana", "Cerro", "Cotorro", "Diez de Octubre", "Guanabacoa", "Habana del Este", "Habana Vieja", "La Lisa", "Marianao", "Playa", "Plaza de la Revolución", "Regla", "San Miguel del Padrón"],
        "Mayabeque": ["Batabanó", "Bejucal", "Güines", "Jaruco", "Madruga", "Melena del Sur", "Nueva Paz", "Quivicán", "San José de las Lajas", "San Nicolás de Bari", "Santa Cruz del Norte"],
        "Matanzas": ["Calimete", "Cárdenas", "Ciénaga de Zapata", "Colón", "Jagüey Grande", "Jovellanos", "Limonar", "Los Arabos", "Martí", "Matanzas", "Pedro Betancourt", "Perico", "Unión de Reyes"],
        "Villa Clara": ["Caibarién", "Camajuaní", "Cifuentes", "Corralillo", "Encrucijada", "Manicaragua", "Placetas", "Quemado de Güines", "Ranchuelo", "Remedios", "Sagua la Grande", "Santa Clara", "Santo Domingo"],
        "Cienfuegos": ["Abreus", "Aguada de Pasajeros", "Cienfuegos", "Cruces", "Cumanayagua", "Lajas", "Palmira", "Rodas"],
        "Sancti Spíritus": ["Cabaiguán", "Fomento", "Jatibonico", "La Sierpe", "Sancti Spíritus", "Taguasco", "Trinidad", "Yaguajay"],
        "Ciego de Ávila": ["Baraguá", "Bolivia", "Chambas", "Ciego de Ávila", "Ciro Redondo", "Majagua", "Morón","Florencia", "Primero de Enero", "Venezuela"],
        "Camagüey": ["Camagüey", "Carlos Manuel de Céspedes", "Esmeralda", "Florida", "Guáimaro", "Jimaguayú", "Minas", "Najasa", "Nuevitas", "Santa Cruz del Sur", "Sibanicú", "Sierra de Cubitas", "Vertientes"],
        "Las Tunas": ["Amancio", "Colombia", "Jesús Menéndez", "Jobabo", "Las Tunas", "Majibacoa", "Manatí", "Puerto Padre"],
        "Holguín": ["Antilla", "Báguanos", "Banes", "Cacocum", "Calixto García", "Cueto", "Frank País", "Gibara", "Holguín", "Mayarí", "Moa", "Rafael Freyre", "Sagua de Tánamo", "Urbano Noris"],
        "Granma": ["Bartolomé Masó", "Bayamo", "Buey Arriba", "Campechuela", "Cauto Cristo", "Guisa", "Jiguaní", "Manzanillo", "Media Luna", "Niquero", "Pilón", "Río Cauto", "Yara"],
        "Santiago de Cuba": ["Contramaestre", "Guamá", "Mella", "Palma Soriano", "San Luis", "Santiago de Cuba", "Segundo Frente", "Songo-La Maya", "Tercer Frente"],
        "Guantánamo": ["Baracoa", "Caimanera", "El Salvador", "Guantánamo", "Imías", "Maisí", "Manuel Tames", "Niceto Pérez", "San Antonio del Sur", "Yateras"],
        "Isla de la Juventud": ["Isla de la Juventud"]
    }

    poblacion_por_año = {}
    datos_poblacion = df[df['Element'] == 'Total Population - Both sexes']
    for _, row in datos_poblacion.iterrows():
        poblacion_por_año[row['Year']] = row['Value'] * 1000 

    with Session(engine) as session:
        existente = session.exec(select(Territorio)).first()
        if existente:
            print("⚠️ Los datos ya existen en la base de datos. Saltando carga para evitar duplicados.")
            return  
        # FASE 1: Registro del Nodo Nacional
        cuba = Territorio(nombre="Cuba", nivel="Nacional", tipo_entidad="Centro de Control Nacional")
        session.add(cuba); session.commit(); session.refresh(cuba)

        territorios = []
        for p_nom in provincias:
            # FASE 1: Registro como Almacén Central
            p = Territorio(nombre=p_nom, nivel="Provincial", padre_id=cuba.id, tipo_entidad="Almacén Central")
            session.add(p); session.commit(); session.refresh(p)
            territorios.append(p)
            
            for m_nom in municipios_por_provincia[p_nom]:
                # FASE 1: Registro como Punto de Venta (Bodega)
                m = Territorio(nombre=m_nom, nivel="Municipal", padre_id=p.id, tipo_entidad="Punto de Venta (Bodega)")
                session.add(m)
            session.commit() # Commit por bloque de provincia para velocidad

        productos = {}
        for item in df['Item'].unique():
            prod = Producto(nombre=item, categoria="Alimento")
            session.add(prod); session.commit(); session.refresh(prod)
            productos[item] = prod.id

        registros = []
        # -------------------------------
        # Obtener todos los municipios
        # -------------------------------

        municipios_db = session.exec(
            select(Territorio).where(Territorio.nivel=="Municipal")
        ).all()

        provincias_db = session.exec(
            select(Territorio).where(Territorio.nivel=="Provincial")
        ).all()

        registros = []

        for provincia in provincias_db:

            municipios = [
                m for m in municipios_db
                if m.padre_id == provincia.id
            ]

            cantidad_municipios = len(municipios)

            if cantidad_municipios == 0:
                continue

            factor_provincia = np.random.uniform(0.90,1.10)

            for _,row in df.iterrows():

                if row["Element"]!="Food":
                    continue

                disponible_provincia = (
                    row["Value"]*factor_provincia
                )

                perdida_provincia = (
                    disponible_provincia*
                    np.random.uniform(0.05,0.20)
                )

                # -------------------------
                # Registro Provincial
                # -------------------------

                registros.append(

                    RegistroBalance(

                        año=int(row["Year"]),

                        producto_id=productos[row["Item"]],

                        territorio_id=provincia.id,

                        disponible=round(disponible_provincia,2),

                        mermas=round(perdida_provincia,2),

                        importacion=0,

                        consumo_per_capita=0

                    )

                )

                # -------------------------
                # Distribuir municipios
                # -------------------------

                pesos=np.random.dirichlet(
                    np.ones(cantidad_municipios)
                )

                for municipio,peso in zip(municipios,pesos):

                    disponible=disponible_provincia*peso

                    mermas=perdida_provincia*peso*np.random.uniform(0.9,1.1)

                    registros.append(

                        RegistroBalance(

                            año=int(row["Year"]),

                            producto_id=productos[row["Item"]],

                            territorio_id=municipio.id,

                            disponible=round(disponible,2),

                            mermas=round(mermas,2),

                            importacion=0,

                            consumo_per_capita=0

                        )

                    )

        session.add_all(registros)

        session.commit()
        
    print(f"✅ ETL FAO Completado: {len(registros)} registros de inventario creados con perfiles logísticos.")

if __name__ == "__main__":
    run_etl()