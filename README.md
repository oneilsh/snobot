# SNOBot

This work-in-progress repo implements RAG and SQL Q&A over an OMOP vocabulary. 
Included is a chatbot, and a UI for named entity recognition
(NER) and named entity normalization (NEN).

## Local Development

You'll need [uv](https://github.com/astral-sh/uv).

Add a `.env` file with `OPENAI_API_KEY=<your key>` and `ACCESS_PW=<password to use>`

Acquire OMOP vocabulary files from [https://athena.ohdsi.org](https://athena.ohdsi.org) and add them to the `resources/omop_vocab/` folder:

- `resources/omop_vocab/CONCEPT.csv`
- `resources/omop_vocab/CONCEPT_ANCESTOR.csv`
- `resources/omop_vocab/CONCEPT_CLASS.csv`
- `resources/omop_vocab/CONCEPT_RELATIONSHIP.csv`
- `resources/omop_vocab/DOMAIN.csv`
- `resources/omop_vocab/RELATIONSHIP.csv`
- `resources/omop_vocab/VOCABULARY.csv`

Use `make` to install dependencies and run the app:

```bash
$ make install
$ make app
```

The first time the app runs, it will generate embeddings for all of the vocab concepts
in `resources/omop_vocab/CONCEPT.csv`, and index an SQL database based on this and the other OMOP tables.
This takes upwards of 30 minutes; on subsequent reruns, the pre-computed databases are used, and it takes a couple
minutes to load them into RAM.

The database files can be removed with `make clean`.

## Production Deployment

For secure deployment on an Ubuntu server:

1. **Clone the repository** on your server (can be done as root):
   ```bash
   git clone <your-repo-url>
   cd snobot
   ```

2. **Create your `.env` file** in the project directory:
   ```bash
   # Example .env content:
   OPENAI_API_KEY=sk-your-openai-key-here
   # ACCESS_PW is optional, see below
   ACCESS_PW=your-secure-password
   ```

3. **Add your OMOP vocabulary files** to `resources/omop_vocab/`

*Warning*: Be sure to create `.env` and unzip your vocab files prior to `make deploy`.

4. **Deploy with one command**:
   ```bash
   make deploy
   ```

This will:
- Create a dedicated `snobot` user
- Install system dependencies (nginx, uv, etc.)
- Set up the application in `/opt/snobot`
- Move configuration to secure location (`/etc/snobot/.env`)
- Configure nginx reverse proxy with security headers
- Set up systemd service with security restrictions
- Configure firewall and logging

After deployment, SNOBot will be available at `http://your-server-ip`

### Post-Deployment Management

```bash
# Check service status
systemctl status snobot

# View application logs
tail -f /var/log/snobot/snobot.log

# Restart the application
systemctl restart snobot

# Update the application (run from project directory after git pull)
sudo deploy/install-app.sh
systemctl restart snobot
```


## Access password

The application implements a SNOMED disclaimer and, if an `ACCESS_PW` environment variable or `.env` entry exists, 
requires either an OpenAI API key or the access password. If an access password is set, entering it generates
a sharable password-containing URL.

## Known bugs

The chat interface appears incompatible with `opaiui`'s chat sharing feature.