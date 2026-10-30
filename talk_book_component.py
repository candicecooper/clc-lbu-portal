"""
talk_book_component.py
──────────────────────
Registers the Talk Book's two-way Streamlit component (used by pages/73_Talk_Book.py).

Streamlit can only declare a custom component from a normal imported module,
not from inside a page script (that raises "module is None"), so it lives here
in the repo root, next to staff_auth.py.

The component's files are in data/talk_book/ (index.html).
"""
from pathlib import Path

import streamlit.components.v1 as components

COMP_DIR = Path(__file__).resolve().parent / "data" / "talk_book"
AVAILABLE = (COMP_DIR / "index.html").exists()

talk_book = components.declare_component("clc_talk_book", path=str(COMP_DIR)) if AVAILABLE else None
