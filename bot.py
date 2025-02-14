import os
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Token del bot (coloca tu token aquí)
TOKEN = "7742611312:AAEbSADQDFUOZ3AG_4d_mi57HMYNpBpfkIA"

# Diccionario para rastrear la sesión del usuario
user_sessions = {}

async def start(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    user_sessions[chat_id] = {"step": "inicio"}
    await update.message.reply_text(
        "Hola! Soy tu asistente de clases. ¿Qué materia deseas consultar?\n"
        "1) Cálculo\n"
        "2) Física\n"
        "3) Matemática"
    )

async def handle_message(update: Update, context: CallbackContext):
    chat_id = update.message.chat_id
    message_text = update.message.text.strip()

    if chat_id not in user_sessions or message_text.lower() in ["reiniciar", "reset"]:
        user_sessions[chat_id] = {"step": "inicio"}
        await update.message.reply_text(
            "Hola! ¿Qué materia deseas consultar?\n"
            "1) Cálculo\n"
            "2) Física\n"
            "3) Matemática"
        )
        return

    # Enviar mensaje al servidor FastAPI
    api_url = f"https://cf27-2803-2a01-4-5b7-b849-1786-fa5d-f94c.ngrok-free.app/chat/?user_id={chat_id}&message={message_text}"
    response = requests.get(api_url).json()
    
    await update.message.reply_text(response["response"])

def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print("Bot iniciado...")
    app.run_polling()

if __name__ == "main":
    main()