# SNOBot

This work-in-progress repo implements RAG and SQL Q&A over an OMOP vocabulary. 
Included is a chatbot, and a UI for named entity recognition
(NER) and named entity normalization (NEN).

## Installation & Use

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


Use `make` to install dependencies and run either the chat or UI app. 

```bash
$ make install
$ make app
```

The first time the `chat-app` runs, it will generate embeddings for all of the vocab concepts
in `resources/omop_vocab/CONCEPT.csv`, and index an SQL database based on this and the other OMOP tables.
This takes upwards of 30 minutes; on subsequent reruns, the pre-computed databases are used, and it takes a couple
minutes to load them into RAM.

The database files can be remove with `make clean`.

## Access password

The most recent release implements a SNOMED disclaimer, and requires either an OpenAI API key, 
or an access password defined in `.env`. A pre-filled URL is generated for direct access sharing.

## Known bugs

The chat interface appears incompatible with `opaiui`'s chat sharing feature.