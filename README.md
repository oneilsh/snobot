# SNOBot

This work-in-progress repo implements RAG and SQL Q&A over an OMOP vocabulary. 
Included is a chatbot, and a (still being scaffolded) UI for named entity recognition
(NER) and named entity normalization (NEN). (Maybe this will be renamed `txt2omop` or something.

## Installation & Use

You'll need [uv](https://github.com/astral-sh/uv).

Add a `.env` file with `OPENAI_API_KEY=<your key>`

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
$ make chat-app # access on localhost:8051
$ make ui-app   # access on localhost:8051
```

The first time the `chat-app` runs, it will generate embeddings for all of the vocab concepts
in `resources/omop_vocab/CONCEPT.csv`, and index an SQL database based on this and the other OMOP tables.
This takes upwards of 30 minutes; on subsequent reruns, the pre-computed databases are used, and it takes a couple
minutes to load them into RAM. The current embedding index is in upwards of 14G in memory for SNOMED
alone, future iterations will likely use an on-disk vector db.

The database files can be remove with `make clean`. (The UI scaffold
currently does not use either DB.)


