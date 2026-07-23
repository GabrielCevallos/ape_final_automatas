import json


def load_connectors(path: str) -> tuple[dict, dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data["coordinadas"], data["subordinadas"]
