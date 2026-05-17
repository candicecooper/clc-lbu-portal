# Test version - no Groq dependency
import streamlit as st

st.set_page_config(page_title="Test - PLC", page_icon="✍️", layout="wide")

st.title("✍️ Professional Language Converter - TEST")
st.write("If you can see this, the page loads correctly.")
st.write("The issue is either:")
st.write("- Missing 'groq' in requirements.txt")
st.write("- Missing GROQ_API_KEY in deployment secrets")

st.text_area("Test input", placeholder="Type something...")
if st.button("Test button"):
    st.success("Button works!")
