from .models import Token


def _build_map(tokens: list[Token], attr: str) -> dict[str, str]:
    punct = set(".,;:!?")
    result = {}
    for t in tokens:
        if t.text in punct:
            continue
        result[t.text.lower()] = getattr(t, attr)
    return result


def compare_pos(tokens_a: list[Token], tokens_b: list[Token]) -> float:
    map_a = _build_map(tokens_a, "pos")
    map_b = _build_map(tokens_b, "pos")
    coinciden = sum(1 for k in map_a if k in map_b and map_a[k] == map_b[k])
    total = sum(1 for k in map_a if k in map_b)
    return round((coinciden / total * 100) if total > 0 else 0, 1)


def compare_dependencies(tokens_a: list[Token], tokens_b: list[Token]) -> float:
    map_a = _build_map(tokens_a, "dep")
    map_b = _build_map(tokens_b, "dep")
    coinciden = sum(1 for k in map_a if k in map_b and map_a[k] == map_b[k])
    total = sum(1 for k in map_a if k in map_b)
    return round((coinciden / total * 100) if total > 0 else 0, 1)
