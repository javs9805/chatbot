from fastapi import FastAPI, Query
import requests
from util import normalizar_texto, limpiar_clave_json, split_array
from functions import Handlers
from pydantic import BaseModel
from dotenv import load_dotenv
import os
load_dotenv()

REDIS_HOST = os.getenv("url_redis")
REDIS_PORT = os.getenv("port_redis")
REDIS_DB = os.getenv("db_redis")
TOKEN = os.getenv("t_key")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

app = FastAPI()

abm = Handlers()

class TelegramUpdate(BaseModel):
    update_id: int
    message: dict
    
PAGE_SIZE = 25  # Tamaño de cada página de materias

@app.post("/resetear_chat_sessions")
async def resetChatSessions(key:str):
    if key == "lokita304":
        cs = abm.resetChatSessions()
        return {"status":200, "message":"has limpiado chat_sessions","chat_sessions":cs}


@app.post("/get_chat_sessions")
async def getChatSessions(key:str):
    if key == "lokita304":
        return abm.getChatSessions()
    return "No tenes acceso"

@app.post("/")
async def telegram_webhook(update: TelegramUpdate):
    data = update.model_dump()
    chat_id = data['message']['chat']['id']
    nombre = data['message']['from']['first_name']
    mensaje = data['message']['text']
    respuesta = chat(chat_id, mensaje, nombre)
    respuesta.update({
            "chat_id": chat_id,
    })
    requests.post(f"{BASE_URL}/sendMessage",json=respuesta)
    return {"recibido":data, "enviado":respuesta}


def chat(user_id: str, message: str, username:str):
    """
    Chatbot basado en Redis para consultar carreras, materias y secciones.
    """

    # Iniciar nueva sesión si el usuario no existe o quiere reiniciar
    print(user_id not in abm.chat_sessions)
    if user_id not in abm.chat_sessions or message.lower() in ["reiniciar", "reset"]:
        return abm.bienvenida_handler(message, user_id, username)

    if abm.chat_sessions[user_id]["step"] == "seleccion_bienvenida":
        return abm.seleccion_bienvenida_handler(message, user_id, username)

    # Paso 1: Seleccionar Carrera
    if abm.chat_sessions[user_id]["step"] == "seleccion_carrera":
        return abm.seleccion_carrera_handler(message, user_id, username)

    # Paso 2: Seleccionar Materia
    if abm.chat_sessions[user_id]["step"] == "seleccion_materia":
        return abm.seleccionar_materia_handler(message, user_id, username)

    # Paso 3: Seleccionar Sección
    if abm.chat_sessions[user_id]["step"] == "seleccion_seccion":
        return abm.seleccionar_seccion_handler(message, user_id, username)

    return {"response": "Algo salió mal. Intenta nuevamente."}
