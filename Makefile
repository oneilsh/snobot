.PHONY: install app

install:
	@echo "Installing dependencies..."
	uv sync --no-install-project

app:
	@echo "Running UI app..."
	uv run streamlit run app.py

clean:
	@echo "Cleaning up..."
	# NB: these are also hardcoded in vec_db.py and sql_db.py
	rm -rf resources/omop_vocab/omop_vocab.duckdb
	rm -rf resources/omop_vocab/embeddings.csv
	rm -rf resources/omop_vocab/faiss.index
