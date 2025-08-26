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

clean:
	@echo "Cleaning up..."
	# NB: these are also hardcoded in vec_db.py and sql_db.py
	rm -rf resources/omop_vocab/omop_vocab.duckdb
	rm -rf resources/omop_vocab/chroma_db
