import httpx
from fastapi import FastAPI, Request
from pydantic import BaseModel
from dotenv import load_dotenv
import os
load_dotenv()


TOKEN = os.getenv("t_key")
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

client = httpx.AsyncClient()

app = FastAPI()


class TelegramUpdate(BaseModel):
    update_id: int
    message: dict

@app.post("/")
async def telegram_webhook(update: TelegramUpdate):
    data = update.model_dump()  # Cambiado de dict() a model_dump()
    chat_id = data['message']['chat']['id']
    text = data['message']['text']

    await client.get(f"{BASE_URL}/sendMessage?chat_id={chat_id}&text={text}")

    return update