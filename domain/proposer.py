import re

from .models import Connector, Proposition, Token


def split_propositions(
    text: str, connectors: list[Connector], tokens: list[Token]
) -> list[Proposition]:
    if not connectors:
        verbo = None
        for t in tokens:
            if t.pos in ("VERB", "AUX"):
                verbo = t.text
                break
        return [Proposition(text, verbo)]

    partes = [text.strip()]

    for c in sorted(connectors, key=lambda x: -len(x.word)):
        conector = c.word
        for i, parte in enumerate(partes):
            lower_parte = parte.lower()
            idx = lower_parte.find(conector)
            if idx == -1:
                continue

            before = parte[:idx].strip()
            after_connector = parte[idx + len(conector):].strip()

            if not before:
                words_after = after_connector.replace(".", "").replace(",", "").strip().split()
                verb_count = 0
                split_at = len(words_after)
                for wi, w in enumerate(words_after):
                    for t in tokens:
                        if t.text.lower() == w.lower() and t.pos in ("VERB", "AUX", "ADJ"):
                            verb_count += 1
                            if verb_count == 1:
                                split_at = wi + 1
                                break
                    if verb_count >= 1:
                        break

                subord = conector.capitalize() + " " + " ".join(words_after[:split_at])
                main = " ".join(words_after[split_at:])
                new_parts = []
                if subord.strip():
                    new_parts.append(subord.strip())
                if main.strip():
                    new_parts.append(main.strip())
            else:
                new_parts = [before]
                if after_connector:
                    new_parts.append(after_connector)

            partes = partes[:i] + new_parts + partes[i + 1:]
            break

    props = []
    for parte in partes:
        parte_clean = re.sub(r"[.,;:!?]", "", parte).strip().lower()
        parte_tokens = parte_clean.split()
        verbo = None
        for t in tokens:
            if t.text.lower() in parte_tokens and t.pos in ("VERB", "AUX"):
                verbo = t.text
                break
        if not verbo:
            for t in tokens:
                if t.text.lower() in parte_tokens and t.pos == "ADJ":
                    verbo = t.text + " (ADJ)"
                    break
        props.append(Proposition(parte.strip(), verbo))

    return props
