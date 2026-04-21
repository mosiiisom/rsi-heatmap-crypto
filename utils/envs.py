import streamlit as st
import os
from dotenv import load_dotenv

load_dotenv()


def get_envs(key, default=None):
    is_bool = str(st.secrets.get(key, os.getenv(key, default))).lower() in ('true','false')
    if is_bool:
        return bool(st.secrets.get(key, os.getenv(key, default)))

    return st.secrets.get(key, os.getenv(key, default))
