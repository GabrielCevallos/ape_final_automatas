import time
import os

import stanza
import psutil

from domain.models import Token
from domain.classifier import detect_connectors
from domain.proposer import split_propositions

_nlp = None


def _get_nlp():
    global _nlp
    if _nlp is None:
        _nlp = stanza.Pipeline("es", processors="tokenize,mwt,pos,lemma,depparse", logging_level="ERROR")
    return _nlp


def _get_memory_mb():
    return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)


def analyze(text: str, coordinators: dict, subordinates: dict) -> dict:
    nlp = _get_nlp()
    start = time.time()
    mem_before = _get_memory_mb()

    doc = nlp(text)

    tokens = []
    sujetos = []
    verbos = []
    objetos = []

    for sent in doc.sentences:
        for word in sent.words:
            head_text = sent.words[word.head - 1].text if word.head > 0 else "ROOT"
            tokens.append(Token(
                text=word.text, lemma=word.lemma, pos=word.upos,
                dep=word.deprel, head=head_text,
            ))
            if word.deprel in ("nsubj", "nsubj:pass"):
                sujetos.append(word.text)
            if word.upos == "VERB":
                verbos.append(word.text)
            if word.deprel in ("obj", "dobj"):
                objetos.append(word.text)

    conectores = detect_connectors(text, coordinators, subordinates)
    proposiciones = split_propositions(text, conectores, tokens)

    mem_after = _get_memory_mb()
    elapsed = round((time.time() - start) * 1000, 2)

    return {
        "tokens": tokens,
        "sujetos": sujetos,
        "verbos": verbos,
        "objetos": objetos,
        "tiempo": elapsed,
        "memoria": round(mem_after - mem_before, 2),
        "proposiciones": proposiciones,
    }
