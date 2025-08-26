"""SNOMED CT License Disclaimer Component."""

import streamlit as st
import os
import dotenv
import base64
from urllib.parse import urlencode

# Load environment variables
dotenv.load_dotenv(override=True)


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


def _encode_password_for_url(password):
    """Encode password for URL parameter (Base64)."""
    if not password:
        return ""
    return base64.b64encode(password.encode('utf-8')).decode('utf-8')


def _decode_password_from_url(encoded_password):
    """Decode password from URL parameter (Base64)."""
    if not encoded_password:
        return ""
    try:
        return base64.b64decode(encoded_password.encode('utf-8')).decode('utf-8')
    except Exception:
        return ""


def _get_url_password():
    """Get password from URL parameters if present."""
    query_params = st.query_params
    encoded_pw = query_params.get("pw", "")
    return _decode_password_from_url(encoded_pw)


def _validate_url_password(password):
    """Validate if the URL password is correct."""
    access_pw = os.getenv("ACCESS_PW")
    return access_pw and password.strip() == access_pw.strip()


def _generate_shareable_url(password):
    """Generate a shareable URL with encoded password."""
    if not password:
        return ""
    
    encoded_pw = _encode_password_for_url(password)
    base_url = st.get_option("server.baseUrlPath") or ""
    
    # Get current URL without query params
    current_url = f"http://localhost:8501{base_url}"
    
    # Add encoded password parameter
    params = {"pw": encoded_pw}
    return f"{current_url}?{urlencode(params)}"


@st.dialog("SNOMED CT License Agreement", width="large")
def show_disclaimer_dialog():
    """Display the SNOMED CT license disclaimer dialog with authentication."""
    st.markdown("### Important License Information")
    
    # Display the disclaimer text in a scrollable container
    with st.container(height=300):
        st.markdown(DISCLAIMER_TEXT)
    
    # Check if ACCESS_PW environment variable is available
    access_pw_available = os.getenv("ACCESS_PW") is not None
    
    # Get password from URL if present and validate it
    url_password = _get_url_password()
    url_password_valid = url_password and _validate_url_password(url_password)
    
    # Initialize variables
    password = None
    api_key_input = None
    
    # Only show authentication section if ACCESS_PW is available
    if access_pw_available:
        if url_password_valid:
            # URL password is valid - skip password entry, make API key optional
            st.markdown("### Authentication")
            
            st.markdown("Using password from URL.")

            password = url_password
            api_key_input = st.text_input("OpenAI API Key (optional, leave blank to use default):", type="password", key="api_key_input")
        else:
            # No valid URL password - show full authentication options
            st.markdown("### Authentication Required")
            st.markdown("**Please provide either an access password or your own OpenAI API key:**")
            
            # Authentication form
            auth_method = st.radio(
                "Choose authentication method:",
                ["Use Access Password", "Provide OpenAI API Key"],
                key="auth_method"
            )
            
            if auth_method == "Use Access Password":
                # Auto-fill password from URL if available (but invalid)
                password = st.text_input(
                    "Access Password:", 
                    type="password", 
                    key="access_password",
                    value=url_password
                )
                api_key_input = None
                
                # Automatically update URL with encoded password for easy sharing
                if password and password != url_password:
                    # Update the URL with the encoded password
                    encoded_pw = _encode_password_for_url(password)
                    st.query_params["pw"] = encoded_pw
            else:
                api_key_input = st.text_input("OpenAI API Key:", type="password", key="api_key_input")
                password = None
    
    st.markdown("---")
    st.markdown("**By clicking 'Accept', you acknowledge that you have read and agree to the terms above.**")
    
    col1, col2, col3 = st.columns([1, 1, 1])
    with col2:
        if st.button("Accept", type="primary", use_container_width=True):
            # Validate authentication
            if _validate_authentication(password, api_key_input, url_password_valid, access_pw_available):
                st.session_state.disclaimer_accepted = True
                # Store the authentication method and key info
                if api_key_input:
                    st.session_state.using_custom_api_key = True
                    st.session_state.api_key_preview = api_key_input[:12] + "..."
                    # Override the environment variable for this session
                    os.environ["OPENAI_API_KEY"] = api_key_input
                else:
                    st.session_state.using_custom_api_key = False
                    st.session_state.api_key_preview = None
                st.rerun()
            else:
                st.error("Invalid password or API key. Please try again.")


def _validate_authentication(password, api_key, url_password_valid=False, access_pw_available=True):
    """Validate the provided password or API key."""
    access_pw = os.getenv("ACCESS_PW")
    default_api_key = os.getenv("OPENAI_API_KEY")
    
    # If no ACCESS_PW is available, authentication is not required
    if not access_pw_available:
        return True
    
    # If URL password is valid, we only need to validate API key if provided
    if url_password_valid:
        if api_key:
            # API key is optional, but if provided, validate it
            if api_key.startswith("sk-") and len(api_key) > 20:
                return True
            else:
                st.error("❌ Invalid API key format. Must start with 'sk-' and be at least 20 characters.")
                return False
        else:
            # No API key provided, but URL password is valid - that's fine
            return True
    
    # Standard validation for manual entry
    if password:
        if access_pw is None:
            st.error("❌ ACCESS_PW environment variable not found. Please check your .env file.")
            return False
        
        # Strip whitespace and compare
        password_clean = password.strip()
        access_pw_clean = access_pw.strip()
        
        if password_clean == access_pw_clean:
            return True
        else:
            st.error(f"❌ Password mismatch.")
            return False
            
    elif api_key:
        # Basic validation for API key format (starts with sk- and reasonable length)
        if api_key.startswith("sk-") and len(api_key) > 20:
            return True
        else:
            st.error("❌ Invalid API key format. Must start with 'sk-' and be at least 20 characters.")
            return False
    
    st.error("❌ Please provide either a password or API key.")
    return False


def show_api_key_status():
    """Show API key status in the sidebar."""
    if st.session_state.get("disclaimer_accepted", False):
        st.sidebar.markdown("### API Key Status")
        
        if st.session_state.get("using_custom_api_key", False):
            st.sidebar.success("🔑 Using Custom API Key")
            if st.session_state.get("api_key_preview"):
                st.sidebar.caption(f"Key: {st.session_state.api_key_preview}")
        else:
            st.sidebar.info("Using Default API Key")
            default_key = os.getenv("OPENAI_API_KEY")
            if not default_key:
                st.sidebar.warning("⚠️ No default key found")


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