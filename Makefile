.PHONY: install app deploy clean

install:
	@echo "Installing dependencies..."
	uv sync --no-install-project

app:
	@echo "Running UI app..."
	uv run streamlit run app.py

deploy:
	@echo "Starting deployment process..."
	@echo "This will set up SNOBot for production on this Ubuntu server"
	@echo "Make sure you have a .env file in the current directory"
	@if [ ! -f .env ]; then \
		echo "Error: .env file not found. Please create one with OPENAI_API_KEY and ACCESS_PW"; \
		exit 1; \
	fi
	@chmod +x deploy/setup-deployment.sh deploy/install-app.sh deploy/configure-services.sh
	@echo "Step 1: Setting up deployment environment..."
	@sudo deploy/setup-deployment.sh
	@echo "Step 2: Installing application..."
	@sudo deploy/install-app.sh
	@echo "Step 3: Configuring services..."
	@sudo deploy/configure-services.sh
	@echo "Deployment complete! SNOBot should be available at http://your-server-ip"

# SNOMED CT Evaluation commands
eval-test:
	@echo "Running SNOMED CT evaluation on test set..."
	uv run python -m evals.snomed_eval --data_dir evals/data/snomed_challenge --split test --output evals/outputs/test/test_submission.csv --evaluate

eval-train:
	@echo "Running SNOMED CT evaluation on training set..."
	uv run python -m evals.snomed_eval --data_dir evals/data/snomed_challenge --split train --output evals/outputs/train/train_submission.csv --evaluate

prepare-smoke-data:
	@echo "Preparing smoke test data (default: 1 note, 6 concepts)..."
	uv run python evals/prepare_smoke_test.py

prepare-smoke-data-custom:
	@echo "Usage: make prepare-smoke-data-custom NOTES=2 CONCEPTS=10 SKIP=0 (or CONCEPTS=all)"
	@echo "Preparing smoke test data with $(NOTES) notes, $(CONCEPTS) concepts per note, skipping first $(if $(SKIP),$(SKIP),0) notes..."
	uv run python evals/prepare_smoke_test.py --notes $(NOTES) --concepts $(CONCEPTS) --skip $(if $(SKIP),$(SKIP),0)

eval-smoke:
	@echo "Running SNOMED CT smoke test..."
	uv run python -m evals.snomed_eval --data_dir evals/data/snomed_challenge --split smoke --output evals/outputs/smoke/smoke_submission.csv --evaluate



test-eval:
	@echo "Testing evaluation framework..."
	uv run python evals/test_eval.py

precompute-databases:
	@echo "Pre-computing and caching databases..."
	uv run python evals/precompute_databases.py

clean:
	@echo "Cleaning up..."
	# NB: these are also hardcoded in vec_db.py and sql_db.py
	rm -rf resources/omop_vocab/omop_vocab.duckdb
	rm -rf resources/omop_vocab/chroma_db
	rm -rf evals/outputs/
	rm -rf evals/reports/
	rm -f evals/*_submission.csv evals/evaluation_summary.json

clean-databases:
	@echo "Cleaning up cached databases..."
	rm -rf resources/omop_vocab/omop_vocab.duckdb
	rm -rf resources/omop_vocab/chroma_db
