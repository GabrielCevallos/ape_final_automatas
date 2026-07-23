.ONESHELL:

.PHONY: setup run clean

setup:
	python3 -m venv .venv
	. .venv/bin/activate && pip install -r requirements.txt
	. .venv/bin/activate && python3 -m spacy download es_core_news_sm
	. .venv/bin/activate && python3 -c "import stanza; stanza.download('es')"

run:
	. .venv/bin/activate && python3 app.py

clean:
	rm -rf .venv __pycache__ */__pycache__
