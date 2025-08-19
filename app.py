import streamlit as st
from ui.pages.annotator import render_ner_ui
from ui.pages.chat import render_chat_app
from ui.components.disclaimer import check_and_show_disclaimer


# Configure the main page
st.set_page_config(
    page_title="SNOBot Platform",
    page_icon="📑",
    initial_sidebar_state="expanded"
)

# Check and show disclaimer if needed
disclaimer_accepted = check_and_show_disclaimer()

# Only show the app if disclaimer has been accepted
if disclaimer_accepted:
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
    nav = st.navigation([ner_page, chat_page])

    # Run the selected page
    nav.run()
else:
    # Show a loading message while disclaimer is being displayed
    st.info("Please accept the license agreement to continue.")
