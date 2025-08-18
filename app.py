import streamlit as st
from ui_app import render_ner_ui
from chat_app import render_chat_app


# Configure the main page
st.set_page_config(
    page_title="SNOBot Platform",
    page_icon="📑",
    initial_sidebar_state="expanded"
)

# Create navigation
chat_page = st.Page(
    page=render_chat_app,
    title="Chat UI",
    icon="💬",
    default=True
)

ner_page = st.Page(
    page=render_ner_ui, 
    title="Text Annotator",
    icon="🔍"
)

# Set up navigation
nav = st.navigation([chat_page, ner_page])

# Run the selected page
nav.run()
