# app.py — BioNER + Resolution (modular)
import pandas as pd
import streamlit as st

from ui.models import Settings
from ui.state import init_state, mark_stale, analyze_cb
from ui.resolver import resolve_entities_api
from ui.utils import payload_to_df, csv_text, OMOP_DOMAINS, DOMAIN_COLORS
from ui.annotated import render_annotated_component_from_df_css
from ui.examples import example_names, get_example

import dotenv
dotenv.load_dotenv(override=True)

st.set_page_config(page_title="BioNER + Resolution", layout="wide")
init_state()

# ---------- Sidebar ----------
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
        df = payload_to_df(payload)

        st.session_state.entities_df = df
        st.session_state.results = {"payload": payload, "text": st.session_state.input_text, "settings": settings}
        st.session_state.stale = False
        status_widget.update(label="Done ✅", state="complete")

# ---------- Display ----------
if st.session_state.results:
    with st.expander("Results", expanded=True):
        render_annotated_component_from_df_css(
            st.session_state.results["text"],
            st.session_state.entities_df
        )

        print(df)
        display_cols = [
            "mention", "canonical_label", "id", "domain",
            "confidence", 
            "start", "end", "row_id"
        ]
        df = st.session_state.entities_df
        st.dataframe(df[display_cols] if not df.empty else df, use_container_width=True, hide_index=True)

        st.download_button(
            "Download CSV",
            csv_text(df),
            "entities.csv",
            "text/csv",
            use_container_width=False
        )



