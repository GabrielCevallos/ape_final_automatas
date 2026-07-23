from flask import Flask, render_template, request, jsonify

from domain.classifier import detect_connectors, classify_sentence
from domain.comparator import compare_pos, compare_dependencies
from adapters import connectors as connector_loader
from adapters import spacy as spacy_adapter
from adapters import stanza as stanza_adapter

app = Flask(__name__)

COORDINATORS, SUBORDINATES = connector_loader.load_connectors("conectores.json")


@app.route("/")
def index():
    return render_template("index.html")

@app.route("/analizar", methods=["POST"])
def analizar():
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Datos inválidos"}), 400
            
        oraciones = data.get("oraciones", [])
        if not oraciones:
            return jsonify({"error": "No se proporcionaron oraciones"}), 400

        resultados = []
        for oracion in oraciones:
            texto = oracion.strip()
            if not texto:
                continue

            try:
                conectores = detect_connectors(texto, COORDINATORS, SUBORDINATES)
                tipo_oracion, num_props = classify_sentence(conectores)

                spacy_res = spacy_adapter.analyze(texto)
                stanza_res = stanza_adapter.analyze(texto, COORDINATORS, SUBORDINATES)

                precision_pos = compare_pos(spacy_res["tokens"], stanza_res["tokens"])
                precision_dep = compare_dependencies(spacy_res["tokens"], stanza_res["tokens"])

                def token_dict(t):
                    return {"text": t.text, "lemma": t.lemma, "pos": t.pos, "dep": t.dep, "head": t.head}

                resultados.append({
                    "oracion": texto,
                    "tipo_oracion": tipo_oracion,
                    "num_proposiciones": num_props,
                    "conectores": [
                        {"conector": c.word, "tipo": c.type, "categoria": c.category}
                        for c in conectores
                    ],
                    "spacy": {
                        "tokens": [token_dict(t) for t in spacy_res["tokens"]],
                        "sujetos": spacy_res["sujetos"],
                        "verbos": spacy_res["verbos"],
                        "objetos": spacy_res["objetos"],
                        "html_arbol": spacy_res["html_arbol"],
                        "tiempo": spacy_res["tiempo"],
                        "memoria": spacy_res["memoria"],
                    },
                    "stanza": {
                        "tokens": [token_dict(t) for t in stanza_res["tokens"]],
                        "sujetos": stanza_res["sujetos"],
                        "verbos": stanza_res["verbos"],
                        "objetos": stanza_res["objetos"],
                        "tiempo": stanza_res["tiempo"],
                        "memoria": stanza_res["memoria"],
                        "proposiciones": [
                            {"texto": p.text, "verbo": p.verb}
                            for p in stanza_res["proposiciones"]
                        ],
                    },
                    "comparacion": {
                        "precision_pos": precision_pos,
                        "precision_dep": precision_dep,
                    },
                })
            except Exception as e:
                print(f"Error procesando oración '{texto}': {str(e)}")
                # Devuelve un resultado parcial o continúa
                resultados.append({
                    "oracion": texto,
                    "error": str(e),
                    "tipo_oracion": "Error",
                    "num_proposiciones": 0,
                    "conectores": [],
                    "spacy": {"tokens": [], "sujetos": [], "verbos": [], "objetos": [], "html_arbol": "", "tiempo": 0, "memoria": 0},
                    "stanza": {"tokens": [], "sujetos": [], "verbos": [], "objetos": [], "tiempo": 0, "memoria": 0, "proposiciones": []},
                    "comparacion": {"precision_pos": 0, "precision_dep": 0}
                })

        return jsonify({"resultados": resultados})
    
    except Exception as e:
        print(f"Error general: {str(e)}")
        return jsonify({"error": f"Error del servidor: {str(e)}"}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)
