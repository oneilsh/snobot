import streamlit as st

def init_state():
    ss = st.session_state
    ss.setdefault("input_text", "")
    ss.setdefault("results", None)       # {"payload":..., "text": str, "settings": Settings}
    ss.setdefault("entities_df", None)   # latest computed DF (source of truth)
    ss.setdefault("stale", False)        # mark current results stale on any input change
    ss.setdefault("trigger_run", False)  # compute only when Analyze sets this True

def mark_stale():
    st.session_state.stale = True

def load_example_cb():
    st.session_state.input_text = (
        "Pt with chronic kidney disease (CKD) and history of diabetes mellitus type 2. "
        "Complains of dyspnea; started on metformin 500 mg. Possible polycystic kidney disease."
    )
    mark_stale()

def analyze_cb():
    st.session_state.trigger_run = True
