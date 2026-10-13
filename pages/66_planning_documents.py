"""Planning Documents - staff downloads for Individual Student Plans and Units of Work Planning (JP / PY / SY).
Place in the same folder as your other portal pages. Word files live in data/planning_documents/."""
import os
import streamlit as st

st.set_page_config(page_title="Planning Documents", page_icon="📄", layout="wide")

# Staff-level password gate (shared module). If the helper has a different function name, adjust here.
try:
    import staff_auth
    for _fn in ("require_staff_auth", "require_staff", "check_staff_auth", "staff_gate"):
        if hasattr(staff_auth, _fn):
            getattr(staff_auth, _fn)()
            break
except Exception:
    pass

DOC_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "planning_documents")
MIME = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

PROGRAMS = [
    ("JP", "Junior Primary", "Reception to Year 2", "#44546A"),
    ("PY", "Primary Years", "Years 3 to 6", "#6B4226"),
    ("SY", "Senior Years", "Years 7 to 10", "#2F4858"),
]
DOCS = [
    ("Units_of_Work_Planning", "Units of Work Planning",
     "Plan Child Protection Curriculum, AC General Capabilities, Teaching for Transfer, A 5 is Against the Law and Literacy Block units."),
    ("Individual_Student_Plan", "Individual Student Plan",
     "Document literacy, numeracy and curriculum areas for each student, with modifications, evidence and SMARTAR links."),
]

st.title("Planning Documents")
st.write("Download a blank copy of the planning documents to complete in Word. Save a copy for each unit or student.")

for code, name, years, colour in PROGRAMS:
    st.markdown(f"<h3 style='color:{colour};margin-bottom:0'>{name}</h3><div style='color:#666'>{years}</div>",
                unsafe_allow_html=True)
    cols = st.columns(len(DOCS))
    for col, (suffix, label, desc) in zip(cols, DOCS):
        fname = f"CLC-LBU_{code}_{suffix}.docx"
        path = os.path.join(DOC_DIR, fname)
        with col:
            with st.container(border=True):
                st.markdown(f"**{label}**")
                st.caption(desc)
                if os.path.exists(path):
                    with open(path, "rb") as f:
                        st.download_button("Download Word file", f.read(), file_name=fname,
                                           mime=MIME, key=f"dl_{code}_{suffix}")
                else:
                    st.warning("File not uploaded yet.")
    st.divider()
