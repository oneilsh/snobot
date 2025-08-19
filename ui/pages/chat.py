"""Chat interface page for SNOBot."""

import streamlit as st
import dotenv
from opaiui.app import AgentConfig, AppConfig, serve
from agents.chat_agent import agent

dotenv.load_dotenv(override=True)


def render_chat_app():
    """Render the chat application interface."""
    st.set_page_config(layout="centered")
    
    app_config = AppConfig()

    agent_configs = {
        "SNOBot": AgentConfig(
            agent=agent,
            greeting="Hello! I'm SNOBot, your assistant for exploring SNOMED concepts in the OMOP common data model. You can ask me to search for concepts by name or ask questions about the vocabularies.",
        )
    }
    serve(app_config, agent_configs)
