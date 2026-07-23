from .models import Connector


def detect_connectors(text: str, coordinators: dict, subordinates: dict) -> list[Connector]:
    text_lower = text.lower()
    result = []
    for conector, tipo in coordinators.items():
        if conector in text_lower.split():
            result.append(Connector(word=conector, type=tipo, category="Coordinada"))
    for conector, tipo in subordinates.items():
        if conector in text_lower:
            result.append(Connector(word=conector, type=tipo, category="Subordinada"))
    return result


def classify_sentence(connectors: list[Connector]) -> tuple[str, int]:
    if not connectors:
        return "Simple", 1
    has_coord = any(c.category == "Coordinada" for c in connectors)
    has_sub = any(c.category == "Subordinada" for c in connectors)
    if has_coord and has_sub:
        tipo = "Compuesta Mixta"
    elif has_coord:
        tipo = "Compuesta Coordinada"
    else:
        tipo = "Compuesta Subordinada"
    return tipo, len(connectors) + 1
