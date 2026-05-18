"""Inferencia del uso de un recinto desde su nombre de layer o texto.

Las claves reconocen variantes en español chileno e inglés.
Sirve para que el siguiente módulo (CARGAS RIC) asigne potencia mínima
por m² según el pliego correspondiente al uso."""
import re
import unicodedata
from typing import Literal


PATRONES = [
    # (regex case-insensitive, uso normalizado)
    (r"living|estar|salon", "living"),
    (r"comedor|dining", "comedor"),
    (r"cocina|kitchen", "cocina"),
    (r"dormit|pieza|bedroom|recamara|alcoba", "dormitorio"),
    (r"bano|bath|wc|toilet|aseo", "bano"),
    (r"oficina|study|escritorio|office", "oficina"),
    (r"lavander|laundry|logia", "lavanderia"),
    (r"bodega|storage|despensa", "bodega"),
    (r"hall|recibidor|entry|foyer", "hall"),
    (r"pasillo|corredor|hallway|circulac", "pasillo"),
    (r"terraza|balcon|patio|exterior|jardin", "exterior"),
    (r"comun|amenit|salon_uso", "comun"),
]


def _normaliza(texto: str) -> str:
    """Quita tildes y pasa a minúsculas para hacer match robusto."""
    nfkd = unicodedata.normalize("NFKD", texto)
    sin_tildes = "".join(c for c in nfkd if not unicodedata.combining(c))
    return sin_tildes.lower().strip()


def inferir_uso(texto: str) -> str:
    """Devuelve el uso normalizado para un texto/nombre de layer dado."""
    if not texto:
        return "desconocido"
    n = _normaliza(texto)
    for patron, uso in PATRONES:
        if re.search(patron, n):
            return uso
    return "desconocido"
