import streamlit as st
from ui.pages.annotator import render_ner_ui
from ui.pages.chat import render_chat_app
from ui.components.disclaimer import check_and_show_disclaimer, show_api_key_status


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
    # Show API key status in sidebar
    show_api_key_status()
    
    # Create navigation
    ner_page = st.Page(
        page=render_ner_ui, 
        title="Text Annotator",
        icon="🔍"
    )

    chat_page = st.Page(
        page=render_chat_app,
        title="Chat UI",
        icon="💬",
        default=True
    )

    # Set up navigation
    nav = st.navigation([ner_page, chat_page])

    # Run the selected page
    nav.run()
else:
    # Show a loading message while disclaimer is being displayed
    st.info("Please accept the license agreement and provide authentication to continue.")
    
    # Add button to re-show the disclaimer dialog
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Display Agreement", type="primary", use_container_width=True):
            # Force re-show the disclaimer by calling it directly
            from ui.components.disclaimer import show_disclaimer_dialog
            show_disclaimer_dialog()
