import pandas as pd
import redis
from dotenv import load_dotenv
import os 
import json
from util import normalizar_texto, limpiar_clave_json

load_dotenv()

# Ruta del archivo de Excel
file_path = "horario.xlsx"  # Cambia esto por la ruta real de tu archivo

f = open("materias.txt","w")
REDIS_HOST = os.getenv("url_redis")
REDIS_PORT = os.getenv("port_redis")
REDIS_DB = os.getenv("db_redis")
DIA = "Martes"

redis_client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

# Cargar el archivo Excel
file_path = f"Aulas {DIA} 170225.xlsx"
df = pd.read_excel(file_path, sheet_name="2025_1", skiprows=19, dtype=str, keep_default_na=False)  # Omitir las primeras 19 filas

# Seleccionar columnas relevantes
#df = df.iloc[:, [1, 15, 22, 73]]  # B, P, W, BU

#df.columns = ["asignatura", "carrera", "seccion", "aula"]

# Limpiar datos eliminando filas vacías
df = df.dropna()

# Crear la estructura en Redis
actualizaciones = 0
no_actualizado = 0
for _, row in df.iterrows():
    try:
        carrera = row.iloc[15]
        str_asignatura = row.iloc[1]
        id_asignatura = normalizar_texto(limpiar_clave_json(row.iloc[1]))
        seccion = row.iloc[22]
        aula = row.iloc[73]
#        print(f"se actualizo {id_asignatura} - {carrera} - {seccion} - {aula} - {DIA}: ")
        if carrera and str_asignatura and seccion and aula:
            resAnt = redis_client.json().get("por_carrera",f"$.{carrera}.asignaturas.{id_asignatura}.secciones.{seccion}.clases.{DIA}.aula")
            if resAnt != aula:
                redis_client.json().set("por_carrera",f"$.{carrera}.asignaturas.{id_asignatura}.secciones.{seccion}.clases.{DIA}.aula",aula)
                res = redis_client.json().get("por_carrera",f"$.{carrera}.asignaturas.{id_asignatura}.secciones.{seccion}.clases.{DIA}.aula")
                print(f"se actualizo {id_asignatura} - {carrera} - {seccion} - {aula} - {DIA}: {resAnt}/{res}")
                actualizaciones += 1
        else:
            no_actualizado += 1
            
    except Exception as e:
        print(f"no se actualizo {id_asignatura} - {carrera} - {seccion} - {e}")
        no_actualizado += 1
print(f"cant actualizaciones:{actualizaciones}")
print(f"cant no actualizados:{no_actualizado}")
print("Datos cargados en Redis correctamente.")
