from fastapi import FastAPI, Query
import redis
import json
from util import normalizar_texto, limpiar_clave_json, split_array
import requests
from dotenv import load_dotenv
import os
from pydantic import BaseModel
load_dotenv()

REDIS_HOST = os.getenv("url_redis")
REDIS_PORT = os.getenv("port_redis")
REDIS_DB = os.getenv("db_redis")
TOKEN = os.getenv("t_key")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = FastAPI()

# Conectar a Redis
r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)

# Diccionario de sesiones por usuario
chat_sessions = {}

class TelegramUpdate(BaseModel):
    update_id: int
    message: dict


PAGE_SIZE = 25  # Tamaño de cada página de materias

@app.post("/")
async def telegram_webhook(update: TelegramUpdate):
    data = update.model_dump()  # Cambiado de dict() a model_dump()
    chat_id = data['message']['chat']['id']
    nombre = data['message']['from']['first_name']
    mensaje = data['message']['text']
    text = chat(chat_id, mensaje, nombre)["response"]

    requests.get(f"{BASE_URL}/sendMessage?chat_id={chat_id}&text={text}")
    return {"recibido":mensaje, "enviado":text}


def chat(user_id: str, message: str, username:str):
    """
    Chatbot basado en Redis para consultar carreras, materias y secciones.
    """

    # Iniciar nueva sesión si el usuario no existe o quiere reiniciar
    if user_id not in chat_sessions or message.lower() in ["reiniciar", "reset"]:
        chat_sessions[user_id] = {"step": "seleccion_carrera"}
        
        # Obtener carreras desde Redis
        carreras = r.json().get("por_carrera",f"$")[0].keys()
        carreras_texto = "\n".join([f"{idx+1}) {carrera}" for idx, carrera in enumerate(carreras)])
        
        return {"response": f"Hola {username}, ¿cómo estás? Un gusto saludarte, mi nombre es TuVotcito 🗣️!\n"
                            "Por favor, ingresa la carrera a la que perteneces para indicarte la información de tus materias:\n"
                            f"{carreras_texto}\n\nSelecciona una opción."}

    # Paso 1: Seleccionar Carrera
    if chat_sessions[user_id]["step"] == "seleccion_carrera":
        try:
            seleccion = int(message.strip()) - 1
            carreras = list(r.json().get("por_carrera",f"$")[0].keys())

            if 0 <= seleccion < len(carreras):
                carrera = carreras[seleccion]
                print(carrera)
                chat_sessions[user_id]["carrera"] = carrera
                chat_sessions[user_id]["step"] = "seleccion_materia"
                chat_sessions[user_id]["page"] = 0
                
                # Obtener materias de la carrera
                carrera_data = r.json().get("por_carrera",f"$.{carrera}")[0]
                materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]
                materias_paginadas = split_array(materias, PAGE_SIZE)
                page = chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])
                nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia."

                return {"response": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                f"{materias_texto}{nav_text}"}
            else:
                return {"response": "Selecciona una opción válida."}
        except ValueError:
            return {"response": "Ingresa un número válido."}

    # Paso 2: Seleccionar Materia
    if chat_sessions[user_id]["step"] == "seleccion_materia":
        try:
            # Obtener la carrera seleccionada
            carrera = chat_sessions[user_id]["carrera"]
            carrera_data = r.json().get("por_carrera", f"$.{carrera}")[0]
            materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]

            # Dividir las materias en páginas
            materias_paginadas = split_array(materias, PAGE_SIZE)
            if message.strip().isnumeric():
                seleccion = int(message.strip()) - 1
                if seleccion == -1:
                    carreras = r.json().get("por_carrera",f"$")[0].keys()
                    carreras_texto = "\n".join([f"{idx+1}) {carrera}" for idx, carrera in enumerate(carreras)])
                    chat_sessions[user_id]["step"] = "seleccion_carrera"
                    return {"response": "Por favor, ingresa la carrera a la que perteneces:\n"
                                        f"{carreras_texto}\n\nSelecciona una opción o 0 para volver atrás."}

                if 0 <= seleccion < len(materias_paginadas[chat_sessions[user_id]["page"]]):
                    materia = limpiar_clave_json(materias_paginadas[chat_sessions[user_id]["page"]][seleccion])
                    print(f"se ha seleccionado {materia}")
                    
                    chat_sessions[user_id]["materia"] = materia
                    chat_sessions[user_id]["step"] = "seleccion_seccion"

                    # Obtener secciones de la materia
                    secciones = carrera_data["asignaturas"][materia]["secciones"].keys()
                    str_materia = carrera_data["asignaturas"][materia]["nombre"]
                    secciones_texto = "\n".join([f"{idx+1}) {seccion}" for idx, seccion in enumerate(secciones)])

                    return {"response": f"Estas son las secciones que conozco de {str_materia}:\n"
                                        f"{secciones_texto}\n\nSelecciona una opción o 0 para volver atrás."}
                else:
                    return {"response": "Selecciona una opción válida, 0 para seleccionar carrera y 'S' o 'A' para desplazarte entre las opciones."}
            else:
                # Navegación entre páginas
                if message.strip().upper() == "S":  # Siguiente página
                    if chat_sessions[user_id]["page"] < len(materias_paginadas) - 1:
                        chat_sessions[user_id]["page"] += 1

                elif message.strip().upper() == "A":  # Página anterior
                    if chat_sessions[user_id]["page"] > 0:
                        chat_sessions[user_id]["page"] -= 1

                # Obtener las materias de la página actual
                page = chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])

                # Agregar indicación de navegación
                nav_text = "\n\nEscribe 'S' para Siguiente, 'A' para Anterior, o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."
                if page == 0:
                    nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."
                elif page == len(materias_paginadas) - 1:
                    nav_text = "\n\nEscribe 'A' para Anterior o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."

                return {"response": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                    f"{materias_texto}{nav_text}"}
        except ValueError:
            return {"response": "Selecciona una opción válida, 0 para seleccionar carrera y 'S' o 'A' para desplazarte entre las opciones."}


    # Paso 3: Seleccionar Sección
    if chat_sessions[user_id]["step"] == "seleccion_seccion":
        try:
            seleccion = int(message.strip()) - 1
            carrera = chat_sessions[user_id]["carrera"]
            materia = chat_sessions[user_id]["materia"]
            carrera_data = r.json().get("por_carrera",f"$.{carrera}")[0]
            secciones = list(carrera_data["asignaturas"][materia]["secciones"].keys())

            if seleccion == -1:
                chat_sessions[user_id]["step"] = "seleccion_materia"
                chat_sessions[user_id]["page"] = 0
                
                # Obtener materias de la carrera
                carrera_data = r.json().get("por_carrera",f"$.{carrera}")[0]
                materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]
                materias_paginadas = split_array(materias, PAGE_SIZE)
                page = chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])
                nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia."

                return {"response": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                f"{materias_texto}{nav_text}"}


            if 0 <= seleccion < len(secciones):
                seccion = secciones[seleccion]

                # Obtener datos de la sección seleccionada
                seccion_data = carrera_data["asignaturas"][materia]["secciones"][seccion]
                str_materia = carrera_data["asignaturas"][materia]["nombre"]
                print(seccion_data)
                if "clases" in seccion_data and seccion_data["clases"] != {}:
                    clases_texto = "\n".join([f"{dia}: {clase['horario']} - Aula: {clase['aula']}" 
                                            for dia, clase in seccion_data["clases"].items()])
                    respuesta = (f"Estos son los datos de {str_materia} para la sección {seccion}:\n"
                             f"👨‍🏫 Profesor: {seccion_data['nom_prof']} {seccion_data['ape_prof']}\n"
                             f"📚 Clases:\n{clases_texto}\n\n"
                             "Si deseas consultar otra materia, no dudes en escribirme.")
                else:
                    respuesta = (f"Estos son los datos de {str_materia} para la sección {seccion}:\n"
                             f"👨‍🏫 Profesor: {seccion_data['nom_prof']} {seccion_data['ape_prof']}\n"
                             f"📚 Clases:\nAún no cuento con información acerca de los horarios y las aulas para esta materia 🥺.\n\n"
                             "Si deseas consultar otra materia, no dudes en escribirme.")

                # Reiniciar el chat después de responder
                del chat_sessions[user_id]

                return {"response": respuesta}
            else:
                return {"response": "Selecciona una opción válida o 0 para volver atrás."}
        except ValueError:
            return {"response": "Ingresa un número válido."}

    return {"response": "Algo salió mal. Intenta nuevamente."}
