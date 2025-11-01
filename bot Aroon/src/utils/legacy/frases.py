import random

def obtener_frase_motivadora(path_txt: str, rendimiento: float) -> str:
    """
    Lee las frases motivadoras desde el archivo y devuelve una aleatoria según el rendimiento.
    :param path_txt: Ruta al archivo frases_motivadoras.txt
    :param rendimiento: Porcentaje de efectividad (ej: 75.0)
    :return: Una frase motivadora aleatoria según el rango de rendimiento
    """
    tipo = None
    if rendimiento >= 80:
        tipo = "ALTA"
    elif rendimiento < 60:
        tipo = "BAJA"
    else:
        return "Hoy fue un día equilibrado. Mañana seguimos aprendiendo y mejorando. 💪"

    frases = []
    capturar = False

    with open(path_txt, 'r', encoding='utf-8') as f:
        for linea in f:
            linea = linea.strip()
            if linea.startswith("[") and linea.endswith("]"):
                capturar = (linea[1:-1] == tipo)
                continue
            if capturar and linea:
                frases.append(linea)

    if frases:
        return random.choice(frases)
    else:
        return "No se encontraron frases para este tipo de rendimiento."