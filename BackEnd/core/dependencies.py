import importlib
import streamlit as st
from typing import List, Tuple

REQUIRED_PACKAGES = [
    ("sklearn", "scikit-learn"),
    ("langchain", "langchain"),
    ("langchain_community", "langchain-community"),
    ("faiss", "faiss-cpu"),
    ("openpyxl", "openpyxl"),
    ("unstructured", "unstructured"),
    ("statsmodels", "statsmodels"),
    ("prophet", "prophet"),
    ("xgboost", "xgboost"),
    ("sqlparse", "sqlparse"),
    ("streamlit_autorefresh", "streamlit-autorefresh")
]

def get_missing_dependencies() -> List[str]:
    """Checks for missing packages and returns their pip install names."""
    missing = []
    for module_name, pip_name in REQUIRED_PACKAGES:
        try:
            importlib.import_module(module_name)
        except ImportError:
            missing.append(pip_name)
    return missing

def render_dependency_alerts():
    """Displays a warning in Streamlit if dependencies are missing."""
    missing = get_missing_dependencies()
    if missing:
        st.warning(f"⚠️ **Missing Dependencies Detected:** The following features may be limited: {', '.join(missing)}. \n\n Please run: `pip install {' '.join(missing)}`")