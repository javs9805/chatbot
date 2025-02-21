from util import limpiar_clave_json, split_array, normalizar_texto, obtener_timestamp_py
import redis
import json
from dotenv import load_dotenv
import os
load_dotenv()

REDIS_HOST = os.getenv("url_redis")
REDIS_PORT = os.getenv("port_redis")
REDIS_DB = os.getenv("db_redis")
TOKEN = os.getenv("t_key")


class Handlers:

    chat_sessions = {}
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, decode_responses=True)
    PAGE_SIZE = 25
    opciones = ["Que es TVNF?", "Información acerca de las aulas"]
    REDIS_LOGS = "chatbot_steps"
    REDIS_JSON_CARRERAS = "por_carrera"
    msg_competencia = """
📣🔥 ¡LA BATALLA DEFINITIVA YA LLEGÓ! 🔥📣

⚔ DIEGOS vs LUCAS ⚔

Dos nombres, una sola gloria.
Los Diegos, astutos y feroces.
Los Lucas, imparables y demoledores.

💰 Las apuestas están abiertas.
🔥 Solo uno será el campeón.

🚀 ¡Elegí tu equipo y sé parte de la histórica batalla hoy a las 16hs en el Bloque A! 🚀
⚠️ Decide sabiamente ya que solo puedes votar una vez y las votaciones son hasta las 16hs. ⚠️

1) Team Diego.
2) Team Lucas.
0) Seguiré pensando.
"""

    
    def getChatSessions(self):
        return self.chat_sessions

    def resetChatSessions(self):
        a = self.chat_sessions
        self.chat_sessions.clear()
        return a

    def bienvenida_handler(self, message, user_id, username):
        self.chat_sessions[user_id] = {"step": "seleccion_bienvenida","nombre":username}
        
        # Obtener carreras desde Redis
        opciones_texto = "\n".join([f"{idx+1}) {opc}" for idx, opc in enumerate(self.opciones)])
        
        return {"text": f"Hola {username}, ¿cómo estás? Un gusto saludarte, mi nombre es TuVotcito 🗣️!\n"
                            "Como puedo ayudarte hoy?\n\n"
                            f"{opciones_texto}\n\nSelecciona una opción."}


    def seleccion_bienvenida_handler(self, message, user_id, username):
        try:
            seleccion = int(message.strip()) - 1
            if seleccion == 0:# Que es TVNF?
                self.registrar_estado("TVNF")
                del self.chat_sessions[user_id]
                return {"text":"¿Qué es 'Tu Voz, Nuestra Fuerza'? ✨📢\n\n"
                                    "'Tu Voz, Nuestra Fuerza' es más que un lema; es un sentimiento que nos une como una gran familia 🤝\\."
                                    "Creemos en la amistad, la solidaridad y el poder de cada voz para construir una comunidad universitaria más justa y equitativa\\.\n\n"
                                    "Nos impulsa el deseo de trabajar juntos, apoyarnos en los momentos difíciles y celebrar nuestros logros 🎓💪\\."
                                    "Aquí, cada opinión cuenta, porque sabemos que la verdadera fuerza nace de la unión\\.\n\n"
                                    "Alzamos la voz con respeto, integridad y liderazgo para hacer del presente y el futuro un lugar mejor para todos 🩵✨\\.\n\n"
                                    "Enterate más sobre nosotros en nuestras redes sociales:\n"
                                    "Instagram: [Accede aqui](https://www.instagram.com/tvnfpuna/)\n"
                                    "Tiktok: [Accede aqui](https://www.tiktok.com/@tvnfpuna)\n\n"
                                    "\\#TuVozNuestraFuerza \\#TuVozNosUne",
                                    "parse_mode": "MarkdownV2"
                                    }



            elif seleccion == 1:# Información acerca de las aulas
                self.chat_sessions[user_id]["step"] = "seleccion_carrera"
                carreras = self.r.json().get(self.REDIS_JSON_CARRERAS,"$")[0].keys()
                opciones_carreras = "\n".join([f"{idx+1}) {seccion}" for idx, seccion in enumerate(carreras)])
                return {"text": f"Porfavor selecciona tu carrera:\n{opciones_carreras}\n\nSelecciona una de ellas enviando el número correspondiente o presiona 0 para volver atras."}
            
            
            else:
                self.registrar_estado("seleccion_bienvenida_invalido")
                return {"text": "Selecciona una opción válida."}
        except ValueError:
            self.registrar_estado("seleccion_bienvenida_error")
            return {"text": "Ingresa un número válido."}
        
    
    def obtener_ganador_handler(self):
        votos_diegos = int(self.r.json().get("votacion","$.diego")[0])
        votos_lucas = int(self.r.json().get("votacion","$.lucas")[0])
        
        if votos_diegos > votos_lucas:
            return {"ganador": "DIEGOS", "votos": votos_diegos}
        elif votos_lucas > votos_diegos:
            return {"ganador": "LUCAS", "votos": votos_lucas}
        else:
            return {"ganador": "empate", "votos": votos_diegos}

        
    def diego_vs_lucas_handler(self, message, user_id, username):
        votacion = "votacion"
        try:
            if not self.r.exists(votacion):
                print("no existe el json, creando json")
                self.r.json().set(votacion, "$", {"diego": 0, "lucas": 0, "votantes": []})
            datos_votacion = self.r.json().get(votacion)

            # Verificar si el usuario ya votó
            if user_id in datos_votacion["votantes"]:
                print("el usuario ya ha votado")
                del self.chat_sessions[user_id]
                return {"text": f"⚠️ {username}, ya has votado y no puedes votar de nuevo."}

            # Si el mensaje es 1 -> Voto para Diego
            if message == "1":
                print("el usuario voto por diego")
                del self.chat_sessions[user_id]
                self.r.json().numincrby(votacion, "$.diego", 1)
                self.r.json().arrappend(votacion, "$.votantes", user_id)
                return {"text": f"✅ {username} has elegido ser del team Diego. ¡Gracias por tu voto! \nTe esperamos hoy en el Bloque A a las 16hs para ver quien se llevará el prestigio a casa."}

            # Si el mensaje es 2 -> Voto para Lucas
            elif message == "2":
                print("el usuario voto por lucas")
                del self.chat_sessions[user_id]
                self.r.json().numincrby(votacion, "$.lucas", 1)
                self.r.json().arrappend(votacion, "$.votantes", user_id)
                return {"text": f"✅ {username} has elegido ser del team Lucas. ¡Gracias por tu voto! \nTe esperamos hoy en el Bloque A a las 16hs para ver quien se llevará el prestigio a casa."}

            # Si el mensaje es 0 -> No hacer nada
            elif message == "0":
                print("el usuario no voto")
                del self.chat_sessions[user_id]
                return {"text": f"Lo sé, es una decisión dificil, tomate tu tiempo ya que solo puedes votar una vez."}

            else:
                return {"text": "Ingresa un número válido."}

        except ValueError:
            self.registrar_estado("seleccionar_carrera_error")
            return {"text": "Ingresa un número válido."}


    def seleccion_carrera_handler(self, message, user_id, username):
        try:
            seleccion = int(message.strip()) - 1
            carreras = list(self.r.json().get(self.REDIS_JSON_CARRERAS,f"$")[0].keys())

            if seleccion == -1:
                self.chat_sessions[user_id] = {"step": "seleccion_bienvenida"}
                opciones_texto = "\n".join([f"{idx+1}) {opc}" for idx, opc in enumerate(self.opciones)])

                return {"text": f"Hola {username}, ¿cómo estás? Un gusto saludarte, mi nombre es TuVotcito 🗣️! Como puedo ayudarte hoy?\n\n"
                    f"{opciones_texto}\n\nSelecciona una opción."}


            if 0 <= seleccion < len(carreras):
                carrera = carreras[seleccion]
                print(carrera)
                self.chat_sessions[user_id]["carrera"] = carrera
                self.chat_sessions[user_id]["step"] = "seleccion_materia"
                self.chat_sessions[user_id]["page"] = 0
                
                # Obtener materias de la carrera
                carrera_data = self.r.json().get(self.REDIS_JSON_CARRERAS,f"$.{carrera}")[0]
                materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]
                materias_paginadas = split_array(materias, self.PAGE_SIZE)
                page = self.chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])
                nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia o 0 para volver a seleccionar tu carrera."

                return {"text": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                f"{materias_texto}{nav_text}"}
            else:
                self.registrar_estado("seleccionar_carrera_invalido")
                return {"text": "Selecciona una opción válida."}
        except ValueError:
            self.registrar_estado("seleccionar_carrera_error")
            return {"text": "Ingresa un número válido."}


    def seleccionar_materia_handler(self, message, user_id, username):
        try:
            # Obtener la carrera seleccionada
            carrera = self.chat_sessions[user_id]["carrera"]
            carrera_data = self.r.json().get(self.REDIS_JSON_CARRERAS, f"$.{carrera}")[0]
            materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]

            # Dividir las materias en páginas
            materias_paginadas = split_array(materias, self.PAGE_SIZE)
            if message.strip().isnumeric():
                seleccion = int(message.strip()) - 1
                if seleccion == -1:
                    carreras = self.r.json().get(self.REDIS_JSON_CARRERAS,f"$")[0].keys()
                    carreras_texto = "\n".join([f"{idx+1}) {carrera}" for idx, carrera in enumerate(carreras)])
                    self.chat_sessions[user_id]["step"] = "seleccion_carrera"
                    return {"text": "Por favor, ingresa la carrera a la que perteneces:\n"
                                        f"{carreras_texto}\n\nSelecciona una opción."}

                if 0 <= seleccion < len(materias_paginadas[self.chat_sessions[user_id]["page"]]):
                    materia = limpiar_clave_json(materias_paginadas[self.chat_sessions[user_id]["page"]][seleccion])
                    print(f"se ha seleccionado {materia}")
                    
                    self.chat_sessions[user_id]["materia"] = materia
                    self.chat_sessions[user_id]["step"] = "seleccion_seccion"

                    # Obtener secciones de la materia
                    secciones = carrera_data["asignaturas"][materia]["secciones"].keys()
                    str_materia = carrera_data["asignaturas"][materia]["nombre"]
                    secciones_texto = "\n".join([f"{idx+1}) {seccion}" for idx, seccion in enumerate(secciones)])

                    return {"text": f"Estas son las secciones que conozco de {str_materia}:\n"
                                        f"{secciones_texto}\n\nSelecciona una opción o 0 para volver atrás."}
                else:
                    self.registrar_estado("seleccionar_materia_invalido")
                    return {"text": "Selecciona una opción válida, 0 para seleccionar carrera y 'S' o 'A' para desplazarte entre las opciones."}
            else:
                # Navegación entre páginas
                if message.strip().upper() == "S":  # Siguiente página
                    if self.chat_sessions[user_id]["page"] < len(materias_paginadas) - 1:
                        self.chat_sessions[user_id]["page"] += 1

                elif message.strip().upper() == "A":  # Página anterior
                    if self.chat_sessions[user_id]["page"] > 0:
                        self.chat_sessions[user_id]["page"] -= 1

                # Obtener las materias de la página actual
                page = self.chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])

                # Agregar indicación de navegación
                nav_text = "\n\nEscribe 'S' para Siguiente, 'A' para Anterior, o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."
                if page == 0:
                    nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."
                elif page == len(materias_paginadas) - 1:
                    nav_text = "\n\nEscribe 'A' para Anterior o un número para seleccionar una materia o 0 para seleccionar de vuelta la carrera."

                return {"text": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                    f"{materias_texto}{nav_text}"}
        except ValueError:
            self.registrar_estado("seleccionar_materia_error")
            return {"text": "Selecciona una opción válida, 0 para seleccionar carrera y 'S' o 'A' para desplazarte entre las opciones."}

        
    def seleccionar_seccion_handler(self, message, user_id, username):
        try:
            seleccion = int(message.strip()) - 1
            carrera = self.chat_sessions[user_id]["carrera"]
            materia = self.chat_sessions[user_id]["materia"]
            carrera_data = self.r.json().get(self.REDIS_JSON_CARRERAS,f"$.{carrera}")[0]
            secciones = list(carrera_data["asignaturas"][materia]["secciones"].keys())

            if seleccion == -1:
                self.chat_sessions[user_id]["step"] = "seleccion_materia"
                self.chat_sessions[user_id]["page"] = 0
                
                # Obtener materias de la carrera
                carrera_data = self.r.json().get(self.REDIS_JSON_CARRERAS,f"$.{carrera}")[0]
                materias = [carrera_data["asignaturas"][x]["nombre"] for x in carrera_data["asignaturas"]]
                materias_paginadas = split_array(materias, self.PAGE_SIZE)
                page = self.chat_sessions[user_id]["page"]
                materias_actuales = materias_paginadas[page]
                materias_texto = "\n".join([f"{idx+1}) {str_materia}" for idx, str_materia in enumerate(materias_actuales)])
                nav_text = "\n\nEscribe 'S' para Siguiente o un número para seleccionar una materia."

                return {"text": f"Selecciona la materia correspondiente a {carrera} (Página {page+1}/{len(materias_paginadas)}):\n"
                                f"{materias_texto}{nav_text}"}


            if 0 <= seleccion < len(secciones):
                seccion = secciones[seleccion]

                # Obtener datos de la sección seleccionada
                seccion_data = carrera_data["asignaturas"][materia]["secciones"][seccion]
                str_materia = carrera_data["asignaturas"][materia]["nombre"]
                print(seccion_data)
                if "clases" in seccion_data and seccion_data["clases"] != {}:
                    clases_texto = ""
                    for dia, clase in seccion_data["clases"].items():
                        if clase["horario"] != "" and clase['aula'] != "":
                            clases_texto = clases_texto + f"{dia}: {clase['horario']} - Aula: {clase['aula']}\n"
                        elif clase['horario'] != "":
                            clases_texto = clases_texto + f"{dia}: {clase['horario']} - Aula: NO DISPONIBLE\n"
                    if clases_texto != "":
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
                del self.chat_sessions[user_id]

                return {"text": respuesta}
            else:
                self.registrar_estado("seleccionar_seccion_invalido")
                return {"text": "Selecciona una opción válida o 0 para volver atrás."}
        except ValueError:
            self.registrar_estado("seleccionar_seccion_error")
            return {"text": "Ingresa un número válido."}
    
    def registrar_estado(self, step):
        self.r.json().get("logs","$")
        print("dejando log")

        # Inicializar el JSON en Redis si no existe
        if not self.r.exists(self.REDIS_LOGS):
            self.r.json().set(self.REDIS_LOGS, "$", {})  # Se crea un JSON vacío
            
        # Verificar si el step ya existe en el JSON, si no, inicializarlo en 0
        if not self.r.json().get(self.REDIS_LOGS, f"$.{step}"):
            self.r.json().set(self.REDIS_LOGS, f"$.{step}", 0)

        # Incrementar el contador en Redis JSON
        self.r.json().numincrby(self.REDIS_LOGS, f"$.{step}", 1)
        
    def obtener_estadisticas_json(self):
        """Devuelve el número de usuarios que han pasado por cada step en formato JSON."""
        return self.r.json().get(self.REDIS_LOGS)