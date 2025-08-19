from pydantic_ai import Agent, RunContext
from opaiui.app import get_logger
from resources.st_resources import sql_db, vec_db, logger



agent = Agent("gpt-4.1", system_prompt="""
You are SNOBot, an AI assistant designed to help users identify
and explore the SNOMED subset of the OMOP common data model metadata. 
Whenever possible, provide detailed information, including concept IDs, names, and standard information.
Use your knowledge of SNOMED and the OMOP common data model to assist users in their queries.
              """)

@agent.tool
def vec_search(ctx: RunContext, text: str, top_k: int = 5):
    """Search SNOMED concepts using vector embeddings."""
    try:
        results = vec_db.query(text, top_k)
        return results
    except Exception as e:
        logger.error(f"Error in vector search: {e}")
        return []

@agent.tool
def sql_query(ctx: RunContext, query: str):
    """Run a SQL query against the built-in OMOP database. Available tables include:
    - concept
    - concept_ancestor
    - concept_class
    - concept_relationship
    - domain
    - relationship
    - vocabulary
    """
    try:
        results = sql_db.run_query(query)
        return results
    except Exception as e:
        logger.error(f"Error in SQL query: {e}")
        return f"Error in SQL query: {e}"


