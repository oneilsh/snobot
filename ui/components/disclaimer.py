"""SNOMED CT License Disclaimer Component."""

import streamlit as st


DISCLAIMER_TEXT = """
Use of SNOMED CT in this software is governed by the conditions of the following SNOMED CT Sub-license issued by [IHTSDO Affiliate Name]

1. The meaning of the terms "Affiliate", or "Data Analysis System", "Data Creation System", "Derivative", "End User", "Extension", "Member", "Non-Member Territory", "SNOMED CT" and "SNOMED CT Content" are as defined in the IHTSDO Affiliate License Agreement (see http://snomed.org/license.pdf).

2. Information about Affiliate Licensing is available at http://snomed.org/license. Individuals or organizations wishing to register as IHTSDO Affiliates can register at http://snomed.org/salsa, subject to acceptance of the Affiliate License Agreement (see http://snomed.org/license.pdf).

3. The current list of IHTSDO Member Territories can be viewed at www.ihtsdo.org/members. Countries not included in that list are "Non-Member Territories".

4. End Users, that do not hold an IHTSDO Affiliate License, may access SNOMED CT® using this software subject to acceptance of and adherence to the following sub-license limitations:
   a) The sub-licensee is only permitted to access SNOMED CT® using this software (or service) for the purpose of exploring and evaluating the terminology.
   b) The sub-licensee is not permitted the use of this software as part of a system that constitutes a SNOMED CT "Data Creation System" or "Data Analysis System", as defined in the IHTSDO Affiliate License. This means that the sub-licensee must not use this software to add or copy SNOMED CT identifiers into any type of record system, database or document.
   c) The sub-licensee is not permitted to translate or modify SNOMED CT Content or Derivatives.
   d) The sub-licensee is not permitted to distribute or share SNOMED CT Content or Derivatives.

5. IHTSDO Affiliates may use this software as part of a "Data Creation System" or "Data Analysis System" subject to the following conditions:
   a) The IHTSDO Affiliate, using this software must accept full responsibility for any reporting and fees due for use or deployment of such a system in a Non-Member Territory.
   b) The IHTSDO Affiliate must not use this software to access or interact with SNOMED CT in any way that is not permitted by the Affiliate License Agreement.
   c) In the event of termination of the Affiliate License Agreement, the use of this software will be subject to the End User limitations noted in 4.
"""


@st.dialog("SNOMED CT License Agreement", width="large")
def show_disclaimer_dialog():
    """Display the SNOMED CT license disclaimer dialog."""
    st.markdown("### Important License Information")
    
    # Display the disclaimer text in a scrollable container
    with st.container(height=400):
        st.markdown(DISCLAIMER_TEXT)
    
    st.markdown("---")
    st.markdown("**By clicking 'Accept', you acknowledge that you have read and agree to the terms above.**")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Accept", type="primary", use_container_width=True):
            st.session_state.disclaimer_accepted = True
            st.rerun()


def check_and_show_disclaimer():
    """Check if disclaimer needs to be shown and display it if necessary."""
    # Initialize disclaimer state if not present
    if "disclaimer_accepted" not in st.session_state:
        st.session_state.disclaimer_accepted = False
    
    # Show disclaimer if not yet accepted
    if not st.session_state.disclaimer_accepted:
        show_disclaimer_dialog()
        return False  # Indicates disclaimer is being shown
    
    return True  # Indicates disclaimer has been accepted