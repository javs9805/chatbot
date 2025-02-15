from fastapi import FastAPI, Query
import json
import redis 
from dotenv import load_dotenv
import os
import unicodedata
from util import normalizar_texto, limpiar_clave_json
import requests
from pydantic import BaseModel
load_dotenv()

REDIS_HOST = os.getenv("url_redis")
REDIS_PORT = os.getenv("port_redis")
REDIS_DB = os.getenv("db_redis")
TOKEN = os.getenv("t_key")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = FastAPI()

# Cargar datos desde el Excel
r = redis.StrictRedis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB, decode_responses=True)
# Diccionario de sesiones por usuario
chat_sessions = {}


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict

@app.post("/")
async def telegram_webhook(update: TelegramUpdate):
    data = update.model_dump()  # Cambiado de dict() a model_dump()
    chat_id = data['message']['chat']['id']
    nombre = data['message']['from']['first_name']
    mensaje = data['message']['text']
    text = chat(chat_id, mensaje, nombre)["response"]

    requests.get(f"{BASE_URL}/sendMessage?chat_id={chat_id}&text={text}")
    return update


def chat(user_id: str, message: str, username:str):
    if user_id not in chat_sessions or message.lower() in ["reiniciar", "reset"]:
        chat_sessions[user_id] = {"step": "inicio"}
               
        return {"response": f"Hola {username}, ¿cómo estás? Bienvenido al chatbot!\n"
                            "Ingresa una palabra clave de la materia que estás buscando, ejemplo: Aerodinamica"}

    # Paso 1: Buscar materias por palabra clave
    if chat_sessions[user_id]["step"] == "inicio":
        # Buscar materias que coincidan en Redis
        json_data = r.json().get("materias","$..nombre")
        materias_coincidentes = []
        for key in json_data:
            if normalizar_texto(message.lower()) in key.lower():
                materias_coincidentes.append(key)

        if not materias_coincidentes:
            return {"response": "No encontré materias con esa palabra clave. Inténtalo nuevamente."}

        # Guardar coincidencias en la sesión del usuario
        chat_sessions[user_id]["materias"] = materias_coincidentes
        chat_sessions[user_id]["step"] = "seleccion_materia"

        materias_texto = "\n".join([f"{idx+1}) {materia}" for idx, materia in enumerate(materias_coincidentes)])
        return {"response": f"Estas son las coincidencias que tengo:\n{materias_texto}\n\nSelecciona una de ellas enviando el número correspondiente o presiona 0 para reintentar."}

    # Paso 2: Selección de materia
    if chat_sessions[user_id]["step"] == "seleccion_materia":
        try:
            seleccion = int(message.strip()) - 1
            if seleccion == -1:
                chat_sessions[user_id]["step"] = "inicio"
                return {"response": "Ingresa una palabra clave de la materia que estás buscando."}

            materias = chat_sessions[user_id]["materias"]
            if 0 <= seleccion < len(materias):
                materia = materias[seleccion]
                chat_sessions[user_id]["materia"] = materia
                chat_sessions[user_id]["step"] = "seleccion_seccion"
                id_materia = limpiar_clave_json(materia)
                # Obtener datos desde Redis
                materia_data = r.json().get("materias",f"$.{id_materia}")[0]
                print(materia_data)
                # Filtrar secciones disponibles
                secciones_disponibles = materia_data["secciones"].keys()
                secciones_texto = "\n".join([f"{idx+1}) {seccion}" for idx, seccion in enumerate(secciones_disponibles)])

                return {"response": f"Selecciona una sección que deseas consultar de {materia_data['nombre']}:\n{secciones_texto}"}
            else:
                return {"response": "Por favor, selecciona un número válido de la lista o presiona 0 para reintentar."}
        except ValueError:
            return {"response": "Ingresa un número válido."}

    # Paso 3: Selección de sección
    if chat_sessions[user_id]["step"] == "seleccion_seccion":
        try:
            seleccion = int(message.strip()) - 1
            materia = chat_sessions[user_id]["materia"]
            id_materia = limpiar_clave_json(materia)
            materia_data = r.json().get("materias",f"$.{id_materia}")[0]
            secciones_disponibles = list(materia_data["secciones"].keys())

            if 0 <= seleccion < len(secciones_disponibles):
                seccion = secciones_disponibles[seleccion]
                chat_sessions[user_id]["step"] = "final"

                # Obtener datos de la sección seleccionada
                seccion_data = materia_data["secciones"][seccion]
                clases_texto = "\n".join([f"{dia}: {clase['horario']} - Aula: {clase['aula']}" 
                                          for dia, clase in seccion_data["clases"].items()])

                respuesta = (f"Esta es la información que tengo de la sección {seccion} de {materia_data['nombre']}:\n"
                             f"👨‍🏫 Profesor: {seccion_data['nom_prof']} {seccion_data['ape_prof']}\n"
                             f"📚 Clases:\n{clases_texto}\n\n"
                             "Si deseas consultar otra materia, no dudes en escribirme.")

                # Reiniciar el chat después de responder
                del chat_sessions[user_id]

                return {"response": respuesta}
            else:
                return {"response": "Por favor, selecciona un número válido para la sección."}
        except ValueError:
            return {"response": "Ingresa un número válido."}

    # Si algo falla, reiniciar el chat
    chat_sessions[user_id]["step"] = "inicio"
    return {"response": "Hubo un error, iniciemos de nuevo. Ingresa una palabra clave de la materia."}
