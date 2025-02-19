import re
import unicodedata
import pytz
from datetime import datetime

def normalizar_texto(texto):
    """Elimina acentos y caracteres especiales del texto."""
    if isinstance(texto, str):
        texto = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('utf-8')
    return texto

def limpiar_clave_json(texto):
    """Convierte una clave en una versión válida para RedisJSON eliminando caracteres especiales."""
    if isinstance(texto, str):
        texto = normalizar_texto(texto)  # Eliminar acentos primero
        texto = re.sub(r"[^\w]", "", texto)  # Eliminar caracteres que no sean letras, números o guiones bajos
    return texto


def split_array(array, V):
    return [array[i:i + V] for i in range(0, len(array), V)]


def obtener_timestamp_py():
    tz_paraguay = pytz.timezone("America/Asuncion")
    now_paraguay = datetime.now(tz_paraguay)
    return now_paraguay


if __name__ == "__main__":
    now = obtener_timestamp_py()
    las_16 = now.replace(day=19,month=2, year=2025, hour=11, minute=31, second=0, microsecond=0)
    if now > las_16:
        print(obtener_timestamp_py())
        print("ya paso el tiempo")
    else:
        print("tienes tiempo")
        