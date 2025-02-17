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


client = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)

def verificar_dias_de_clase(row):
    #Lunes    Martes   Miercol  Jueves   Viernes  Sabado
    #AI y AJ, AK y AL, AM y AN, AO y AP, AQ y AR, AS y AT
    #34   35  36   37  38   39  40   41  42   43  44   45
    dias = {
            "Lunes":[34,35],
            "Martes":[36,37],
            "Miercoles":[38,39],
            "Jueves":[40,41],
            "Viernes":[42,43],
            "Sabado":[44,45]
        }
    d = {"clases":{}}
    for key in dias.keys():
        if not pd.isna(row.iloc[dias[key][1]]):
            horario = row.iloc[dias[key][1]]
            aula = row.iloc[dias[key][0]] if not pd.isna(row.iloc[dias[key][0]]) else "No disponible"
            d["clases"][key] = {"horario":horario, "aula":aula}
    return d
        
        
def main():
    # Cargar el archivo de Excel
    xls = pd.ExcelFile(file_path)   
    materias = {}
    # Obtener los nombres de todas las hojas
    sheets = xls.sheet_names
    print(f"El archivo tiene {len(sheets)} hojas: {sheets}")
    client.json().set("materias", f"$", {})
    # Recorrer cada hoja y mostrar las primeras filas
    sheet  = sheets[0]
    if not client.json().get("por_carrera"):
        client.json().set("por_carrera", ".", {})
    for sheet in sheets:
            print(f"\nProcesando hoja: {sheet}")
            client.json().set("por_carrera", f"$.{sheet}", {})
            client.json().set("por_carrera", f"$.{sheet}.asignaturas", {})
            # Leer los primeros 15 registros para inspección
            df = pd.read_excel(file_path, sheet_name=sheet, skiprows=10, dtype=str, keep_default_na=False)
            df = df.map(normalizar_texto)

            #C,J,M,N
            for index, row in df.iterrows():
                str_asignatura = row.iloc[2]  # Tercera columna (índice 2)
                id_asignatura = limpiar_clave_json(row.iloc[2])  # Tercera columna (índice 2)
                seccion = limpiar_clave_json(row.iloc[9])
                nom_prof = row.iloc[13] if not pd.isna(row.iloc[13]) else "No disponible"
                ape_prof = row.iloc[12] if not pd.isna(row.iloc[12]) else "No disponible"
                clases = verificar_dias_de_clase(row)
                if str_asignatura != "" and seccion != "":
                    print(f"Procesando '{str_asignatura}' - {seccion}")
                    print("la asignatura no existe" if len(client.json().get("por_carrera",f"$.{sheet}.asignaturas.{id_asignatura}")) == 0 else "la asignatura existe")
                    print("la seccion de la asignatura no existe" if len(client.json().get("por_carrera",f"$.{sheet}.asignaturas.{id_asignatura}.secciones.{seccion}")) == 0 else "la seccion de la asignatura existe")
                    print(client.json().get("por_carrera",f"$.{sheet}.asignaturas.{id_asignatura}.secciones"))
                    if len(client.json().get("por_carrera",f"$.{sheet}.asignaturas.{id_asignatura}")) == 0:
                        try:
                            print(f"se agrega '{str_asignatura}' con la seccion {seccion} como '{id_asignatura}'")
                            client.json().set("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}",{})
                            client.json().set("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}.secciones",{})
                            client.json().set("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}.secciones.{seccion}",{
                                                    "nom_prof": nom_prof,
                                                    "ape_prof": ape_prof,
                                                    "clases": clases["clases"]
                                                }
                                            )
                            client.json().set("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}.nombre", str_asignatura)
                        except Exception as e:
                            print(f"no se pudo agregar {id_asignatura}")
                            print(e)
                            return
                    elif len(client.json().get("por_carrera",f"$.{sheet}.asignaturas.{id_asignatura}.secciones.{seccion}")) == 0:
                        try:
                            print(f"se agrega la seccion {seccion} de '{str_asignatura}\n'")
                            secciones_asignatura = client.json().get("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}.secciones")[0]
                            asig_datos = {
                                "nom_prof": nom_prof,
                                "ape_prof": ape_prof,
                                "clases": clases["clases"]
                            }
                            secciones_asignatura[seccion] = asig_datos
                            client.json().set("por_carrera", f"$.{sheet}.asignaturas.{id_asignatura}.secciones",secciones_asignatura)
                            print(f"se agrega {id_asignatura} - {seccion}")
                        except Exception as e:
                            print(f"No se pudo agregar {id_asignatura} - {seccion}")
                            print(f"nom_prof: {nom_prof}")
                            print(f"ape_prof: {ape_prof}")
                            print(e)
                            return                            





if __name__ == "__main__":
    main()