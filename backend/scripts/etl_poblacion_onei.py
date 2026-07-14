import sys
import os
import pandas as pd
import numpy as np
import unicodedata
from sqlalchemy import create_engine
from sqlmodel import Session, select 

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from models import Territorio, PoblacionHistorica, RegistroBalance 
from repositories import TerritorioRepository, PoblacionHistoricaRepository

engine = create_engine(os.getenv("DATABASE_URL"))

def normalizar_texto(texto):
    """
    Función crítica para integración: Elimina tildes, convierte a minúsculas 
    y limpia espacios para que los nombres de la FAO y ONEI coincidan.
    """
    if not texto or pd.isna(texto): return ""
    s = str(texto).strip().lower()
    # Eliminar tildes (Río -> rio)
    s = ''.join(c for c in unicodedata.normalize('NFD', s)
                if unicodedata.category(c) != 'Mn')
    # Eliminar prefijos comunes en reportes de la ONEI
    s = s.replace("mpio. ", "").replace("prov. ", "").replace("municipio ", "")
    return s

def procesar_excel_onei():
    """Procesar archivo Excel de población ONEI con normalización de nombres"""
    print("📊 Leyendo archivo Excel de ONEI...")
    path_excel = "/data/3.5-poblacion-residente-clasificada-por-sexo-zonas-urbana-y-rural-provincias-y-municipios (2).xls"
    
    try:
        df = pd.read_excel(path_excel)
    except Exception as e:
        print(f"❌ No se pudo leer el Excel: {e}")
        return

    # IDENTIFICACIÓN DINÁMICA DE AÑOS
    mapeo_columnas_año = {}
    for i, col in enumerate(df.columns):
        col_str = str(col)
        for anio in range(2006, 2024):
            if str(anio) in col_str:
                mapeo_columnas_año[anio] = i
                break
    
    años_encontrados = sorted(list(mapeo_columnas_año.keys()))
    print(f"📅 Años detectados en el Excel: {años_encontrados}")
    
    with Session(engine) as session:
        territorio_repo = TerritorioRepository(session)
        poblacion_repo = PoblacionHistoricaRepository(session)
        
        todos_territorios_db = territorio_repo.get_all()
        registros_creados = 0
        
        for año in años_encontrados:
            print(f"🔄 Procesando año {año}...")
            idx_inicio_año = mapeo_columnas_año[año]
            
            for idx, row in df.iterrows():
                nombre_raw = row.iloc[0]
                if pd.isna(nombre_raw): continue
                
                nombre_excel = str(nombre_raw).strip()
                
                # Saltar filas basura
                if nombre_excel.lower() in ["cuba", "provincias y municipios", "poblacion residente"]:
                    continue

                nombre_excel_norm = normalizar_texto(nombre_excel)
                territorio = None
                
                for t in todos_territorios_db:
                    if normalizar_texto(t.nombre) == nombre_excel_norm:
                        territorio = t
                        break
                
                if territorio:
                    try:
                        
                        pob_total = row.iloc[idx_inicio_año]
                        
                        if not isinstance(pob_total, (int, float, np.number)):
                            pob_total = row.iloc[idx_inicio_año + 1]
                            
                        pob_total = int(pob_total) if not pd.isna(pob_total) else 0
                        
                        if pob_total > 100: 
                            existente = poblacion_repo.get_by_territorio_y_año(territorio.id, año)
                            if not existente:
                                poblacion_hist = PoblacionHistorica(
                                    año=año,
                                    territorio_id=territorio.id,
                                    poblacion_total=pob_total
                                )
                                session.add(poblacion_hist)
                                registros_creados += 1
                    except:
                        continue
            
            session.commit()
            
        print(f"✅ ETL ONEI completado. {registros_creados} registros de población creados.")

def calcular_equidad_per_capita():
    """
    UNE FAO + ONEI: El corazón de la Fase 2.
    Calcula cuántos Kg de alimento tocan por persona al año.
    """
    print("⚖️ Calculando indicadores de equidad per cápita (Ingestión Cruzada)...")
    
    with Session(engine) as session:
        balances = session.exec(select(RegistroBalance)).all()
        pob_repo = PoblacionHistoricaRepository(session)
        
        actualizados = 0
        
        for bal in balances:
            pob_data = pob_repo.get_by_territorio_y_año(bal.territorio_id, bal.año)
            
            if pob_data and pob_data.poblacion_total > 0:
                # FÓRMULA: (Toneladas de Alimento * 1000) / Número de habitantes
                consumo_kg = (bal.disponible * 1000) / pob_data.poblacion_total
                bal.consumo_per_capita = round(consumo_kg, 4)
                session.add(bal)
                actualizados += 1
        
        session.commit()
        print(f"✅ ÉXITO: {actualizados} registros actualizados con indicadores de equidad.")

if __name__ == "__main__":
    try:
        procesar_excel_onei()
        calcular_equidad_per_capita()
    except Exception as e:
        print(f"❌ Error crítico: {e}")
        import traceback
        traceback.print_exc()