from pydantic_ai import Agent, RunContext
from opaiui.app import AgentConfig, AppConfig, AgentState, serve, get_logger, current_deps, render_in_chat, set_status
from resources.vec_db import VecDB
from resources.sql_db import SqlDB
import streamlit as st

import dotenv
dotenv.load_dotenv(override=True)

logger = get_logger()


# streamlit can cache expensive to compute functions
@st.cache_resource
def get_vec_db() -> VecDB:
    return VecDB()

@st.cache_resource
def get_sql_db() -> SqlDB:
    return SqlDB()

sql_db = get_sql_db()
vec_db = get_vec_db()


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
        return []




app_config = AppConfig()

agent_configs = {
    "SNOBot": AgentConfig(
        agent=agent,
        greeting = "Hello! I'm SNOBot, your assistant for exploring SNOMED concepts in the OMOP common data model. You can ask me to search for concepts by name or ask questions about the vocabularies.",
    )
}
serve(app_config, agent_configs)




