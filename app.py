from flask import Flask, render_template, request, jsonify
import spacy
import stanza
import time
import re
import json
import psutil
import os
from spacy import displacy

app = Flask(__name__)

with open(os.path.join(os.path.dirname(__file__), "conectores.json"), "r", encoding="utf-8") as f:
    CONECTORES = json.load(f)

CONNECTORS_COORDINADOS = CONECTORES["coordinadas"]
CONNECTORS_SUBORDINADOS = CONECTORES["subordinadas"]

nlp_spacy = spacy.load("es_core_news_sm")
nlp_stanza = stanza.Pipeline("es", processors="tokenize,mwt,pos,lemma,depparse", logging_level="ERROR")


def get_memory_mb():
    return round(psutil.Process(os.getpid()).memory_info().rss / 1024 / 1024, 2)


def detectar_conectores(texto):
    conectores = []
    texto_lower = texto.lower()
    for conector, tipo in CONNECTORS_COORDINADOS.items():
        if conector in texto_lower.split():
            conectores.append({"conector": conector, "tipo": tipo, "categoria": "Coordinada"})
    for conector, tipo in CONNECTORS_SUBORDINADOS.items():
        if conector in texto_lower:
            conectores.append({"conector": conector, "tipo": tipo, "categoria": "Subordinada"})
    return conectores


def clasificar_oracion(conectores):
    if not conectores:
        return "Simple", 1
    tiene_coord = any(c["categoria"] == "Coordinada" for c in conectores)
    tiene_subord = any(c["categoria"] == "Subordinada" for c in conectores)
    if tiene_coord and tiene_subord:
        tipo = "Compuesta Mixta"
    elif tiene_coord:
        tipo = "Compuesta Coordinada"
    else:
        tipo = "Compuesta Subordinada"
    return tipo, len(conectores) + 1


def separar_proposiciones_stanza(doc, texto, conectores):
    all_words = []
    for sent in doc.sentences:
        for w in sent.words:
            all_words.append(w)

    if not conectores:
        verbo = None
        for w in all_words:
            if w.upos in ("VERB", "AUX"):
                verbo = w.text
                break
        return [{"texto": texto, "verbo": verbo}]

    texto_lower = texto.lower().strip()
    partes = [texto.strip()]

    for c in sorted(conectores, key=lambda x: -len(x["conector"])):
        conector = c["conector"]
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
                    for aw in all_words:
                        if aw.text.lower() == w.lower() and aw.upos in ("VERB", "AUX", "ADJ"):
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

            partes = partes[:i] + new_parts + partes[i+1:]
            break

    props = []
    for parte in partes:
        parte_clean = re.sub(r'[.,;:!?]', '', parte).strip().lower()
        parte_tokens = parte_clean.split()
        verbo = None
        for w in all_words:
            if w.text.lower() in parte_tokens and w.upos in ("VERB", "AUX"):
                verbo = w.text
                break
        if not verbo:
            for w in all_words:
                if w.text.lower() in parte_tokens and w.upos == "ADJ":
                    verbo = w.text + " (ADJ)"
                    break
        props.append({"texto": parte.strip(), "verbo": verbo})

    return props


def analizar_spacy(texto):
    start = time.time()
    mem_before = get_memory_mb()
    doc = nlp_spacy(texto)
    tokens = []
    for t in doc:
        tokens.append({
            "text": t.text, "lemma": t.lemma_, "pos": t.pos_,
            "dep": t.dep_, "head": t.head.text,
        })
    sujetos = [t.text for t in doc if t.dep_ in ("nsubj", "nsubj:pass")]
    verbos = [t.text for t in doc if t.pos_ == "VERB"]
    objetos = [t.text for t in doc if t.dep_ in ("dobj", "obj")]
    html_arbol = displacy.render(doc, style="dep", options={"compact": False, "jupyter": False})
    mem_after = get_memory_mb()
    elapsed = round((time.time() - start) * 1000, 2)
    return {
        "tokens": tokens, "sujetos": sujetos, "verbos": verbos,
        "objetos": objetos, "html_arbol": html_arbol, "tiempo": elapsed,
        "memoria": round(mem_after - mem_before, 2),
    }


def analizar_stanza(texto):
    start = time.time()
    mem_before = get_memory_mb()
    doc = nlp_stanza(texto)
    tokens = []
    sujetos = []
    verbos = []
    objetos = []
    for sent in doc.sentences:
        for word in sent.words:
            head_text = sent.words[word.head - 1].text if word.head > 0 else "ROOT"
            tokens.append({
                "text": word.text, "lemma": word.lemma, "pos": word.upos,
                "dep": word.deprel, "head": head_text,
            })
            if word.deprel in ("nsubj", "nsubj:pass"):
                sujetos.append(word.text)
            if word.upos == "VERB":
                verbos.append(word.text)
            if word.deprel in ("obj", "dobj"):
                objetos.append(word.text)
    props = separar_proposiciones_stanza(doc, texto, detectar_conectores(texto))
    mem_after = get_memory_mb()
    elapsed = round((time.time() - start) * 1000, 2)
    return {
        "tokens": tokens, "sujetos": sujetos, "verbos": verbos,
        "objetos": objetos, "tiempo": elapsed,
        "memoria": round(mem_after - mem_before, 2),
        "proposiciones": props,
    }


def comparar_pos(spacy_tokens, stanza_tokens):
    spacy_map = {t["text"].lower(): t["pos"] for t in spacy_tokens if t["text"] not in ".,;:!?"}
    stanza_map = {t["text"].lower(): t["pos"] for t in stanza_tokens if t["text"] not in ".,;:!?"}
    coinciden = 0
    total = 0
    for key in spacy_map:
        if key in stanza_map:
            total += 1
            if spacy_map[key] == stanza_map[key]:
                coinciden += 1
    return round((coinciden / total * 100) if total > 0 else 0, 1)


def comparar_dependencias(spacy_tokens, stanza_tokens):
    spacy_map = {t["text"].lower(): t["dep"] for t in spacy_tokens if t["text"] not in ".,;:!?"}
    stanza_map = {t["text"].lower(): t["dep"] for t in stanza_tokens if t["text"] not in ".,;:!?"}
    coinciden = 0
    total = 0
    for key in spacy_map:
        if key in stanza_map:
            total += 1
            if spacy_map[key] == stanza_map[key]:
                coinciden += 1
    return round((coinciden / total * 100) if total > 0 else 0, 1)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/analizar", methods=["POST"])
def analizar():
    data = request.get_json()
    oraciones = data.get("oraciones", [])
    if not oraciones:
        return jsonify({"error": "No se proporcionaron oraciones"}), 400

    resultados = []
    for oracion in oraciones:
        texto = oracion.strip()
        if not texto:
            continue

        conectores = detectar_conectores(texto)
        tipo_oracion, num_props = clasificar_oracion(conectores)

        spacy_res = analizar_spacy(texto)
        stanza_res = analizar_stanza(texto)

        precision_pos = comparar_pos(spacy_res["tokens"], stanza_res["tokens"])
        precision_dep = comparar_dependencias(spacy_res["tokens"], stanza_res["tokens"])

        resultados.append({
            "oracion": texto,
            "tipo_oracion": tipo_oracion,
            "num_proposiciones": num_props,
            "conectores": conectores,
            "spacy": spacy_res,
            "stanza": stanza_res,
            "comparacion": {
                "precision_pos": precision_pos,
                "precision_dep": precision_dep,
            },
        })

    return jsonify({"resultados": resultados})


if __name__ == "__main__":
    app.run(debug=True, port=5000)
