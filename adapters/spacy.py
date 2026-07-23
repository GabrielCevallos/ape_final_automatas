import time
import os

import spacy
import psutil
from spacy import displacy

from domain.models import Token

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = spacy.load("es_core_news_sm")
    return _nlp


def _get_memory_mb():
    return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)


def analyze(text: str) -> dict:
    nlp = _get_nlp()
    start = time.time()
    mem_before = _get_memory_mb()

    doc = nlp(text)

    tokens = []
    for t in doc:
        tokens.append(Token(
            text=t.text, lemma=t.lemma_, pos=t.pos_,
            dep=t.dep_, head=t.head.text,
        ))

    sujetos = [t.text for t in doc if t.dep_ in ("nsubj", "nsubj:pass")]
    verbos = [t.text for t in doc if t.pos_ == "VERB"]
    objetos = [t.text for t in doc if t.dep_ in ("dobj", "obj")]

    html_arbol = displacy.render(doc, style="dep", options={"compact": False, "jupyter": False})
    mem_after = _get_memory_mb()
    elapsed = round((time.time() - start) * 1000, 2)

    return {
        "tokens": tokens,
        "sujetos": sujetos,
        "verbos": verbos,
        "objetos": objetos,
        "html_arbol": html_arbol,
        "tiempo": elapsed,
        "memoria": round(mem_after - mem_before, 2),
    }
