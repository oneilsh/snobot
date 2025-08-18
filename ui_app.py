# app.py — BioNER + Resolution (modular)
import pandas as pd
import streamlit as st

from ui.models import Settings
from ui.state import init_state, mark_stale, analyze_cb
from ui.resolver import resolve_entities_api
from ui.utils import csv_text, OMOP_DOMAINS, DOMAIN_COLORS
from ui.annotated import render_annotated_component_from_concepts
from ui.examples import example_names, get_example
from agents.extract_agent import FullCodedConcept


def render_ner_ui():
    st.set_page_config(layout="wide")
    init_state()    # ---------- Sidebar ----------
    
    with st.sidebar:
        st.title("Settings")
        st.selectbox("Resolver backend", ["Default"], key="backend", on_change=mark_stale)
        st.multiselect(
            "Target Domains", OMOP_DOMAINS,
            default=["Condition", "Observation"], key="domains", on_change=mark_stale
        )

    # ---------- Main: inputs ----------
    st.markdown("#### SNOBot: SNOMED-based Biomedical Named Entity Recognition and Resolution")

    with st.expander("Input", expanded=True):
        col_in, col_actions = st.columns([3, 1])
        with col_in:
            st.text_area("Paste text or upload a file", height=240, key="input_text", on_change=mark_stale)

        with col_actions:
            up = st.file_uploader("Upload .txt/.md", type=["txt", "md"])
            if up:
                st.session_state.input_text = up.read().decode("utf-8")
                mark_stale()

        def _on_example_change():
            st.session_state.results = None
            name = st.session_state.get("example_choice")
            if name and name != "— Choose an example —":
                st.session_state.input_text = get_example(name)
                mark_stale()

        c1, c2, c3 = st.columns([1, 2, 1])
        with c1:
            st.selectbox(
                label = "Choose an example",
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
        with status_ph.status("Processing…", expanded=False) as status_widget:
            status_widget.update(label="Calling resolver…")
            settings = Settings(backend=st.session_state.backend, domains=st.session_state.domains)
            payload = resolve_entities_api(st.session_state.input_text, settings, status_widget)
            st.session_state.entities_df = payload[1]
            st.session_state.results = {"payload": payload, "text": st.session_state.input_text, "settings": settings}
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



