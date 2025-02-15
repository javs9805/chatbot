import re
import unicodedata


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
