"""Text annotation and NER interface page for SNOBot."""

import pandas as pd
import streamlit as st

from models import Settings, FullCodedConcept
from ui.state import init_state, mark_stale, analyze_cb
from ui.resolver import resolve_entities_api
from ui.utils import csv_text, OMOP_DOMAINS, DOMAIN_COLORS
from ui.components.annotated import render_annotated_component_from_concepts
from ui.examples import example_names, get_example

# Text truncation settings
MAX_TEXT_LENGTH = 4000


def _truncate_text_with_warning(text, source="input"):
    """Truncate text to MAX_TEXT_LENGTH and show toast warning if needed."""
    if len(text) > MAX_TEXT_LENGTH:
        truncated_text = text[:MAX_TEXT_LENGTH]
        st.toast(f"⚠️ Text from {source} was truncated to {MAX_TEXT_LENGTH:,} characters (was {len(text):,} characters)", icon="⚠️")
        return truncated_text
    return text


def _get_truncated_input_text():
    """Get input text with truncation applied if needed."""
    input_text = st.session_state.get("input_text", "")
    if len(input_text) > MAX_TEXT_LENGTH:
        truncated_text = input_text[:MAX_TEXT_LENGTH]
        st.toast(f"⚠️ Input text was truncated to {MAX_TEXT_LENGTH:,} characters (was {len(input_text):,} characters)", icon="⚠️")
        return truncated_text
    return input_text


def _handle_file_upload():
    """Handle file upload with truncation."""
    up = st.session_state.get("file_uploader")
    if up:
        uploaded_text = up.read().decode("utf-8")
        truncated_text = _truncate_text_with_warning(uploaded_text, "uploaded file")
        # Store in a separate key to avoid widget modification issues
        st.session_state.uploaded_text = truncated_text
        st.session_state.use_uploaded_text = True
        mark_stale()


def render_ner_ui():
    """Render the Named Entity Recognition and annotation interface."""
    st.set_page_config(layout="wide")
    init_state()
    
    # ---------- Sidebar ----------
    with st.sidebar:
        # resolver currently unused
        # st.title("Settings")
        # st.selectbox("Resolver backend", ["Default"], key="backend", on_change=mark_stale)
        # target domains currently unused
        # st.multiselect(
        #     "Target Domains", OMOP_DOMAINS,
        #     default=["Condition", "Observation"], key="domains", on_change=mark_stale
        # )
        st.session_state.domains = ["Condition", "Observation"]
        st.session_state.backend = "Default"

    # ---------- Main: inputs ----------
    st.markdown("#### SNOBot: SNOMED-based Biomedical Named Entity Recognition and Resolution")

    with st.expander("Input", expanded=True):
        col_in, col_actions = st.columns([3, 1])
        with col_in:
            # Use uploaded text if available, otherwise use manual input
            text_value = ""
            if st.session_state.get("use_uploaded_text", False):
                text_value = st.session_state.get("uploaded_text", "")
                # Clear the flag after using it
                st.session_state.use_uploaded_text = False
            
            st.text_area("Paste text or upload a file", height=240, key="input_text", 
                        value=text_value, on_change=mark_stale)

        with col_actions:
            up = st.file_uploader("Upload .txt/.md", type=["txt", "md", "csv", "tsv"], 
                                key="file_uploader", on_change=_handle_file_upload)

        def _on_example_change():
            st.session_state.results = None
            name = st.session_state.get("example_choice")
            if name and name != "— Choose an example —":
                st.session_state.input_text = get_example(name)
                mark_stale()

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.selectbox(
                label="Choose an example",
                options=["— Load example —", *example_names()],
                key="example_choice",
                on_change=_on_example_change,
                label_visibility="collapsed"
            )
        with c3:
            st.button("Analyze", type="primary", use_container_width=True, on_click=analyze_cb)

    status_ph = st.empty()

    # ---------- Compute only on Analyze ----------
    if st.session_state.trigger_run and st.session_state.input_text.strip():
        st.session_state.trigger_run = False
        
        # Get truncated input text (will show toast if truncation occurs)
        input_text = _get_truncated_input_text()
        
        with status_ph.status("Processing…", expanded=False) as status_widget:
            status_widget.update(label="Calling resolver…")
            settings = Settings(backend=st.session_state.backend, domains=st.session_state.domains)
            payload = resolve_entities_api(input_text, settings, status_widget)
            st.session_state.entities_df = payload[1]
            st.session_state.results = {"payload": payload, "text": input_text, "settings": settings}
            st.session_state.stale = False
            status_widget.update(label="Done ✅", state="complete")

    # ---------- Display ----------
    if st.session_state.results:
        with st.expander("Results", expanded=True):
            # Convert DataFrame back to FullCodedConcept objects
            coded_concepts = []
            if not st.session_state.entities_df.empty:
                for _, row in st.session_state.entities_df.iterrows():
                    coded_concepts.append(FullCodedConcept(
                        mention_str=row.get('mention_str', ''),
                        concept_id=str(row.get('concept_id', '')),
                        concept_name=row.get('concept_name', ''),
                        domain_id=row.get('domain_id', 'Other'),
                        vocabulary_id=row.get('vocabulary_id', ''),
                        concept_code=row.get('concept_code', ''),
                        standard=row.get('standard', False),
                        negated=row.get('negated', False)
                    ))
            
            render_annotated_component_from_concepts(
                st.session_state.results["text"],
                coded_concepts
            )

            df = st.session_state.entities_df
            st.dataframe(df if not df.empty else df, use_container_width=True, hide_index=True)

            st.download_button(
                "Download CSV",
                csv_text(df),
                "entities.csv",
                "text/csv",
                use_container_width=False
            )
