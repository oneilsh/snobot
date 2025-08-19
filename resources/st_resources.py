from resources.vec_db import VecDB
from resources.sql_db import SqlDB
import streamlit as st
from opaiui.app import get_logger


@st.cache_resource
def get_vec_db() -> VecDB:
    return VecDB()

@st.cache_resource
def get_sql_db() -> SqlDB:
    return SqlDB()


sql_db = get_sql_db()
vec_db = get_vec_db()


logger = get_logger()
