"""
Transition Report Builder — CLC Learning and Behaviour Unit

Students are chosen from the Student Register by INITIALS only (the same code
every portal tool uses). Two sections pull live data:

  • Regulation Profile  ← Window of Tolerance Builder (wot_builder_reports,
                           students/register Supabase project)
  • SMARTAR Goals       ← SMARTAR Goal Builder (smartar_students / smartar_goals /
                           smartar_tracking, behaviour Supabase project) —
                           active AND archived goals, with the Builder's own
                           "Distribution" pie chart for each goal

A full name can be typed for the printout only; it is never saved. The copy
filed to the Document Archive always uses initials.
"""
import os
import re
import base64
import uuid
import json
import statistics
from io import BytesIO
from datetime import date, datetime, timedelta
from collections import defaultdict

import streamlit as st
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from supabase import create_client

# ── Document Archive integration (fails soft if unavailable) ─────────────────
try:
    from archive_utils import archive_document
    ARCHIVE_AVAILABLE = True
except Exception:
    ARCHIVE_AVAILABLE = False

    def archive_document(**_k):
        return None

st.set_page_config(page_title="Transition Report Builder", layout="wide", page_icon="📄",
                   initial_sidebar_state="expanded")


# ══════════════════════════════════════════════════════════════════════════════
# CONNECTIONS
# ══════════════════════════════════════════════════════════════════════════════
def _secret(*paths, default=None):
    """First secret found. Each path is 'KEY' or 'section.key'. Render env vars
    are checked first, then Streamlit secrets (same order as other portal tools)."""
    for p in paths:
        if "." not in p and os.environ.get(p):
            return os.environ[p]
    for p in paths:
        try:
            node = st.secrets
            for part in p.split("."):
                node = node[part]
            if node:
                return node
        except Exception:
            continue
    return default


def _students_client():
    """Supabase project holding the Student Register, Window of Tolerance
    reports and the Document Archive. Uses archive_utils' own connection when
    available (so it always lands on the same project as the archive), then
    falls back to the *_STUDENTS env vars, then the unsuffixed ones."""
    if "_tr_students_client" in st.session_state:
        return st.session_state["_tr_students_client"]
    client = None
    try:
        from archive_utils import _get_client as _au_client
        client = _au_client()
    except Exception:
        client = None
    if client is None:
        candidates = [
            (("SUPABASE_URL_STUDENTS", "supabase_students.url"),
             ("SUPABASE_KEY_STUDENTS", "SUPABASE_ANON_KEY_STUDENTS", "supabase_students.key")),
            (("SUPABASE_URL",), ("SUPABASE_KEY", "SUPABASE_ANON_KEY")),
        ]
        for url_names, key_names in candidates:
            url, key = _secret(*url_names), _secret(*key_names)
            if not (url and key):
                continue
            try:
                c = create_client(url, key)
                c.table("student_directory").select("id").limit(1).execute()
                client = c
                break
            except Exception:
                continue
    if client is not None:                      # only remember a working connection — retry on the next run otherwise
        st.session_state["_tr_students_client"] = client
    return client


def _smartar_client():
    """Same project/credentials the SMARTAR Goal Builder uses."""
    if "_tr_smartar_client" in st.session_state:
        return st.session_state["_tr_smartar_client"]
    url = _secret("supabase.url", "BEHAVIOUR_SUPABASE_URL")
    key = _secret("supabase.key", "BEHAVIOUR_SUPABASE_KEY")
    client = None
    if url and key:
        try:
            client = create_client(url, key)
        except Exception:
            client = None
    if client is not None:
        st.session_state["_tr_smartar_client"] = client
    return client


# ══════════════════════════════════════════════════════════════════════════════
# CONSTANTS
# ══════════════════════════════════════════════════════════════════════════════
# ── SMARTAR / GAS — identical to 25_SMARTAR_Goal_Builder.py ──────────────────
LEVEL_ORDER  = ["EXCEEDING", "ABOVE", "EXPECTED", "BELOW", "NOT YET"]
TRACK_LEVELS = ["EXCEEDING", "ABOVE", "EXPECTED", "NOT YET"]   # BELOW isn't tracked daily
LEVEL_EMOJI  = {"EXCEEDING": "🌟", "ABOVE": "✅", "EXPECTED": "🎯", "BELOW": "⚠️", "NOT YET": "❌"}
LEVEL_COLOR  = {"EXCEEDING": "#1a7a3c", "ABOVE": "#2d8a5e", "EXPECTED": "#1d6fa4",
                "BELOW": "#d97706", "NOT YET": "#c0392b"}   # Builder's text colours
MPL_COLOR    = {"EXCEEDING": "#27ae60", "ABOVE": "#2ecc71", "EXPECTED": "#2980b9",
                "BELOW": "#e67e22", "NOT YET": "#c0392b"}
SCORE_MAP    = {"EXCEEDING": 5, "ABOVE": 4, "EXPECTED": 3, "BELOW": 2, "NOT YET": 1}
SCORE_TO_LVL = {v: k for k, v in SCORE_MAP.items()}
GAS_COLUMN   = {"EXCEEDING": "gas_exceeding", "ABOVE": "gas_above", "EXPECTED": "gas_expected",
                "BELOW": "gas_below", "NOT YET": "gas_not_yet"}
SESSIONS_FOR_PERIOD = {
    "All Day":            ["Morning", "Middle", "Afternoon"],
    "Morning Only":       ["Morning"],
    "Middle Only":        ["Middle"],
    "Afternoon Only":     ["Afternoon"],
    "Morning & Middle":   ["Morning", "Middle"],
    "Middle & Afternoon": ["Middle", "Afternoon"],
}
ALL_SESSIONS = ["Morning", "Middle", "Afternoon"]

# ── Window of Tolerance — same zones/columns/colours as the WoT Builder's Regulation Map ──
WOT_ZONES = [
    {"id": "hyper",      "name": "Mobilisation",        "tag": "Hyperarousal",     "color": "#C1543A", "tint": "#F3E2DC"},
    {"id": "copingup",   "name": "Coping",               "tag": "Early warning",    "color": "#C98A2E", "tint": "#F3E7D3"},
    {"id": "wot",        "name": "Window of Tolerance", "tag": "Regulated",        "color": "#4C7A5A", "tint": "#E1EBE3"},
    {"id": "copingdown", "name": "Coping",               "tag": "Early withdrawal", "color": "#3E6E8E", "tint": "#DEE7ED"},
    {"id": "hypo",       "name": "Immobilisation",      "tag": "Hypoarousal",      "color": "#38456B", "tint": "#DFE2EA"},
]
WOT_COLS = [("context", "Context"), ("behaviour", "Behaviour descriptors"), ("interventions", "Interventions")]

# ── Report sections ──────────────────────────────────────────────────────────
SOUNDS_WRITE = [
    ("Blending (building words)", 14),
    ("Segmenting (identifying sounds)", 69),
    ("Phoneme Manipulation", 10),
    ("Alphabet Code Knowledge", 50),
    ("Non-Word Reading", 30),
]
# Big Ideas in Number — the 4 big ideas / 19 elements on the CLC report's assessment grid
BIIN = [
    ("Trusting the count", [("1.1", "Subitising"), ("1.2", "Mental objects")]),
    ("Place value", [("2.1", "Number naming"), ("2.2", "Efficient counting"), ("2.3", "Sequencing"),
                     ("2.4", "Renaming and counting")]),
    ("Multiplicative thinking", [("3.1", "Countable units"), ("3.2", "Additive strategies"), ("3.3", "Sharing"),
                                 ("3.4", "Arrays and regions"), ("3.5", "Cartesian product"),
                                 ("3.6", "Propositional reasoning")]),
    ("Partitioning", [("4.1", "Equal parts"), ("4.2", "Fraction naming"), ("4.3", "Fraction making"),
                      ("4.4", "Fraction recording"), ("4.5", "Decimal fraction naming and recording"),
                      ("4.6", "Comparing and ordering"), ("4.7", "Rational number sequencing")]),
]
BIIN_RESULTS = ["", "Mastered", "Developing", "Needs improvement"]
BIIN_RANK = {"Needs improvement": 1, "Developing": 2, "Mastered": 3}
BIIN_FILL = {"Mastered": "B7DE9B", "Developing": "FFE38A", "Needs improvement": "F4A9A3"}   # green / yellow / red
BIIN_LEGEND = "Green = Mastered (90–100%) · Yellow = Developing (70–80%) · Red = Needs improvement (< 70%)"

# High Impact Teaching Strategies and their key elements — the same matrix as the CLC report template
HITS_ELEMENTS = {
    "Goal setting": [
        "Goals are developed from outcomes of student assessments",
        "Goals are presented clearly to students, so they know what they need to learn",
        "Goals focus on surface and/or deep learning",
        "Challenges student relevant to their current mastery of the topic",
        "Goals are linked to explicit assessment criteria"],
    "Structuring lessons": [
        "Clear expectations", "Sequencing and linking learning", "Clear instructions", "Clear transitions",
        "Scaffolding", "Questioning / feedback", "Formative assessment", "Exit cards"],
    "Explicit teaching": [
        "Shared learning intentions", "Relevant content and activities",
        "New content is explicitly introduced and explored",
        "Teacher models application of knowledge and skills",
        "Worked examples support independent practice",
        "Practice and feedback loops uncover and address misunderstanding"],
    "Worked examples": [
        "Clarify learning objective / demonstrate what students need to do to acquire new knowledge & skills",
        "Present the steps required to arrive at a solution, reducing cognitive load so students can focus on process",
        "Students practise independently using the worked example as a model"],
    "Collaborative learning": [
        "Students work together to apply previously acquired knowledge",
        "Cooperatively solve problems using previously acquired knowledge & skills",
        "Work in groups that foster peer learning", "Groups of students compete against each other"],
    "Multiple exposures": [
        "Time to practise what they have learned",
        "Timely feedback provides opportunities for immediate correction and improvement"],
    "Questioning": [
        "Plan in advance for probing, extending, revising & reflecting", "Use open questions",
        "Questions as an immediate source of feedback to track progress/understanding",
        "Cold call and strategic sampling"],
    "Feedback": [
        "Precise, timely, specific, accurate and actionable",
        "Questioning and assessment is feedback on teaching practice",
        "Use student voice to enable student feedback about teaching"],
    "Metacognitive strategies": [
        "Teaching problem solving", "Teaching study skills", "Promotes self-questioning",
        "Classroom discussion an essential feature", "Uses concept mapping"],
    "Differentiated teaching": [
        "High quality, evidence-based group instruction", "Regular supplemental instruction",
        "Individualised interventions"],
}
HITS_OPTIONS = list(HITS_ELEMENTS.keys())
# ── Information blurbs — wording from the CLC report template, giving a reader context ──
BLURB = {
    "literacy": ("Reading is a complex process that involves learning to recognise the words in texts (reading "
                 "accurately) and making meaning from texts (comprehending language). The ability to read is "
                 "fundamental to students' learning, their development of broader literacy skills and their future "
                 "success. Our reading focus within Learning Centres has been on supporting the development of "
                 "vocabulary, linguistics, and phonics."),
    "vocab": ("The Word Aware program is an evidence-based, structured approach to promote language development in "
              "children of all abilities. The following results reveal vocabulary progress."),
    "sounds_write": ("Sounds-Write is a linguistic phonics program that uses an evidence-based and highly effective "
                     "approach to teach reading and spelling. The following results reveal linguistic and "
                     "phonological skill progress from Sounds-Write assessments."),
    "biin": ("The Big Ideas in Number is a framework of 6 numeracy concepts providing the foundation for developing "
             "number sense. Number sense is fundamental to mathematical learning."),
    "hits": ("These 10 High Impact Teaching Strategies (HITS) are a part of the repertoire of effective strategies "
             "that teachers can apply to the wide variety of learning needs students present with each day. This "
             "ensures that every student is supported to access their learning entitlement. The strategies and key "
             "elements below have promoted positive student engagement in learning."),
    "smartar": ("Prior to a student's placement at the learning centre, the team around the child analyse behaviours "
                "of concern against exclusion goals, interventions and supporting documentation to create SMARTAR "
                "goals (Specific / Measurable / Achievable / Realistic / Timely / Agreed / Reviewed). Learning centre staff use "
                "these SMARTAR goals to develop a meaningful intervention plan, focusing on specific personal and "
                "social capabilities."),
    "gas": ("Goal Attainment Scale (GAS) is a functional scale designed to track student SMARTAR goal progress. GAS is "
            "characterised by a range of SMARTAR goals that have been scaled upwards and downwards in relation to "
            "performance levels. The highlighted level within each GAS represents the success criteria the student is "
            "currently meeting, as a result of the observational data collected throughout the student's placement. "
            "The GAS also provides valuable information about the next SMARTAR goal the student can progress towards."),
}
RP_BLURB_INTRO = ("Relational safety is embedded in the way we work restoratively with students. It is woven within a "
                  "sequenced process of engagement between adult and student.")
RP_BLURB_STEPS = [
    "Prepares themselves to support relational safety with the student.",
    "Carefully selects activities that support the child to feel safe within relationships and context.",
    "Relationally merges with the student by synchronising to the child's internal state, creating a relational "
    "boundary of strength and support.",
    "Reciprocally consolidates with the student, characterised by reciprocal exchanges that are playful and "
    "repetitive. This supports the student to feel connected to the adult and helps the student to feel stable, "
    "calm and secure.",
]
RP_CITATION = ("Tucci, J., Weller, A., & Mitchell, J. (2018). In Porges, S.W., & Dana, D. (Eds). Clinical Applications "
               "of the Polyvagal Theory: The Emergence of Polyvagal-Informed Therapies (pp. 89–105). New York: W.W. Norton.")
SOUNDS_WRITE_DESC = {
    "Blending (building words)": "Pushing sounds together to build words",
    "Segmenting (identifying sounds)": "Pulling apart the individual sounds in words",
    "Phoneme Manipulation": "Inserting sounds into and deleting sounds out of words",
    "Alphabet Code Knowledge": "Mapping sounds to letters",
    "Non-Word Reading": "Using sound-mapping skills rather than visual memory",
}
SCORE_LEGEND = "Green = Mastered (90–100%) · Yellow = Developing (70–89%) · Red = Needs improvement (< 70%)"
WOT_ZONE_DESC = {
    "hyper": "Too much arousal to integrate. Activation of the sympathetic nervous system (fight / flight / freeze).",
    "copingup": "Coping mechanisms — reduced capacity to learn and interact.",
    "wot": "Student feels safe to learn and interact with others.",
    "copingdown": "Coping mechanisms — reduced capacity to learn and interact.",
    "hypo": "Too little arousal to integrate. Activation of the dorsal system (submission / collapse / blunted).",
}

RP_OPTIONS = ["Comic Strip Conversations", "Circles (Nurture/Restorative/Community)",
              "Restorative Meetings", "Relational Mapping", "Restorative Conversations",
              "Affective Questioning/Statements"]

# Restorative 'flower' (from the CLC report template) and each petal, cut from it
RP_FLOWER_JPG_B64 = (
    "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"
    "ra61ZWNkwZiWP6TM6d+zGnaR32nN3B5Sfcr/AGOtCXFTfjzb+HyMbv6FSPDOPhyS+JM9Swac03TsWf0Xo35XZ2zUYJpHtbHE3b2Q"
    "Gnr3O2/ZZHD4PDYTV+RdVx0UoqZ+nDW9cSfVMkHUD4E9PgFVeWz+WysRiv2vXMNl9rYtA/Wv+05d1nVGesSWZJMg/nszx2JXNaAT"
    "IwbNd7ttlY9PrOOHLnz3fisGRalQVTiUNly2XgyaZCvV1fkNSYivhKdPM155JqT4GuabHJI4PadydyR16eKinECvjcfm2YjGRs2x"
    "8DK9iZp3M84G8jj8zsNvAL24fXF9mqG6izMkt25WrPZVLA1gbIQQC4ADcdST4kqJSSSSyvllcXSPcXOcfEnqSpFrb1YT978KXj15"
    "fz1I15dUqtPMV7zfPy5/z0PlERbI1QRF7cFi7eazNXFUWF89mQRsHlv4/IdVbOSgm5ckXQg5yUY82Wf6N+jTls87Ul6IGlj3bQBw"
    "6STHx94aOvxIWy+w8lhtH4KppvTtPD02gMrsAc7xe77zj8SsyvNtSvXeV3U6dPQ9R0qxVlbqn16+oREUA2QREQBERAEREAREQBER"
    "AEREAREQBERAEREAREQBERAEQrjcoDlFwTssTldSYXGbi5kYGOH3AeZ34BY6lWFJZm8LzL4QlUeIrJl0UDvcT8NES2rVtWffsGD8"
    "zv8AksVLxWlJPqsM1vlzWN/4LV1de0+m8Oovhl/oToaTeT5Q+ZaKKqf8qtz+qYP8U/yXP+VW5/VMH+Kf5LF/cmn/AJ/o/sZP6Lef"
    "l+qLVRVV/lVuf1TB/in+Sf5Vbn9Uwf4p/kn9yaf+f6Mf0W8/L9UWqiqr/Krc/qmD/FP8k/yq3P6pg/xT/JP7k0/8/wBGP6Lefl+q"
    "LVRVV/lVuf1TB/in+Sf5Vbn9Uwf4p/kn9yaf+f6Mf0W8/L9UWqiqr/Krc/qmD/FP8k/yq3P6pg/xT/JP7k0/8/0Y/ot5+X6otVFV"
    "X+VW5/VMH+Kf5J/lVuf1TB/in+Sf3Jp/5/ox/Rbz8v1RKuJ+mmak01LDGwG5ADLXd4823VvwIWtcjHRvcx7S1zTyuBHUHyV0nipb"
    "/qmD/FP8lXmpm1sxmrGSZX+h+vdzOjYd283ifmuh0XtzplrGVOtU93ps/sZqWkXi2cfqiLost9VRf51/5IcVF/nX/gFvf/yFoX/a"
    "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"
    "2d5fsv3OEU0boF3JRjl1HioLl6Bk0FaUua5wf9kb7bKLZbH2sXk58dcj9XZgeWPb36/xW+cWuZ5TWsq9GKlOOEzyIiyWncNZzeVb"
    "jqzmskLHvJcDsAxpcd/wVqyzBCnKpJRistmNRfTmua7lcCDv22XyBuTt1QtcWnhobIueU7gbHc9tx3WSwGHs5qazHWcxv0arJZeX"
    "duVg3I+KLLL6dGdSSjFZbMYiybsQ9unm5f6XW9qcwmtzH1zdhvzEeSxoBKcuYnRnTxxLnucLhfW3jt032XHghjwB069Vtrwjzgz2"
    "gsbbe/mnjj9RMf7bOn7titSgrp9GHOCO9kdPyv8AZlaLMIJ+8OjgPlspNrPhnjxOp7I3vs993be01j49C+j2Wl3pD6hOoeKORLJO"
    "etQ2pwbdtm9XH5uJW2fEDOx6b0dlMzIQDWruLOvd56NH4kLQyeWSexJYlcXSSvL3nzcTufzK3ttHfiPT60tsHwiKw+EmM0/FWv6k"
    "1bWbPjGPjx8Ebj0dNKer/gxoLvcpbeFkjxWXgrxFY+iNFY93F6TTedsVxXqSvcIZeYfS2hrnNALfDbYn3bqVYTC6Usyah1FJY0fM"
    "aUEDIIWQTCpXLpOXne3u4kdB71a5pF6plHIprV0NayURytjLYXE1LdiRlIzyOY2fZ227G7Ehm/TcrpqcP8y67lIcjYo4qvi3tZat"
    "25eWLmd9kNIG7iR1G3gq8SLXFkQRWjpPQuKOL1QMlqHAzyRY0Pr2I3ukbBu9u024HTxG3dearo5+b0nUqYqLDmeK5bZFdjL/AFt4"
    "xM5uXY9Oo+z08E40V4WVuu6N3N0P2vPzWVwGmcjmcTkMjV5RHTdFEGHfmmlkcGtjZ5u8Vmsnw5ydGrdezL4i3ex8RmuUYJy6WFo+"
    "14bHl8dj0Um2u3bVFKLNnpOpV9NrqrT5dV4oiSLhj+ZvvXO/uXZ0K8K0FKB7RY31G+oqtSeU/oET5FN/gspMCJuPMfim48x+KZQ2"
    "CJuPMfim48x+KZQ2CJuPMfim48x+KZQ2CJuPMfim48x+KZQ2CJuPMfim48x+KZQ2CJuPMfim48x+KZQ2CJuPMfim4J2B3J7KuUNg"
    "iyGPwuYyMgjoYu7ZeezYoHH+Cn2l+CGuMy5j7NSLFwH79l3tbe5o6/jso9W7o0Vmc0iHcaha26zVml8SsT07qb8OeGeo9aWGPq13"
    "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"
)
_PETAL_COMIC = (
    "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"
    "Wiiis2qV/9k="
)
_PETAL_CIRCLES = (
    "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"
    "RBBRRRRBBRRRRBH/2Q=="
)
_PETAL_MEETINGS = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwMDAgQDAwMEBAQFBgoGBgUFBgwICQcKDgwPDg4MDQ0PERYTDxAVEQ0NExoTFRcY"
    "GRkZDxIbHRsYHRYYGRj/2wBDAQQEBAYFBgsGBgsYEA0QGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY"
    "GBgYGBgYGBj/wAARCABSAJYDASIAAhEBAxEB/8QAHAAAAgIDAQEAAAAAAAAAAAAAAAYHCAMEBQIB/8QAPRAAAQMDAgQDBAcGBgMA"
    "AAAAAQIDBAAFEQYSBxMhMRRBUSJhcYEjMkJUkZOhCBVSYpLBJDNygrGyQ0TC/8QAGwEAAQUBAQAAAAAAAAAAAAAABgACBAUHAQP/"
    "xAA3EQABAgMEBggGAgMBAAAAAAABAAIDBBEFITFRBhJBYXGhEzIzgZGxwfAUFSIj0eE0QkNSgqL/2gAMAwEAAhEDEQA/AL/UUVEf"
    "EniU5Efd09p1/a8nKJMtB6oPmhB9fU+XYdagWlaUGz4JjRjdsG0nIKXJSUWciiFCH6TXqviRYdLrVFKjOnj/ANVgj2D/ADq7J+HU"
    "+6omvPFfVt0WpMaUi2snsiKn2vms5P4YpIUoqUVKUSSckk9zXTg6a1Dc2+ZAsk+Qg/bQyrb+J6Vls9pJaNovLYFWtybWveRf5Dcj"
    "uUsWTk2h0WhObvxgsEm73aa5zJd0mvq9XH1K/vWt4iT95e/MNdeTo/VUNouSdPXFCB1KgyVAfhmuKpKkLKVJKVDoUkYI+IqgjtmY"
    "bqxg4HfX1VvCdBcPt0I3UWTxMn7y9/Wa9Icmuq2tOyVq74QpRP6Vgrv6XkR4yro7KekNN+CIKoywh0fSN/UJ867KtMaIGOdQX38B"
    "VKMRDYXBtVxTIkgkGQ+CO4KzQJEo9pD58+izT0/Ftc2ROnTIXj3VOJAUy8nIj8obHclSfaUQcqweoII9cMKNGjqYdi2uElciA+0h"
    "iQcrdXygc534UFHOD7Pcjyqy+VRNanSXd+dOHNQhPsp1L+7Kvu5JfiZP3h7+s0eIk/eHv6zTrFtFmVOYTJgREwt8fkyBIO6SVY5i"
    "Fe12HteQ27R61gt8K3u6fXeX4NuaIHOaS3v9kpdSNqiV+mTtwSe+RTRZUatOkG3PAY/rNdM/D/1yy2pQcW+pGHVuqTnsskjPzrHg"
    "egp/uUOLcZ7tskpjRHpUuUqO4l3CEEKQpKyNxA3p3ZPn0rSlxNOL029Lt9tW6lSXfpkuAFhSVbUZyoEZACsbTu3HHu6+zYrdbViX"
    "Ab6+HePFJk8wgVZj7x8fBbXDrXy9Lzv3fc3HHLS8R558Mr+ID+E+YHxHvsIhaHG0uNqCkqGQpJyCPUVT+pS4X8QP3a6zpq8Of4Nx"
    "W2NIWr/JJ+wrP2Se3oT6HoS6KaRlhElNOuPVJ2bj6eCpbfsbpAZmAL9oz38c1OFFFFaSghFFFFJJJfErVitMaVKIjm24TMtMEd0D"
    "7S/kD095FQBZ7RcdQXpq225pT0h0k5J6JHmpR8h76ZeKd4VdeI0toLyzBAioGegI6qP9RP4VKXC7S7di0i3PfaxOnpDriiOqEd0p"
    "/DqfeazSahP0gtd0GtIUO7wx7yeXBG0CI2yLOEWn1v8AY7gOay6U4Z2PTrLb8llu4XADKn3k5Sk/yJPQfHvWbiTxBtXDPQ51BcoU"
    "2e47IagwbbAQFvzZLqtrTLYJA3E+vYAnypxqov7VXGfTK5T3DGHGQLzaZMa4pv0i7t21q0zkjmsctSkLLroSclITt2rwSCa0KUk4"
    "MowQ4DQ0bkIR5mLMP14rqlTbw34tOa01TddH6j0ZdtG6qtjDcx203Fxt7mxnCUoeadaJStO4FJ8welN2odHWHUsZSbjCRzsezJaA"
    "S4n/AHefwNUd4PftFsac4sStXcVrjbdUXm8NsWt+/Wi8MvC2REr9lIhpaRhresKWpKlKz1xgVf1p5qQyHGXEOIPZSFBQPzFPjS8O"
    "Oww4rQQdhTIUV8JwfDNDuVZtY6MuOkLoGpCufDdJ5EpIwF+4+ih6UtVazUViiai07ItMxI2Op9heOrax9VQ94NVamw37fcpEGUjY"
    "8w4ppY9CDg1kek1hizYwfC7N2G45fhaHYdqGehlsTrtx371mVaZadPt3otpMRbymNwOSlYAPUeQOe/uNe5ViuUOQxHchrW89HTJD"
    "bSStQQrOCoAdO361vW7UDVvtUWKqImU2lbxfYd6IcCigo6jzCkZ/TzroRdWN7FeKdeTIdZbDkkMJdPMS4tZG0kdDvHn0IFV0KXkn"
    "gBzyDQeNL/E3DK+qmvizLSSG1FT4Vu97Usx7dNlKb5EN5YccDKVhs7SonGM471sybFcoznKXFWt4OraLKEKUsbcAnGPqnIwa7zmr"
    "m3ILW1x1DqPZcbEZGHRzuYVb8+znzAHcdDWKVqOILfcGIT83fI8RscUNhHMcbVg4UemEKH4U8ykkG9pU03eSb8RMl3Upfv8ANLzN"
    "tuD/ADORb5LnLOHNjKjsPv6dPnWJ6NIjqSJEZ1kqG5PNQUkj1GfKpAau8KdZnZKZvh3lBzc+twBTOWUIVuRvBUVFBwcK70pX24xL"
    "k6w8yp9x/Ci+66nYFknIwncQD6kYB9KZOSMGBD1mRKnZhf6+m/YnS83EiP1XNoPfvNcij40UVUKwU28LeIHjmmtM3l0CS2kJiPqP"
    "+akD6h/mA7eo946yrVPkqUhaVoWpC0nKVJOCCOxBqwXDbXqNSwBa7m4lN1YR3Jx4hI+0P5h5j5/DT9FdI+nAk5k/WOqTt3Hf58cQ"
    "a37G6ImZgD6doy38PJP9FFFHaFFVBsKvOs0B4kmZNAVn+dzr/wA1a1CEtthCAEpSMADyFVQt7v7v1dFefG3w8xClj02udf8AirYA"
    "gpyD0PUGgLQehEwT1qivNFmlIIMEDCh9FDOqP2jeG9o1Dd9PXODqSXa7dIFtvN+h2t122W51YALT0hP1SNwCiAduRkikvUX7Nrek"
    "+J+lOInALTOkI0u3ty0XCLfJkpTM1LzSUNr3/SElI3en1hUU65uUaFf+IOhNO60uqOFN6vjz+qbxH0u7MRaJDykmUw3NSsI2Egbl"
    "FCuXn3dbLap4k3uzzYmhuFvD656tuhgtOtzHFeFtUVlScNrdlq6L6DO1sKUR6UeoTUS6d4b6g4/ag0PrLiDaOG900FbGp6mkWmRL"
    "kLnrcHKG/nNoPsLbJBJ8j7qfX+K/B/ga/P0BprSV8FtsSRKu6tNWhyTDs4d9vdIWD7JIO4gZIHU1xeE9y1/wH0jYOFvETQkmfaGn"
    "TGh6r0wVzo2555SwmSyQHWcKcI34Ke3ao64r32dpni1xHtHDvVV1VY76EK1o5E0s7dk2FxTAaccbeQtIC1NAEoUFbcZ+CSVzbfcI"
    "V3s8W6W2U1KhS2UPsPtHKXW1gKSoHzBBBqv3FmGiJxNkrbAAkMtvED1I2n/rUycPI2nYXCXTMLSM8T7Cxa4zVvlBW7nMJbSELz6k"
    "AH41D3F2S3I4mvNoOSxHaaV8cFX/ANCg/TYN+XgnHWFPAoj0Xr8YaZH0SLXQtNmlXl91qKtlCm0pJ5qiM7lBIAwD3JFc+tmLcJcJ"
    "iS1FeU0JKA24pBIVtCgcAjt2rK4Bhh46UVbfhwu5o9ih5b9vFbCbDeFJJFvkFXcJ5Zyodeo6YwNpr2NO3sJeU9bJLCWWS+tTzZQA"
    "kDPcjzx0rZk6tu8m3phK8MhpLYbAaa24A/vX2Vq+7zGnm5AjLDoWCotklO8YWUknoSO/l6YqeWWcBc5x7goutN5N5rg0UUVVKcii"
    "iikkis8OZJt9wZnQnlMyGVBbbiO6SKwUU5ri0hzTQhccARQ4KyuhNaxdXWTKylq5MACSwP8Aun+U/oelFLXDbh2mDbTeL8yoyZTY"
    "DcYkp5SCQfax9o4HTy+NFbhZEadiSkN0y0a9M6HcSKY097Fltow5Zkw9sBx1eH7UacQLUbRxFukbZtbdc8Q3jttX7XT55HyqbOHG"
    "pUah0WwHHAZsQBiQnzOPqq+YH45rg8YtLquFka1FEbKn4SSh4AZKmie/+09fgT6VEmm9R3DS98RcoC+o9lxpR9l1Pmk/2PlQSZh2"
    "j9rv1x9p9/cTiOBqijoRa9nM1T9bPMfkLRtGkf2iNL8BNR8IofCzTt0iXEXZhN6VqZDRUmY48oOFktHqkO9irrjyqynD6xzdNcJt"
    "L6duZbM222mLCf5atyeY2ylCsHzGQetfNMa2smqoqVQpAblAfSRHThxHy+0PeKZa0iBMQ5hgiQnAtO0IKiwnwXFkQUIXwjPXzqs+"
    "n7Rx94c3LXNosfC3T+pbbfNST7yzcHtSJiKUiQRtSpstKOQEjOT7qszXNvF8tVigKmXWa1GaHbeeqvckdyfhT4kRsNpe80AzTWtc"
    "8hrRUlIXCayzuFP7L+m7Jq4sMzLNbQ3KSw5zEheSdqVefcD41FbMuNfdQ3W43eM684629MAbe5eCkFW3scjGB8q6mvNeytXTBHYS"
    "uPa2VZbZJ9pw/wAa/f6DypMBI7EjyrKdJNIGTsw1kIVhs5nP8I/sWyHS0Fzolz3ch7xTiNAvutc1i5MqHJDxHLVhORkJ3HAV08xn"
    "qK0zpVrxETlXVt9l10JdXyy1y0YUoqJUfRCvh0pc5rgAAcWBjH1iBj0r5vUR9c4+NUTpqTIGrAp/0VbNgzAxi8gmt3R7KpKixcTy"
    "nCpyOhtovqW0NuFZScE5WAcfwqNDmhno7jolXJptCXUtIcS0paXidmCkjunK8Z9xpVC1gjC1DHbBPT4Ub14A3qwOw3Gl8TJm8wP/"
    "AEVzoJgf5eQTcvR0aMtEaVKkKkFp5Z5TJIWpBRgJB7pwo+0O+PdWK46PZj26dc412bXGYWtLbaml71FKiCCR0Hboo9DSrzFZHtqy"
    "Og9rtX3evBG9WD3GT1rr5uUII6DhecueaTZeYBBMXjcF5oooqqU5FS3ws4f89TOqL0z9EDuhx1p+sfJxQPl6D5+lcjhpoBWoZgvF"
    "3ZULUyr2EEY8SoHt/pHn69vWp9SkJSEpAAAwAPKtA0T0d1yJ6aF39RnvPp4oR0gtnUBlYBv/ALH0/K+0UUVpSCV5WhDjam3EJWhQ"
    "IUlQyCD5EVXniHoF7S9xXcLe0pdoeV7JHUsKP2Fe70Py797EVjfYZlRlx5DSHWnElK21p3JUD5EVT21Y0K1IPRvucMDl+s1ZWZaU"
    "SRi67bwcRn+1UNC1tOpcbWpC0nKVJOCD7iKZ4HEXWdvbDbV8ecQOwfSl39SM/rTxqvg2pTjk3SjqQCSTBeVgD/Qr+x/GoquVpudn"
    "kmPdYEiG4PJ5BSD8D2PyrKpqRtKx3nrNGbSaHvHqj2BNSVpNGBORpUJkk8UNbyWyg3gNA+bLKEH8cUrzJ024yjJny3pLx7reWVH9"
    "a16KrZifmZi6NELuJJU2DKQYPZMA4BFFFFRFIXSssqPEnuOPu8hSmVoakcvmclZxhW34ZHuzmu8zd7Fujia4JD7CVHxiWVIUtRWr"
    "oR224I8s0n9aKny1ovl2hrQDx9078VFjSjYpqSR797k5SLrYAsfupaGHCp91DimlJUhamsJKlHIzuzjHQZFeGtQ2t5Sl3VciVzYr"
    "cTGwfRAo+lX1HfcE9uvSlDrRXt83i1qGgbqXYUwXn8BDpQk+vimqbdID9vnpauaVxlxwiPAMbYWlApxhXnjBPfr3Natq0Rqu9x0S"
    "LdZJC2HBuQ84UtoUPUFRGR07iveidLu6r1YzbyFCKgc2UsdMNg9gfUnoPmfKrOtttstJabQEIQAlKQMAAdhRLYlh/OWmZmqtaLhT"
    "btONbhhcqC1bVdZzugl7zia7MsKX7b9ygmBwV1I+pJnT7fEQT7QSpTqh18gAB6+dNFv4I2NlCTc7rOlrB6hraygj0x1P61KFFF8v"
    "otZkG/oqneSeWHJDka2p2LjEI4XeSxRo0eFDaiRWUMsNJCENoGAkDsBWWiiiAAAUCrCSbyiiiiuriKKKKSSKxPR2JLRZksNvNnuh"
    "xIUD8jRRXlG7Ny9IXXChvWtotMe6KEe1wmhn/wAbCU/8ClPwUL7ox+WKKKyCd7Zy0eT7II8FC+6MflijwUL7ox+WKKKiqSjwUL7o"
    "x+WKPBQvujH5YoopJI8FC+6MflijwUL7ox+WKKKSSlnhXFjMaalrYjtNKXJIUpCAkqASMZx3xk/jT5RRWr2D/AhcPUrO7U/lxOKK"
    "KKKt1XoooopJIooopJL/2Q=="
)
_PETAL_MAPPING = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwMDAgQDAwMEBAQFBgoGBgUFBgwICQcKDgwPDg4MDQ0PERYTDxAVEQ0NExoTFRcY"
    "GRkZDxIbHRsYHRYYGRj/2wBDAQQEBAYFBgsGBgsYEA0QGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY"
    "GBgYGBgYGBj/wAARCABSAJYDASIAAhEBAxEB/8QAHQAAAgICAwEAAAAAAAAAAAAAAAcGCAMFAQQJAv/EAEMQAAEDAwIEAwQECgkF"
    "AAAAAAECAwQABREGBxIhMUEIE1EUIjJhFXGR0SNCVFVigYKTlMEWM0NSU3KSobElc6Ky8P/EABsBAAEFAQEAAAAAAAAAAAAAAAcA"
    "AQQFBgMC/8QANREAAQMCAwYCCgICAwAAAAAAAQACAwQRBSExBhJBUWFxobETFCIjMoGRwdHwNOEz8VJyov/aAAwDAQACEQMRAD8A"
    "v9RRRSSRUY17rqybeaLkajvrqg0g+WyyjmuQ6QeFtA9Tg8+gAJPStlqTUVp0ppabqG9yRHgw2y66vGT8gB3JOAB3Jrz/AN1dzrvu"
    "frVy6yy7HtzJKIFvK8pjo7k45FasZUf1DkBV3guEOr5LuyYNT9h+5LR7OYBJi0+eUbfiP2HU+Gq1Gt9dah1/q9/UN/llby/daZbJ"
    "DcdsHk2gdgPXqTkmo7xr/wARf+o180UTI42xtDGCwCNsNJDCwRxtAaMgsqJMlsENyXkZ68DhGfsNfXts78ulfvlffWCivW6OS6+j"
    "ZyCz+3Tvy6V++V99fJlSicmS+T/3D99YqKbdbyS9G3ksvtMn8pe/eGj2mT+UvfvDWKilut5J9xvJZfaZP5S9+8NcplSknKZT4PqH"
    "FD+dYRzUEgEqPRI5k/qrvGy3kR/PNnuIaxnzDFc4ceucYpjuDWy8u9G3J1gtjaNc6zsDocsuq7xBI7NS18P+kkg/ZTh0Z4rtZWd1"
    "uNq+FHv8TICnmwI8lI+se4r9YH11X88llJ5KHUdxRUSpw2mqRaVgPXj9VArMGoa1tp4getrH6jNekehNydI7i2gztM3MOrbH4eI6"
    "OB9g/po9PmMg+tS2vMCw3+86Yv8AHvdguL8CewrKHmVYPzBHRST3SeRq9uzG8dt3R06WZAah6hhoBmQ0nksdPNbz1QT26pPI9icL"
    "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"
)
_PETAL_CONVERSATIONS = (
    "/9j/4AAQSkZJRgABAQAAAQABAAD/2wBDAAQDAwMDAgQDAwMEBAQFBgoGBgUFBgwICQcKDgwPDg4MDQ0PERYTDxAVEQ0NExoTFRcY"
    "GRkZDxIbHRsYHRYYGRj/2wBDAQQEBAYFBgsGBgsYEA0QGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgYGBgY"
    "GBgYGBgYGBj/wAARCACWAHYDASIAAhEBAxEB/8QAHQAAAQQDAQEAAAAAAAAAAAAAAAUGBwgBAgQDCf/EAEQQAAEDBAAEAwUGAwQH"
    "CQAAAAECAwQABQYRBxIhMRNBUQgiYXGBFBUjMoKRQlKhFiRichczQ5WxwdIlR1NXkqKy0fD/xAAcAQABBQEBAQAAAAAAAAAAAAAF"
    "AAIEBgcDAQj/xAAyEQABAwIDBAoBBQEBAAAAAAABAAIDBBEFITEGEkFRExQiYXGBkaGxwfAHFRYy0UIj/9oADAMBAAIRAxEAPwC/"
    "1FFFJJFFFFJJFFFNHiPnkLh7hD16faEiSpQZiRebl8Zw9h/lA2SfQfKmveGAudouU88cEbpZTZrRcnuTuo2Kp3dfaL4kXHmESRbr"
    "WhQ1qLGCj21+Zwq+dMe755md+GrvlN1lI1rw1SFJR21+VOh/SoDsQb/y3891Sqn9QMPjyia558LD3z9leK65di9jaLl3yG2whzcv"
    "40lCTveta3umZdePvDG2bCL25cFj+GDHW5v5KICf61S7pzFWhzHuddazuuJr5OACr1V+olS7Knia3xJP+Ky929qa3oCkWTFJLx/h"
    "cmSEtjv/ACpCj2+NMa7e0hxDnlQgG2WtB2B4EfxFAfNZP/Cogori6qldxVeqdrsVqMjMQO6w+M/dOe68RM5vmxc8ruzyT3Ql8to/"
    "9KNCrI+zflCrxw0fscl5Tkm0v8g5lbPhObUn9jzj6Cqj1K3s95IbHxijwXV8se7NKhq325/zNn9wR+qn00pbKLnVStlsYmixSN0z"
    "yQ/sm5J10177K5FFFFGluSKKKKSSKKKKSSwpQSkqUQABsk+VUq40Z8c54huGE+V2e37jw9dl/wA7n6iOn+FKfWp64+Z//ZTBPuS3"
    "vct1u6VNJKT1aZ7LX8Cd8o+JJ8qrLw/gQrjnceLPjRX2BHkOeHK2GtoZWpJVryBAJ+VDK2TecIgs221xUzyswiA5uI3j46D7Pkmw"
    "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"
)
_PETAL_AFFECTIVE = (
    "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"
)
RP_PETAL_JPG_B64 = {
    "Comic Strip Conversations": _PETAL_COMIC,
    "Circles (Nurture/Restorative/Community)": _PETAL_CIRCLES,
    "Restorative Meetings": _PETAL_MEETINGS,
    "Relational Mapping": _PETAL_MAPPING,
    "Restorative Conversations": _PETAL_CONVERSATIONS,
    "Affective Questioning/Statements": _PETAL_AFFECTIVE,
}


def b64img(data):
    import base64
    return BytesIO(base64.b64decode(data))

TEAL = "#1A7A6E"
WOT_CHAR_CM, WOT_LINE_K = float(os.environ.get("TR_WOT_CHAR", 0.0185)), float(os.environ.get("TR_WOT_LINE", 1.18))  # tuned against renders
HEADER_NAVY = "#323E4F"          # section header bars, as on the CLC report template

# ── Cover page — recreates the CLC report cover (navy / green / lavender shapes,
#    Cowandilla Learning Centre logo top right). Coordinates are on the original's
#    579 × 818 grid (A4). ──
COVER_W, COVER_H = 579.0, 818.0
COVER_NAVY, COVER_GREEN, COVER_GREY, COVER_LAVENDER = "#0F2B50", "#57B848", "#788FA0", "#D8DDED"
COVER_FONTS = ["Liberation Sans", "Arial", "Helvetica", "DejaVu Sans"]
COVER_SHAPES = [
    (COVER_GREEN,    [(163, 0), (233, 0), (579, 346), (579, 366), (163, 366)]),
    (COVER_NAVY,     [(48, 0), (175, 126), (48, 126)]),
    (COVER_GREY,     [(103, 0), (126, 0), (176, 53), (103, 53)]),
    (COVER_GREEN,    [(0, 77), (49, 126), (0, 126)]),
    (COVER_LAVENDER, [(435, 366), (501, 366), (579, 444), (579, 632), (435, 632)]),
    (COVER_GREEN,    [(435, 502), (492, 559), (435, 559)]),
    (COVER_NAVY,     [(0, 204), (579, 761), (579, 818), (0, 818)]),
]
CLC_LOGO_JPG_B64 = (
    "/9j/7gAOQWRvYmUAZAAAAAAB/9sAxQAGBAQEBAQGBAQGCAYGBggKCAcHCAoMCgoKCgoMDAwMDA4ODAwMDhAQFRMMExQUFBQZGhwc"
    "HBofHx8fHx8fHx8fAQcFBQYFBggGBggJCAgICQwKCgoKDAwLDA0MCwwMDAwMDw4MDAwMDAwPDAwODg4ODhEQEBAQEBMTExMVFRUX"
    "FxcCBwUFBgUGCAYGCAkICAgJDAoKCgoMDAsMDQwLDAwMDAwPDgwMDAwMDA8MDA4ODg4OERAQEBAQExMTExUVFRcXF//dAAQADP/A"
    "ABEIAP4AwAMAIgABEQECEQL/xAGiAAEAAgIDAQADAAAAAAAAAAAABwgBBgMEBQIJCgsBAQACAwABBQAAAAAAAAAAAAAFBgEDBAIH"
    "CAkKCxAAAQIDAQQGBgx/AAAAAAAAAQACAwQRBQYSITEHQVFxgaETFSIyYbEUIyRCU3KRkqKyweEICQoWFxgZGiUmJygpKjM0NTY3"
    "ODk6Q0RFRkdISUpSVFVWV1hZWmJjZGVmZ2hpanN0dXZ3eHl6goOEhYaHiImKk5SVlpeYmZqjpKWmp6ipqrO0tba3uLm6wsPExcbH"
    "yMnK0dLT1NXW19jZ2uLj5OXm5+jp6vDx8vP09fb3+Pn6EQAAAwEEBgcGhwAAAAAAAAAAAQIDBAURIhIhMUKS0hNSYnLR8PEGFDKC"
    "wuEHCAkKFRYXGBkaIyQlJicoKSozNDU2Nzg5OkFDREVGR0hJSlFTVFVWV1hZWmFjZGVmZ2hpanFzdHV2d3h5eoGDhIWGh4iJipGT"
    "lJWWl5iZmqGio6SlpqeoqaqxsrO0tba3uLm6wcPExcbHyMnK09TV1tfY2dri4+Tl5ufo6ery8/T19vf4+fr/2gAMAwAAARECEQA/"
    "ALUoiIAIhSqAPnLWCQAScQx5S8C6a7SyLmWXsw8xplwqyWhkX52JO3RsSoqt+7W3boXuZHi6glzil4RIbTpo43HPwbBcbqfFi5Yt"
    "xrqqe5HI63xYuWKcddVT3Ik62ckS5uyHOg6m2lxm44cDWqHMJ10bqtMtLJatqO4tsyXhSjMQL9rX+wtG6LRgABQCiKLbPs6WspJy"
    "BVmxEU2fZ0tZSTkCrNiPYm7r7p5wkxrSjAHGIZ1GN0berzYs5OzBrHmIsSuMve92zK4UXItqtdxqUq5hyLatGlxqUq5hm+eDUOIO"
    "bhXYgWrastx7zkxDzL2K4DdKrrIvElKScJHIjxJSknCk5EbBJXfXWSRF7PujAbdjNDwdEiumtnsvJeiCjLakgensu7TLXb4VHCLo"
    "ZO90sjlNVXNG6cOhk73SymNVXNG6cJ8sW6mwrdHEOmmPflwXazEHbpwr1yK48Kra1zob2xYZLHtNWuaSCDsCMS3S5vJNtOzS2Wtm"
    "+nZbANSYNTNGficM/DsVIuV+ULgS6CkDqybhEi5n5QsyS3KQOrJuES+mUuhZNsWfbUq2cs2M2LDdjocLTmEYwdgV31JpMlERpOEh"
    "JkolESknCRjKIiyMgiIgAiIgD//QtSiLBQBjGtCu3yQ22YX2TYjmxJuhEWNjbC2AzXaQWMkO7Y2Y11iWS8bS4g2vig8cWnKHTZ0g"
    "oqw1qTUk1JOEkqKfJ8jZmbBgcaeVm1ZKtCKfJ8jZmbBgcaeVm1ZKtD6jRYsxFdGjvdEiPJL3uJJcc0kr5RFDmcJwmIczMzhMERFg"
    "AREQAREQAREQAREQB37Gty0bAnGztnRSxwIv2HCx4zHNyxscYylMtyd1sjdPK6kg7VTMPBGl3GrmnNGa05qgtdmzrRm7JnYdoSMQ"
    "w40I1ByiMtrhlg5YXY4netyLkTjMzuJN1EOtwu9bkVInGZnO3UQsXnJgIXhXKXTy109nNmoVGRmUbHg1qWP2Ga04wV7ozVYGa0tU"
    "ktBwkoWBC0tEktJwkYyiIvIeQIiIA//RtPU0Wv3Z3TMuZsl8wyhmo1WSzM11MJIzAMOkvfJAbUmgzVBV2tvvuht2LHY6svAJhS4r"
    "gvQcL89xw51Fxvi6jcrGFNxripsRyPi6rdWMU464qbEeJFjRZiK+PGcXxIji57zhLiTUkr5RduWs50zIzE814bqCNLwrylb4x3Fo"
    "NcqlNFV9KVLOVNFeSlS1SoxjqIvZnLmYslbbrIdMNe3UUWNDmAMD2w2uc4UvsBBYQcwrrNs6RgykCPaM2+DFmoQjwoMOEYhEMkhh"
    "e6+FC4g0ArgwryNgtJmSikZEeRsGiTMlFIyI89F2LRkXWftHLn3+0iVhzOKl7qS+1nY0vca7ZsNwt6BYepsMYwdrb3ANTMETXa5V"
    "aLFRrhggqqaIYqJcMEFVTRDzEXpNsuRgScvNWjNxIJmw90FsKAYgvYbiw1cXAB1WnWRWgWJaxIs0JAsitaJyHHjPc8GkGHLuIe40"
    "wuwAmgzlmoVwkUEsZqBcJFBLHnIvSNky0xChzNmTbpiEZiDLRr+EYT4boxox17UhzDhy61wFckxc5GlrVmrLdGBECWizUOMBVsWG"
    "xt8CMOCpBacwhKgXBCRDNQNIISIeSiwMIBzQsrWNQIiIMgiIgD1LmrfmbnLVh2hAJMOobHh89w64dEYxsVPMlNwJ+VhTsq4Pgxmh"
    "7HDLaRgVclJGRRdC6sW5yZNaAxZYk4ht9m+jRUm9DrNmuoFnKXcNeu4knodZoXbus5S7hr13EmosDEsqbE2CIiAP/9KwGSLbJsi5"
    "uMITr2NNEQIZGMX2vEZwqoSFAKDKW9ZLVpOmLal7LaaslYV+4DFfxd+GmtGVffVvUrpNJTERaYV99m9Suk0lMRFpgXqWdMQIVjz0"
    "CI9rXvmpF7GE0JbDe8vcNg0HCvLXckbKiz8vHmhHl5aDLuYyJEmHlgvolb0CjTWt6VysTUS4hSRyKhysTUS4UlJHIqGxQbWs2Nat"
    "qwpqMwMhRJyYs+YJq06mY5kSCDmOqHN2IK8iYl22vJyU1LTMrDdAk4cvMQY8UQojHQb4VAcNaa4EEEZeBdSLY07CiR4btROECW2l"
    "l7Hh0N8GoAcxw17CcWDSX06xYsOXbHmpmUl3PhiKyBFikRXMIq00DXUqMIBIJW1S2iyNK2dWs7ZMG1S2iyNK2dWs7ZMHbtOXFrSk"
    "nOSkzLAQZCHAiw4sZsOI18K+vm3rsJrUEEY13mR5SLbkpdPtLl2SsKHBfGhOfSO2JBhBhhCHSriS0UIwUw1XkS1gzk1BgRdSS0F0"
    "0Ky0KPFDIkYVoC1tHUBOAFxFTiXVjSMxAlROxmhrDGiS96dfESEAXgtyqVWJJZRzRWqG4VcmA1rKObK4pFVDcKh69gl7YfEQmZTV"
    "TFc4zUrHitL2jDV0Nmvtic8luPLwL7kZ+QhQrLgxowZDdKT8rFe7CYO0h7hDc8DKwgmmVhXRh3PTb3RdSxZaA2DAgzESJFeWsDJj"
    "jmKhpNTlimBdWekI8hEhtiuhxGxWakhRYL7+HEbUi+a7PBBBAIKSbRmkjkbhq1e6bFCTaM0kZolJq1e6bFHqSgg2LLNlpial4sWa"
    "nZN5ECJqVsOFLxL5z3OAoKl2AY6Y6LuyVqWfF1bQ5yO1j5ds9tAecUSHNX19CB3NRzc8rVQAMAwZyUG6LxS6TTBIlKTZu48Uuo0m"
    "UiUpNnp0sGijQNgFlEWkaAREQZBERABdmzLQjWVaEvaMDX5d4fSuNoOtNOeKhdZFlKjQolJmpBKjQolFNSLGyczCnJaDNwTWHGYI"
    "jTsHCo2a5xiC0/IwtMz9zTIDzV8m90E5tNebpGmgtxCtLBoTZkhoU8kWlg1JsyQ0KeSCIi2DYP/T2y6+bM7dPaMYmoEYwxnQ9ZGy"
    "XjrlnYpjzsxME4YsZ7ydzPJ31cSqjVcmtS6spQqjVcm0UurKUC9uyZiUgXPWk+clhNQtpcmDCv3QzTa2rg5uGoFaZWavEK7chZFp"
    "2oIhs+XMYQqakIcxoaXVvalzmipossVKSuFBSRyKotyjLBSkrhQUkcirkyR7c4Nr7UEG82hmxXCz7zANo5fDLBhJN+CSHVw1XJGs"
    "d9s2u60zBdFs2LJakEww6w10KXADXEa64ObQtO+rX22Rab511mNlYu0poJMEihDcd8STQNwg1rRcmqG2dpmq4Sr9TlupDCa9hF7i"
    "vi4OvQKimErbUilXEyUopLk0kqLcNamDdUilylMlKKS5NJKi3DWpg9R9nT1susa0bPh6ll4cpKwo8UFobAfAcdSCISdZpjqcYxLN"
    "oQo1vSU0LGhmbe21ZqMYcPC/UUZo1G8DHektOHKy15bbn7YfNRZBkq4x4bGxIsO/YAGE0a4uvr2hODGuPVPaonhZwlYomi0kQxgJ"
    "bluDgaXnTVabFYNSjIyNkqPcVe0iLYjBqUZGRslR7ir2kRbEbFNR5WCy2GxoTJtstI2bAiwtSFoMRjgHtDmZbTgwYKryLozDdGlH"
    "yQDbOdLgyDRUlrC4mI15JcS8PJvq7JdWJYlqwJyHZz5V+0iKKw4TS15Lc3WSQAKGtTgXKLm7dMwZQSjjFa0PvA+GTeuJAIN9Q1Ip"
    "QYUWto0SaJCzJSUjyaZtoLW0aJNEhZkpKR5NM20eci7U/ZdoWW9kO0IBgOfW9Bcwk0x66XUpUY11VoUk0nAopExzqSpJwKKRMERF"
    "gAREQAREQAREQBIWQ/Nls5aEiTgexkUZ7atOzClIhQ3kVRCy6q8GKJLRAdAtKmMKwPSo1OUiqqlJFgelck5CI51Skj6REXcO0f/U"
    "9V4Ie4HGCQd1WF2rVgmWtScltw5iK3QDjRdVVJSTSo0nOipKI0qMjnQXt2U2z3XO2oLTdFZBM3JAughrnA7W4aOwEAaK8RcsFk7G"
    "hxJeVbGiMcWuiQ4bXOBLa3rnBodiqaErzZLkFQwSUVSaJI82KpBcMElFVyZI2eK2DCnbTko8KLElJOyGQoRhvBiR4AiwnMih16Rr"
    "QdWlKAYMpeLLz9nykSYl4EnGfITcJsOYgRX7Wm9dfNe17WtvSDSlQQctdSBOWlCjwjLRo7Y8EGFBvC7UjW1OsNAwgYTrOkuY2vbr"
    "JwxjNzLZsgQiSXCJe1qGkUrSprSi2KbkqAyJSYyp1Krl7iAbVN5KAyJSYyp1Krine4gHrw7LkbPlLVhRokUyczISsywiG0RmtiRx"
    "etcwkAOBGHDQjCF92VOyMyJmThwph0pJWNNQwC5ojxA6Kx7yKAtbhNABWgXgzD7V1JE2lmY1JMAal1KHh0VrTUVvhVwFK5gWJaHa"
    "cCIyZk2TEN4wsiwmPBoRlOAxEaBWSbmlZEhEpM7c0kMk3kVkSESJJHpWaJR0O1odlQY8J7rOcGsiODojqRYZeQWtZgvcYpiXnWUw"
    "NtWQBbe1moJApTlo3EsxbQtePMMnY0xMPjwgbyMS6/a0HDQjEATh018R560JuKJuajxY0SDe0iuJJZQ1bR23cOEbFeCmiTkTjRVU"
    "U8NamiYUnGiqop4clsAC2J+mXNRq7vcuouWNBnBWZmYUYCKb4xYjHgOc7DW+IoScJXFRwbflpvSSA4g0JGMA4lqVCajMyuIa1Qmo"
    "zMriBFm9iYNYdhBcMBwty3DNGxxJevBbfNdrQBbgIqMojNGckBjEBjCLkhy01EDjCgRXhhIeWMeb05YdQYNFfMJkSM/UcCG+I81I"
    "axpcTm4BUpInmwSKs2Hyi+2wJh0Uy7YMQxRjhBji8du0qvraJOXxbtGjVZQOGo3VbXFUUwaKSKjmEEio5hDiRfUSHEguvIzHQ3Ur"
    "evaWmmbQr5SZKMDKCUY2zIwBN10EjcCNXdoU0Zah/Ing6kukixcqHLO3kWhTBXAp55ygctzKE885QOWGtKGURF3jvH//1d0u+kzJ"
    "XWTzaYIzmxm7EPAJ06rX1I+S9ZVHyVtQxjDpeLvZhOmFHCrLvZGydLVNakqKMK072RsnS1KtSVFGBe9YpiC561dRTu0B20mT2uvn"
    "twUi6zWGC7Dui8FcjZyNDlIsmHAQYz2RHtoK30Kt4a5VL5amSyQqSOqq5MkamKyQo1HVVcmSNjjWg18ralpyEZz5qWlZGVdPAFj4"
    "jnOcIsUbeBdQNqaEhfMK1jKylj2zP6kjRnidlIkw1wEfUWshj2udjcy/N6TnVXgyNoTFnxXRZYsOpGlkRkRrXseytb1zTgcKiuwK"
    "5YlszkaZhTMZsB+oGmHCgmEzULGnCQIeIYcNcdctbSdE8ZyJ8luKSkriqtqNpOmEpIzkT5LcUlJXFVbUe5ZsCb1bS82+efaMpHlJ"
    "4S0eI5xcL2C6/Y5riS1wwVGI4wulZ9p2nDuXn7ycmG6ijSTYZEVwvGnUlWtw4AaDAF03XQWi6LCjsdChiBDiw4UOFDYyEwRgWxKN"
    "GCrgcJOFdOFNxYcpFkobhqGO6G57aAkmFW8w5VL4opskjgRJT3JkpT04YU3Sk4EGqf5MlKenDYrOjNaLAhzDjqObZOy0ZxONsxFL"
    "CTm60QV82XAMjCsuzplm1s/a7THY7EYUq8QmtOwLy40XgRJ2PFgy8BzwIcrfahIoC0udfk1y8OFc89bU/aE3DtCZit1PBvdRvY1r"
    "A0tdf3wAwVJJcTllEt0kUMEtMjQxZLpvIjJN0kUMEtMjdMl03kR3boJmHHix2i15mecJl9ZeLDexjKOcKtJeRrOIUAwLvS0SRi3K"
    "2fZdpxRLwZiPNRGTN6XGHFhPh5Qw0c1zm59F4s9a0e0mUjQpZri6/dFhQWMiOdhqXObjrWpXA+amIsrBknkail3RHQwAAQ6KQX1O"
    "XUtCxU6UrWso0kmR5MmtDFTpStSijSSZHkyZsYbZGnGz8WRmobBDhusa0mQmAUvYUNz2Q25960VOauOIxlpSliyTWjaXIycnMwCB"
    "hiwS7a5hzS2geNhVa5DtSdhMhMY9oEGBFloesg0hRiS9uxJJx5SzCta0IM1KTkKIGxpGGyFAcANZYyt6CNvYzWuNedvSDuIrikZL"
    "ktLFHnb0hVxFcUjJclpYR7luTs5JyE3Ek5iLLudbs5fGE9zCaNBFaEVziszlpS8pPzMCNGiSLrRlpKO+dlxR7Iuo75181tCWOLqu"
    "DSDXDhXkMugtBrIsOIyWjtix3zREaA2IBGfrzm1xVpixLiZa02JmNNx2wZqLHIMR0zCbFFRivQddwYKDBTAinQkzhI1UNw3FWslk"
    "tIBTpSZkZGqhuG4q1kslpA9yWhzEhK2ybStCJLxi+SpPwb+M+JDffuZeuDmOvXADLwYiuvYM/Mi6eWZLWjMzEKLE1uK4vYYhEN2v"
    "NLjWmIVJxLz229aQmJiYiGFG2khojQ40Nj4bhD45gNpRt7iFKUXA20plloNtOA2FBjMNWiFDa1gN6W4G4sRK8TbIKRNElFVdSlVY"
    "eKm6CNJoNUVV1KVVhwxpiamn6lmo0SM8CgfEcXkDMqcpfCxiwITgqtCjhOEc5majhMSXkPSREK0bRcMDnMgtObQFztmFJQGCi124"
    "OzRZVzMpBcKRIrdTRc2+iYdlQLYcuisrhZGxczNJzZGGiliyuFlULmZoObIyVFGH0iIugdA//9ayN1Vitt2wpqztvvbWEcyI3C3T"
    "FFAb2PhPdDiNLXsJa5pxhwNCDoqyWPDmqIck65t1m2pq5lm7Zp07WU25Fph0HDDnqLflzGtBN0lLRFVXRGPy5TWgm6Slpiqro0rK"
    "XsWDGgtgTEvBiQJe0Ij2GXjTLGPhuYAb6CC4OaxxJqCRQ4qhePlLsSkWz4IeJ6T2lh1L0aldCvc0ayMIKiGS5BZGdmhEQxVILhPk"
    "3tR6UeDH1T2rEtKC2HOw56WY/WGsLasdUANFADQHBgONdmDAlYctKTxgw3vlrGizLWvaCx8YRzDa5429S+rQroPugfMxpsz8tDjy"
    "85qK/l2uMMM1A29hFjhUggYMNajGvnV7EE22KyXhCWZLGTEmS4sMualzS6t8XEm+vsdVuJoyScJHWbhjXFJSRjcTRkRwkdZuGtXE"
    "OxITsWdM9ak8yBHi2dJuiQG6hY1mpHPYwFzWgB17fEgHLXNYseNacxPTc06UbHlZJzoEaNCZDgw3GIxt85obekgGgJBouhCtWVlZ"
    "gvkpFsOBFhOgTMvEiviiMx5BILjQtIIqCMRSFaslLRohlpANlpiAYEeA6M95eCQ6+D9ZLXAjBRYQ0Sk0yS5KRuK4o1auGzAMJaJI"
    "0yS5KRuK4o1auGzBKHoS81DZaEdtoTki6aiwGslJ1kNr5eC++qQ9ohgAuGC+INFiXix5a0pqDbO0aWtCLChtlJmLChul2m+rfUa1"
    "zL14wB9DTLXmCbsnaUYmq06hLKah2kvqHV16+pXFgpSi+4tqyk1MMdOSLXy8GA2Xl5dkV8PUbGkka1hLiamtUJqUBQqTClVa5GLv"
    "xzQJqmVCaYUqrXIxd+OaOK1mz7Z57bTY1kcAVvGtaxzaay4Xga1wIwgjGuou1aU+bRjsiajbBhwoTIEGE0khkOHW9bfHC44SSSuq"
    "tKzI1maTkiGhoZGszSckQIiLxGAREQAREQAXsXJ2K637elpGlYTXakj5mo2mpGjgC8c4qlTDkaXNmx7JNpTTKTU8A/DjZD263YVx"
    "nfl1Pe5jdTdJGURMZVnSR0ve5jdLckncCYyrOkjcmta0BoFABQDKAzF9IEVkFkBERAH/17ULo2vZUrbVnxrOnG30OK2hzQcpwzCM"
    "a7xplpRYUklEZHMMYMiURpMpRivVuWLO2BaUSzZ5pDmGrH5T2HXXN33MK6CnW625SUunkDAfSHMw6mXj0wtdmHNacsKErRs6csmc"
    "iSE/DMKNDOEHERlOacsHKKrzvcKnIuEozNVw0pivO9wqci4UxmarhpTHXREXGOQEREAEREAEREAEREAEREAERe9clclOXUTgaAYc"
    "nDI1PGyqc8tzXHSxrzZMltlkhBSRqHkyZLbLJmzKSNQ9DI+uSdbs+LRnGbYZZwNCMESIMIaM1oxndFMgGDAuvISErZkrDkpNghQY"
    "TQ1rQMQ2OxOWV2RnqxOJyJcjKQK4juJWkixuNyJcjKQKWZ3EofSIi6R0AiIgD//QtSiIgDGwXhXTXLWddPK6hmheRmA6hjtGtsO+"
    "jNBXu4CEpmrxWzS1SaFlJEY8VoS0SaVlCRiALoLmrVubmdQWhDrDcaQ47amG8bA5R2BwrygaqxFp2bJ2xIxbPn4YiwYzS1wxEZhB"
    "yiMYKgu6y5ufuQtEQJwGLJRiRKzlMDhzw8DE8ZebjChHa9S2JmtjGRVZ4qYRDpeVpCanNHKqz22VbpR5aLljykzKtZEjwyIcQVhx"
    "RhY4ZrXDAdAriUepJpOBRSJiLUlSFGlRSJpBERYAEREAERDQCtQEAEqF9zEGNKSwnJljocJ2uF+Av3KDhcNiMC3jI6uFi2gYV0Nv"
    "QbyWBD5SVdr0Q5USIOectrcvGcGPoczhbOlREkpEqsodblex0OopMkyDOrKuHbKsOlclkfT1vOZOWiHSsjgOEUiRRmNBxN2J0FLs"
    "hISlmysOTkoTYMGGKNa0UA+GdiuwBSgxUykwKecrjZORMCJajuJWSiacrjZORMCChOeUPpERdA6AREQAREQB/9G1KIiACIiAC6Fs"
    "WPIW7Z8WzLShCLAjCjgcBBynA5TgcIK76LBlCUBgRmRwkIGtCBdFkX2q+ULWztkzTiWQ44v4EdoyiNuRAMZGfhC2mxbFyP7u5d0e"
    "yg+QmmgGNKsdR0M5oaatLa5bcGct9t2wrPuis2LZdpw7+FEFQRgcx23XNOU4ZqgC3bEtu4S3mw9SvhRYZ1JKTcMkB7K0BGxynNOy"
    "IXK2YoTcbNK0dNG9TBg+KZFslNSFPVYb/OZEE2CTZ1oMfmNjQ6abSdkvNi5Fd1UM0YJeIM0RL3ZhbLcDklwboyyybZvZe0gKMcMD"
    "I9Blc8vzW5eVmLzsma6S0JBspYMjEdBbNMfFmHtNC5gN61gIwgVqTmrSt7XGpMmklJrqhHm8LBTWozSpCq8Nfg5H90ExFMCA6UfE"
    "FasZMsJGeAar0IORPdNEwxYktBGXrZdsmqNIEaLKRmTMrEdBjMIcyIwlrgRlghWFuGuifbdyUva9ovayJDa9sxEcQGkwiQXk5VQK"
    "leDB7XKszIyVRDyb2zrmc5EqFSirw12SyHoAIdaNovfmtgsDRuri7ZLxLorauLuOc6QuclIVo2k2ofMxjqWHAObhwOcMwYBlnKXW"
    "u7yUpm1jEsm5x7oEjhbEmRURI2UQ3LazTOwC48jPI+NvxWW5a7KWbBcTBhHl4eDl9MA4804M1bkOZghUiwZJhq1xdOHS53qcjlTU"
    "zRmmu3Erkw9G4S4meunnRdfde58eE4h8vCjY4pBqHluIQxt1owHMpjl4AAUAwDKWGNDGBrQAAKAAUAGVgX2uxDNKCgIZatVNVQnK"
    "KdTmwIiLyHgCIiACIiACIiAP/9K1KIiACIiACIiAMY14V19ysldbZL7PmdZitq+WjUww4lMBzjiIywvdWVhREooDBKjSolJOWQqx"
    "OSc9Y9oRJOaa6BNSkS9NCQWuaahzTmYiCMpbo2LGyT7MgST4jBdFZjHBheQ1s5ANK4cQe00JysNcvBsOTLcsI8qy6mTbtZLhsKcA"
    "xuhE0Y/PaTQ7A7BRTIzs1Zs5AtCSiGFMS72xIbxlOGbmg4iMsLkUmolmhVwqEklROhBLTFWnp1KY2CUyN7s5qa2jPs90uAdbjRnM"
    "bDaMs1BdUZy+rpboocGzYNxlgxSbMkqiYjjAZuNWr3bkDq0GXgOYtnu0yTodp3KSkpZT9RzdpQztOa0kOgNGB7K5RccA2CjGFBiR"
    "osOXgML4kRzWQ2DGXEgNA0SsLkERWZ3EDKTaR2xQSM7dQ2O4K4+LddbAhRAWyEsQ+biDBUZUMHnp2kMOYrCS0vAlIEOWloYhwoTQ"
    "yGxuANaBQABaxZFnQLgLk4MtCh6mmnFgeBgMaZjENpXKaCabBoXfi2pa9lSMxaNsQ5dzIbRqNks55c57nBrWm/FMJIFVuZyLIoDm"
    "yMkrSBwOp1E0aHmybMI9w7FAvAh2tbcpOSkvbEvAZDnXOZCfAeXXkQNLgx98BWoBwjLyl2rJtqHPWZLTk2WQIsclmoy6mttcWlra"
    "4zULzJskzkZh1qVm1MNJNUGcEw61KszR6pCAZa8QXQXhtmLFYBAsshrXA4XkQw9wOZhIC4ZG6Cci2VaMzOwWQpuzgXOhNcS0jUYi"
    "sNThoQaHRSpkQwQ5vyW0GKmRDBDm/JbQbCRlpSi1uXurjRrAbaj5cQ5pkWDBjy5PHN0R7WnDlijw4HLX0bWt6YnLQbZ8CWiQpGKI"
    "d5Ee5sSJtW15oQC0HWqCqxU6DIjKXDZ7gKnQZEZS4bPcDY6hMC8CBdK2bjSG0eFtVOSkaY1o0c0wr3WKDBjJBXdsy03z1iwLUewN"
    "fFgalLAagGhNK6C8ktUKOBJ2ZVMMpapUcBHZi2I9InClQuhYtoPtSypSfiNDHTEMRC0YQCcoLzZS6WNHt82aYLRKPfFgwYwJvnRo"
    "LWue0jFShIGcUNqkiSZncdwgbVJEkzO47hH/07UoiIAIiIAIiIAIiIA61oSUC0ZKYkJlt9CmIbocQdMuBBVYbSkYtlWhM2ZMcdJS"
    "M+C44q3rqB2iKFWnUA5LUgJO7SPEaKCagwo2jS9Om1aHUmFJKqo6nAqBZoqw07OC3jIisNtq3UiejtvoVmw9TCuEGK7WYe6YXZ60"
    "dTPkIyLYVz85aJ16amiwblgtAGm4rSwKFoQ6XWqQYnBPRRtt1MpMzNnNiSrDFiS0eDMCENeeITw5zW7GmLYrp2vO8HFZE1K2bAj6"
    "nhiHGDIsJ8K+LHtdeAva0XxvSF7s9OS0lBEeaeIbC5rKmp1p7g1owZpISdnJaz5d83ORBCgwhVz3YsODdamlAuhaCUao0BGmNyYQ"
    "60JUaoVQEaY3I78PAizsS6CfsyFKysxCZKxzMTL48J0MMvWOaGa1S+cS7KqMC8eJY89PRJ6T2jxGNsx0xMSby0gOjRYrYsO8OXQN"
    "IwZtFt9n21JWoXslNSVhgE38J7BQ4qXzW10Fmz7Ys+03R2SUYRTLuvItARQ4aYxhGA4RgWs2KGsEkuEz5GL7WEeCmSGkBqXDJcjF"
    "7iCEao2TtKfsJkuIMaBEtq0TFj1ZR0KCH3xLgcWswwKHNXZnbNtKRmrRhl8adZaNnRAYmo2ikWCCGNN4GipD6CuE0XrwbrbCjxGQ"
    "mzBaYrryG90OI1jnVpehxYGk1FMa7svacjMz0xZ0GK10xLBpjQhWrQ4VadjoIlkyURQLklRUyVF0ssYSyZKggXJHcM3SFZJpMsal"
    "a9l2hLy8jHkoD4rZxsnBnoLQS5joLmOZFI2ABa7QzF35a0tVE/bLIsrMxIsaZD4DYcF7hEGomNFHBt6MIIwle5CtmzYxgCFGDtpM"
    "SJChUB1p8Kt+MWVelJa2rNnJaYnJaO18KUc9kZwrrDoevgjHgWSZJJUklcB+1l9OhGSZJJUklcH2ZfToRr1m2RPykex5eNCdfQ5G"
    "bbFcMLWRIrmODScVcJGguewLRbCsiWsKNAmIc2yCYLw6DEDA4AjX729psar1pq6CyJSFLxo0bBNND4DWte9720BqGtBNKEYaLtyU"
    "7AtGA2Zli4sdUC+a5hqDQ1DgCsoZJSqBK5fcRaUZSzSSoELl0UqLSjXrBthtn2NLWbFlpkTkrALHwzAiUL4bTgDr29INMBrhXnMs"
    "O1ZCxZG0Xx40WNLxmTkWUENhN9FedSgEC/JAecvKW9UCUGEJbtCREaoZFMinSLhpRk3PCREarhTIp5LSj//UtSiIgAiIgAiIgAiI"
    "gDBxKE8m2nBzyexkh6EepsUDZL842Zu0iwmmolpeFCOwJBeRvJanScQdDhKFtco0qlc5TxkPAC4mBTcePXd5UEZSmnISnGxbmpqS"
    "J1qWm3GmY2K1rhpgrQ5jgXco6HcULKGtDZrsiNVDa8/Ur6GYvm7MudYoEIta/aVK3hfhaHamZQkDGF7M5KS09LvlZuG2LCiCj2OF"
    "QQulCubseDAjS7ZesKOA2I173vBANRrznUocxbmjJSjXBMWmR6dTCJaMlKNcExaZHp1MOjPztuWTZM/PWnElohhwTtHEBj2HUh1l"
    "tb57q1JGJeXYcObsm2JGXmZR8q2ZkTKlznseIkWBrYdrJdQkOfjWwQrnLFgsdDbLkte5jnNfEiPF9DdfMNHOOI4V3ZiSlpp8F8xD"
    "D3QH6khE1q11CKimwJC8TYrNRKM7huGenpcuRkpgxUK1KJRncNwy5LJY0uRGiS0W0I9iWVZM42DAs6ejXjZoFz4gLIpexhBADXOL"
    "aB1SN1XbjQ4snblp2/Kgl8hNQxHaBhiSz4LA8bEt14Z2xW1OsazXyDbMdAaZZuuwsNAQ6+BGXWuGq5YclKQnTERjGgzJBjGlb8ho"
    "aK12AovEnKcBEZzJGNm0immHiTmOAiM7hkY2bSKaaWNNslzHCwYjCHMdaM85rgagg6lIIOWutBabKs2PajTSWnxOS03lBsXUkXUM"
    "U5+FpOxC3SXsOypSFLQpeWZDZJuc+A0Voxz6hxGHLqvt1kWa6QiWW+XaZWLfX8E1LTfOvnbHCTVCcyoChNMklPJpFKaGKME5lSJQ"
    "mmFKeTSKU0MXfhrlzZDbal9TY9U0sIVcdL52pKaNK6C9+xbUdasq+O6GIRZMRoIaDWohPLK12NKrM1YNkzkGDBmJcOZLi9g0LmuY"
    "KUo1zSCBQZq5pCzpOzJcSkhDEKE0ucGipwuNXGpJJJJqtjJmtnARmmC0u42s0LQZFCmC0HcREW4bR//VtSiIgAiIgAiIgAiIgDgm"
    "pmDJS0WbmHXkKAx0R7sxrQSTugVYrYtKJbNrTlrRRR03GdFpjo0nWW6DaBSrkw3WiWlBcrIv2vmQHzhGNkHG1me4jdM9RFBgxpmN"
    "DlpZhiRYrmshsbhLnONA0DPXK6VwqJBZIO5wspFJtFZKPgrfMh222WddI+zI7r1lowr1lcA1LDq5o0RUbos3X5Gca565mTteATEj"
    "wG8RMA1ALjUPbmNaTQ7DCtGl5iNKx4U1KvvIsF7YkN4xhzSC07qFrIlMVkahuM0OlmokmLH3VTMxL2YyFLPMJ81MQZfUjdeY2I8B"
    "xByjStDlLoW1ZcC56wZ+bs2JMMiuhsYXujRIhwvaC4Bz3UdQnCMKWTacnkgXLQ5iDE1BMAsL72hdAmYRDgaZYqKjNBXai2TblpyE"
    "1Z9rTMsWxWNEJ8vCe1we1wcHG+e4UqBgG6rc0SazUpJQwpiqza4hCt2SyUsjTLkZFOkKjDypiHZkpY9qRbMZPwIwk4m1kw6YAp0y"
    "YjqB1csYVxC0ZyHZkvZUzGftLk52Ta6JUh0WDFeCxxOXUVa7Ygr2Ytm3QWjZ87Z9pzEreTEB0KG6DDeCHOwXxvnuqKVwBYtS5fVj"
    "Fs2ZgxxCiyboYiuvaiNChkOvCK4MLag5WFeCmS7iQUEWRkbhyWNK34a1Ml3EgoIsjI3DksvuB0rSsGSddJIywiTLYc22ZiRmiZjA"
    "EsDS2lImAAuOAUXUtMWJL27OQbZmJmHBl5aXEC8ixxe4HAmsM68cGF2MraZmzHzFsSVpteGtlWRmOZTC7UoaAQcql6uF9hQ48/aE"
    "xNlsSBPwYUF0KmEBgeCSdjfYMxZU5zlyKUy2kltkjTDKmBnDIpTipyWRphrUePOmTsKUtp026HHdMmMyHfaneyHhg3+or19aEF1N"
    "FbPYMKShSV7IQ5iHDD3EtmTEv6mleOpLqaS883P2syXs50GchvnLMdEbCixYZLIkKILwB4Dgb6lMIOPPXsyAtJkDiKPgvjlxpqBr"
    "msvcoUcXGq8mKFJVCop0rirqclhzcZYoUlUKizbpqclhzcd1ERdA6AREQB//1rUoiIAIiIAIi6dqT7bLkI089he2E2paDQnDmoEs"
    "zgHaw0WnXd5IUjcpLulJZzZi1HtOo4IwiHXE+JmDMGM6a1C38ki6e2dsNhsg2bCiG91KXl8Yg4MDtR0boAnYrq2RkQ2xar9pdqWj"
    "BhtiG/e6HfxojicZJeGCuxNVpW2M5SCljpZOYk4KNjgTmxDQ4sWetafdGiGJNzk1EJNAXPiPccQAx5gAxKZMjfI51Q3tuW2xrrQe"
    "3aqDgcJdpx4ct5yyMWIZa2G5i4a565Zl9Z8HUkwRR81F1qKc44mjYNAWxIyYSBya5Zg3dVSFIIKRSOOJChxoboUVocx7S1zSKggi"
    "hBGWCoOyQMjiauejRbVseG6NZjzfOa0Evl67dIxlmY7KxHNU7UXy5jXAtcKgjCDmLY0ZpaFAY1MWy2KoUzBW64+62euRtMTktWLL"
    "xaNmpeuCIzNGY8ZR0DgKn+wroLLujkG2hZMYRYZ19uJ7HZbHDGCP1YFq10mRJc/bUR83ZrjZsw4m+1E0GE4nLLMo7lIWiTNyF1tw"
    "kybSs60YDC00vobntLxlB7CwtI2BJWhJrYSlRiHQsmbrloirE741lRzcvkmWhPTMGzbYk4WpnuDRGl3kNOVUtc3BoFSMuhKiUUJD"
    "lWzUzOBQIiLI8QREQAREQAREQB//2Q=="
)


def make_cover_png(report_type, name, date_str, site, note=None, dpi=200):
    """Full-page A4 cover image matching the CLC report template."""
    import base64
    from matplotlib.patches import Polygon
    from PIL import Image

    fig = plt.figure(figsize=(8.27, 11.69), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, COVER_W)
    ax.set_ylim(COVER_H, 0)
    ax.axis("off")
    pt = 8.27 * 72 / COVER_W
    for colour, pts in COVER_SHAPES:
        ax.add_patch(Polygon(pts, closed=True, facecolor=colour, edgecolor="none"))
    logo = Image.open(BytesIO(base64.b64decode(CLC_LOGO_JPG_B64)))
    lw = 125
    lh = lw * logo.height / logo.width
    ax.imshow(logo, extent=(437, 437 + lw, 20 + lh, 20), zorder=3)

    renderer = fig.canvas.get_renderer()

    def text(x, y, s_, size, max_w=None, **kw):
        t = ax.text(x, y, s_, fontsize=size * pt, family=COVER_FONTS, color="white", **kw)
        if max_w:                                   # shrink to fit (e.g. long school names)
            for _ in range(25):
                w = t.get_window_extent(renderer=renderer).width / fig.dpi / 8.27 * COVER_W
                if w <= max_w:
                    break
                t.set_fontsize(t.get_fontsize() * 0.95)
        return t

    words = report_type.upper().split()
    lines = [" ".join(words[:-1]), words[-1]] if len(words) > 1 else words
    y = 497
    for line in lines:
        text(20, y, line, 45, max_w=395, fontweight="bold", va="top")
        y += 50
    text(18, y + 10, "LEARNING AND BEHAVIOUR UNIT", 22, max_w=285, va="top")
    if note:
        import textwrap
        text(20, y + 42, "\n".join(textwrap.wrap(note, 62)[:3]), 10.5, max_w=405, va="top",
             style="italic", linespacing=1.35)
    for (label, value), ly in zip([("Student name:", name), ("Date:", date_str), ("Enrolled site:", site)],
                                  [732, 761, 787]):
        text(133, ly, label, 17, ha="right", va="center")
        text(141, ly - 4, value or "", 11.5, max_w=420, ha="left", va="center")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def make_hits_matrix_png(chosen, dpi=200):
    """The CLC 'High Impact Teaching Strategies' matrix (as on the report template), with the strategies and key
    elements the teacher chose highlighted. chosen = {strategy: [elements]}."""
    import textwrap
    from matplotlib.patches import Rectangle
    W = 7.1                                   # inches
    bar_w, strat_w = 0.30, 1.00
    el_x0 = bar_w + strat_w
    el_w_total = W - el_x0
    fs = 6.6                                  # font size (pt)
    char_in = fs * 0.50 / 72                  # approx. width of one character
    line_in = fs * 1.28 / 72
    head_h = 0.20
    rows = []
    for strat, elements in HITS_ELEMENTS.items():
        cw = el_w_total / len(elements)
        per_line = max(8, int((cw - 0.08) / char_in))
        wrapped = [textwrap.wrap(e, per_line) for e in elements]
        sw = textwrap.wrap(strat, 14)
        h = max(max(len(w) for w in wrapped), len(sw)) * line_in + 0.10
        rows.append((strat, elements, wrapped, sw, cw, h))
    H = head_h + sum(r[5] for r in rows)
    fig = plt.figure(figsize=(W, H), dpi=dpi)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(H, 0); ax.axis("off")
    edge = dict(edgecolor="#000000", linewidth=0.6)
    # header: "Key elements"
    ax.add_patch(Rectangle((el_x0, 0), el_w_total, head_h, facecolor="#A8D08D", **edge))
    ax.text(el_x0 + el_w_total / 2, head_h / 2, "Key elements", ha="center", va="center",
            fontsize=fs + 0.8, fontweight="bold", style="italic")
    # left bar
    ax.add_patch(Rectangle((0, head_h), bar_w, H - head_h, facecolor="#FFD966", **edge))
    ax.text(bar_w / 2, head_h + (H - head_h) / 2, "High Impact Teaching Strategies", rotation=90,
            ha="center", va="center", fontsize=fs + 1.6, fontweight="bold")
    y = head_h
    any_chosen = False
    for strat, elements, wrapped, sw, cw, h in rows:
        picked = chosen.get(strat)
        is_on = picked is not None
        ax.add_patch(Rectangle((bar_w, y), strat_w, h, facecolor="#FFD966" if is_on else "#FFF2CC", **edge))
        ax.text(bar_w + strat_w / 2, y + 0.05, "\n".join(sw), ha="center", va="top", fontsize=fs + 0.4,
                style="italic", fontweight="bold" if is_on else "normal", linespacing=1.15)
        for k, (el, lines) in enumerate(zip(elements, wrapped)):
            x = el_x0 + k * cw
            on = is_on and el in (picked or [])
            any_chosen = any_chosen or on
            ax.add_patch(Rectangle((x, y), cw, h, facecolor="#A8D08D" if on else "white",
                                   edgecolor="#000000", linewidth=1.6 if on else 0.6, zorder=2 if on else 1))
            ax.text(x + cw / 2, y + 0.05, "\n".join(lines), ha="center", va="top", fontsize=fs,
                    fontweight="bold" if on else "normal", linespacing=1.15, zorder=3,
                    color="#000000" if (on or not chosen) else "#555555")
        y += h
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=dpi, facecolor="white", bbox_inches="tight", pad_inches=0.02)
    plt.close(fig)
    return buf.getvalue()


# ── Report types ─────────────────────────────────────────────────────────────
# Review Report      — written about halfway through a normal placement
# Transition Report  — the completed report at the end; built on the Review
# Modified Report    — short placements: only the sections chosen are included
REPORT_TYPES = ["Review Report", "Transition Report", "Modified Report"]
REPORT_TYPE_HELP = {
    "Review Report": "Halfway through a normal placement. Saved, then built on through the placement.",
    "Transition Report": "The completed report at the end of placement — usually started from the Review Report.",
    "Modified Report": "Shorter placements. Has the cover page; choose only the sections to include.",
}
SECTIONS = [
    ("literacy", "Literacy Progress"),
    ("numeracy", "Numeracy Progress"),
    ("hits", "Pedagogical Strategies (HITS)"),
    ("restorative", "Restorative Practice & Relational Safety"),
    ("regulation", "Regulation Profile (Window of Tolerance)"),
    ("smartar", "Behaviour Progress: SMARTAR Goals"),
    ("voice", "Student Voice and Agency"),
    ("attendance", "Attendance"),
    ("summary", "Overall Progress Summary"),
]
SECTION_LABEL = dict(SECTIONS)
SECTION_LABEL["recommendations"] = "Transition Recommendations (Appendix)"
# Transition Recommendations are now an optional appendix (any report type), so Review = all sections
REVIEW_SECTIONS = [k for k, _ in SECTIONS]
VOICE_BLURB = ("Student voice and agency records the student's own views about their learning and their time at the "
               "Learning Centre — what they are proud of, what helps them, the choices they make about their learning, "
               "and what they would like their next school to know.")

# Saved reports live in the students/register project, next to wot_builder_reports
REPORTS_TABLE = "student_reports"
REPORTS_TABLE_SQL = """create table if not exists student_reports (
    id                  uuid primary key default gen_random_uuid(),
    student_register_id text,
    student_initials    text not null,
    report_type         text not null,
    sections            jsonb,
    data                jsonb not null default '{}'::jsonb,
    created_by          text,
    updated_by          text,
    created_at          timestamptz default now(),
    updated_at          timestamptz default now()
);
create index if not exists student_reports_student_idx on student_reports (student_register_id);
alter table student_reports disable row level security;"""

# Session keys (without the tr_ prefix) that make up a saved report. Never the
# printout name, never caches.
SAVED_KEY_RE = re.compile(
    r"^(report_type|sections|report_date|pstart|pend|teacher|school|vocab_(type|pre|post|summary)|numeracy|"
    r"biin_c_\d+|hits|hits_el_\d+|hits_c_\d+|rp|rp_comments|rp_c_\d+|wot|wotz_\w+|regulation|goal_sel|goal_known|"
    r"g_current_.+|days_att|days_tot|att_comment|att_table|att_table_on|summary|recs|app_recs|apps|app_title_\w+|"
    r"app_text_\w+|uploads|voice_text|voice_files|lens|sm_override|finalised)$")
DATE_KEYS = ("report_date", "pstart", "pend")
EDITORS = ["sw", "biin0", "biin1", "biin2", "biin3"]


# ══════════════════════════════════════════════════════════════════════════════
# DATA — STUDENT REGISTER
# ══════════════════════════════════════════════════════════════════════════════
REGISTER_ERROR = ""


def load_register():
    """Current students from the register (same list the WoT Builder reads).
    Students who've left (status 'archived') are hidden; a missing status is
    kept, so a data gap never hides an enrolled student. Returns None if the
    register can't be reached (the reason is left in REGISTER_ERROR). A good
    result is kept for 2 minutes; a failure is retried on the next run."""
    global REGISTER_ERROR
    cached = st.session_state.get("_tr_register_cache")
    if cached and (datetime.now() - cached[0]).total_seconds() < 120:
        return cached[1]
    c = _students_client()
    if c is None:
        REGISTER_ERROR = ("No database connection to the Student Register project — check the Render environment "
                          "variables (SUPABASE_URL_STUDENTS / SUPABASE_KEY_STUDENTS) or that archive_utils.py is deployed.")
        return None
    try:
        rows = c.table("student_directory").select("*").execute().data or []
    except Exception as e:
        REGISTER_ERROR = f"Couldn't read the student_directory table: {e}"
        return None
    out = []
    for r in rows:
        ini = str(r.get("initials") or "").strip()
        if not ini:
            continue
        if str(r.get("status") or "").strip().lower() == "archived":
            continue
        out.append({"id": r.get("id"), "initials": ini, "program": r.get("program") or ""})
    out = sorted(out, key=lambda r: (r["initials"].upper()))
    st.session_state["_tr_register_cache"] = (datetime.now(), out)
    return out


# ══════════════════════════════════════════════════════════════════════════════
# DATA — WINDOW OF TOLERANCE
# ══════════════════════════════════════════════════════════════════════════════
def _normalise_wot(data):
    out = {}
    data = data if isinstance(data, dict) else {}
    for z in WOT_ZONES:
        zd = data.get(z["id"]) or {}
        out[z["id"]] = {}
        for col, _ in WOT_COLS:
            items = zd.get(col) or []
            texts = []
            for it in items:
                t = it.get("text") if isinstance(it, dict) else it
                t = str(t or "").strip()
                if t:
                    texts.append(t)
            out[z["id"]][col] = texts
    return out


def load_wot_report(student):
    """Latest WoT Builder report for this student — by register id, then by
    initials as a fallback. Returns dict or None."""
    c = _students_client()
    if c is None:
        return None
    rows = []
    try:
        rows = (c.table("wot_builder_reports").select("*")
                .eq("student_register_id", student["id"])
                .order("updated_at", desc=True).limit(1).execute().data or [])
    except Exception:
        rows = []
    if not rows:
        try:
            rows = (c.table("wot_builder_reports").select("*")
                    .eq("student_initials", student["initials"])
                    .order("updated_at", desc=True).limit(1).execute().data or [])
        except Exception:
            rows = []
    if not rows:
        return None
    r = rows[0]
    return {
        "status": r.get("status") or "draft",
        "updated_at": r.get("updated_at"),
        "updated_by": r.get("updated_by") or "",
        "data": _normalise_wot(r.get("data")),
    }


def wot_has_content(wot, zone_id):
    return any(wot["data"][zone_id][c] for c, _ in WOT_COLS)


def _lc(s):
    return s[:1].lower() + s[1:] if s else s


def _join(items):
    items = [_lc(i) for i in items]
    if len(items) < 2:
        return "".join(items)
    return "; ".join(items[:-1]) + " and " + items[-1]


def draft_wot_summary(wot, zones_on, who):
    """Starting paragraph built from the pulled WoT phrases — staff edit it after."""
    d = wot["data"]
    on = lambda z: zones_on.get(z, False)
    get = lambda z, c: d[z][c] if on(z) else []
    p = []
    if get("wot", "context"):
        p.append(f"{who} is most settled and ready to learn during {_join(get('wot', 'context')[:2])}.")
    if get("wot", "interventions"):
        p.append(f"What keeps {who} in their window: {_join(get('wot', 'interventions'))}.")
    trig = (get("copingup", "context") + get("hyper", "context"))[:3]
    if trig:
        p.append(f"Common triggers include {_join(trig)}.")
    warn = (get("copingup", "behaviour") + get("copingdown", "behaviour"))[:4]
    if warn:
        p.append(f"Early warning signs to watch for are {_join(warn)}.")
    early = (get("copingup", "interventions") + get("copingdown", "interventions"))[:3]
    if early:
        p.append(f"Stepping in early works best: {_join(early)}.")
    if get("hyper", "interventions"):
        p.append(f"If {who} becomes highly dysregulated, staff should {_join(get('hyper', 'interventions'))}.")
    if get("hypo", "interventions"):
        p.append(f"When shut down, {_join(get('hypo', 'interventions'))}.")
    return " ".join(p).replace("..", ".")




# ══════════════════════════════════════════════════════════════════════════════
# UPLOADS (Student Voice + Appendices) — photos, PDFs, Word documents, text
# Stored inside the saved report as compressed JPEG pages / plain text, so a
# reopened report keeps them. Photos are shrunk to 1600px to keep saves small.
# ══════════════════════════════════════════════════════════════════════════════
UPLOAD_TYPES = ["png", "jpg", "jpeg", "gif", "webp", "bmp", "heic", "heif", "pdf", "docx", "txt", "md"]
UPLOAD_MAX_MB = 15
UPLOAD_MAX_PDF_PAGES = 20


def _img_b64(img):
    from PIL import Image, ImageOps
    try:
        img = ImageOps.exif_transpose(img)          # phone photos come in sideways otherwise
    except Exception:
        pass
    if img.mode in ("RGBA", "LA", "P"):
        img = img.convert("RGBA")
        bg = Image.new("RGB", img.size, (255, 255, 255))
        bg.paste(img, mask=img.split()[-1])
        img = bg
    elif img.mode != "RGB":
        img = img.convert("RGB")
    img.thumbnail((1600, 1600))
    buf = BytesIO()
    img.save(buf, "JPEG", quality=82, optimize=True)
    return base64.b64encode(buf.getvalue()).decode()


def process_upload(name, data):
    """File bytes -> {"kind", "pages": [jpeg b64], "text"}. Raises ValueError with a staff-friendly message."""
    from PIL import Image
    ext = (name.rsplit(".", 1)[-1] if "." in name else "").lower()
    if len(data) > UPLOAD_MAX_MB * 1024 * 1024:
        raise ValueError(f"{name} is bigger than {UPLOAD_MAX_MB} MB — please use a smaller file.")
    if ext in ("heic", "heif"):
        try:
            import pillow_heif
            pillow_heif.register_heif_opener()
        except Exception:
            raise ValueError("iPhone HEIC photos can't be read here. On the iPhone choose Settings → Camera → Formats → "
                             "Most Compatible, or share/save the photo as a JPG, then upload again.")
    if ext in ("png", "jpg", "jpeg", "gif", "webp", "bmp", "heic", "heif"):
        try:
            return {"kind": "image", "pages": [_img_b64(Image.open(BytesIO(data)))], "text": ""}
        except Exception:
            raise ValueError(f"Couldn't open {name} as a picture.")
    if ext == "pdf":
        pages = []
        try:
            import pypdfium2 as pdfium
            pdf = pdfium.PdfDocument(data)
            for i in range(min(len(pdf), UPLOAD_MAX_PDF_PAGES)):
                pages.append(_img_b64(pdf[i].render(scale=150 / 72).to_pil()))
        except ImportError:
            try:
                import fitz
                pdf = fitz.open(stream=data, filetype="pdf")
                for i in range(min(len(pdf), UPLOAD_MAX_PDF_PAGES)):
                    pix = pdf[i].get_pixmap(dpi=150)
                    pages.append(_img_b64(Image.open(BytesIO(pix.tobytes("png")))))
            except ImportError:
                pages = []
        except Exception:
            raise ValueError(f"Couldn't read {name} — is it a password-protected PDF?")
        if pages:
            return {"kind": "pdf", "pages": pages, "text": ""}
        try:                                        # no PDF renderer installed: keep the text at least
            from pypdf import PdfReader
            text = "\n\n".join((p.extract_text() or "").strip() for p in PdfReader(BytesIO(data)).pages)
        except Exception:
            text = ""
        if not text.strip():
            raise ValueError("PDF pages can't be shown on this server yet (add pypdfium2 to requirements.txt). "
                             "Upload a photo/screenshot of the page instead.")
        return {"kind": "pdf", "pages": [], "text": text.strip()}
    if ext == "docx":
        from docx import Document as _Doc
        try:
            d_ = _Doc(BytesIO(data))
        except Exception:
            raise ValueError(f"Couldn't open {name} as a Word document.")
        lines = [p.text for p in d_.paragraphs]
        for tb in d_.tables:
            for row in tb.rows:
                cells = [c.text.strip() for c in row.cells]
                lines.append(" | ".join(dict.fromkeys(c for c in cells if c)))
        pages = []
        for rel in d_.part.rels.values():
            if "image" in rel.reltype and not rel.is_external:
                try:
                    pages.append(_img_b64(Image.open(BytesIO(rel.target_part.blob))))
                except Exception:
                    pass
        text = re.sub(r"\n{3,}", "\n\n", "\n".join(lines)).strip()
        return {"kind": "docx", "pages": pages, "text": text}
    if ext in ("txt", "md"):
        return {"kind": "text", "pages": [], "text": data.decode("utf-8", errors="replace").strip()}
    raise ValueError(f"{name}: that file type can't be added. Use a photo, PDF, Word document or text file.")


def add_upload(list_key, prefix, title_required):
    """Form-submit callback: read the uploaded file + title into the saved list."""
    ver = st.session_state.get(f"_tr_upl_ver_{prefix}", 0)
    f_ = st.session_state.get(f"tr_upl_{prefix}_{ver}")
    title = (st.session_state.get(f"tr_uplt_{prefix}_{ver}") or "").strip()
    st.session_state[f"tr_upl_msg_{prefix}"] = ""
    if f_ is None:
        st.session_state[f"tr_upl_msg_{prefix}"] = "Choose a file to upload first."
        return
    if title_required and not title:
        st.session_state[f"tr_upl_msg_{prefix}"] = "Give this upload a title — it becomes the appendix heading."
        return
    try:
        item = process_upload(f_.name, f_.getvalue())
    except ValueError as e:
        st.session_state[f"tr_upl_msg_{prefix}"] = str(e)
        return
    item.update(id=uuid.uuid4().hex[:8], title=title, name=f_.name)
    st.session_state[list_key] = list(st.session_state.get(list_key) or []) + [item]
    st.session_state[f"_tr_upl_ver_{prefix}"] = ver + 1          # clears the uploader + title


def remove_upload(list_key, item_id):
    st.session_state[list_key] = [x for x in (st.session_state.get(list_key) or []) if x.get("id") != item_id]


def move_upload(list_key, item_id, step):
    items = list(st.session_state.get(list_key) or [])
    i = next((n for n, x in enumerate(items) if x.get("id") == item_id), None)
    if i is None or not (0 <= i + step < len(items)):
        return
    items[i], items[i + step] = items[i + step], items[i]
    st.session_state[list_key] = items


def upload_panel(list_key, prefix, title_required, title_label, help_text):
    """Upload form + the list of what's been added (thumbnail, title, remove/reorder)."""
    items = st.session_state.get(list_key) or []
    for n_, it in enumerate(items):
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 5, 2])
            if it.get("pages"):
                c1.image(base64.b64decode(it["pages"][0]), use_container_width=True)
            else:
                c1.markdown("📄")
            pg = len(it.get("pages") or [])
            c2.markdown(f"**{it.get('title') or '(no title)'}**  \n"
                        f"<span style='color:#666;font-size:0.85rem'>{it.get('name', '')}"
                        f"{f' · {pg} page' + ('s' if pg != 1 else '') if pg else ''}"
                        f"{' · text' if it.get('text') else ''}</span>", unsafe_allow_html=True)
            b1, b2, b3 = c3.columns(3)
            b1.button("↑", key=f"tr_upup_{prefix}_{it['id']}", on_click=move_upload, args=(list_key, it["id"], -1),
                      disabled=n_ == 0, help="Move up")
            b2.button("↓", key=f"tr_updn_{prefix}_{it['id']}", on_click=move_upload, args=(list_key, it["id"], 1),
                      disabled=n_ == len(items) - 1, help="Move down")
            b3.button("✕", key=f"tr_uprm_{prefix}_{it['id']}", on_click=remove_upload, args=(list_key, it["id"]),
                      help="Remove")
    ver = st.session_state.get(f"_tr_upl_ver_{prefix}", 0)
    with st.form(f"tr_uplform_{prefix}_{ver}", clear_on_submit=False, border=True):
        st.text_input(title_label, key=f"tr_uplt_{prefix}_{ver}")
        st.file_uploader("File", type=UPLOAD_TYPES, key=f"tr_upl_{prefix}_{ver}", help=help_text)
        st.form_submit_button("➕ Add upload", on_click=add_upload, args=(list_key, prefix, title_required))
    if st.session_state.get(f"tr_upl_msg_{prefix}"):
        st.warning(st.session_state[f"tr_upl_msg_{prefix}"])


# ── text appendices ──────────────────────────────────────────────────────────
def add_text_appendix():
    st.session_state["tr_apps"] = list(st.session_state.get("tr_apps") or []) + [uuid.uuid4().hex[:8]]


def remove_text_appendix(aid):
    st.session_state["tr_apps"] = [x for x in (st.session_state.get("tr_apps") or []) if x != aid]
    for k in (f"tr_app_title_{aid}", f"tr_app_text_{aid}"):
        st.session_state.pop(k, None)


# ══════════════════════════════════════════════════════════════════════════════
# ATTENDANCE TABLE — the Behaviour Support Tool's "Attendance table for reports"
# (Term-week × Mon–Fri), rebuilt from the same records with the same rules.
# ══════════════════════════════════════════════════════════════════════════════
BST_DAYS_FULL = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday"]
BST_SESSION_LABEL = {"Morning": "AM", "Middle": "Mid", "Afternoon": "PM"}
BST_SESSION_TIMES = {"Morning": ("9:00", "11:00"), "Middle": ("11:00", "13:30"), "Afternoon": ("13:30", "14:45")}
BST_CI_REASON = "C.I. (critical incident)"
BST_TERM_STARTS = {  # SA public school terms (Monday of week 1) — same as the Behaviour Support Tool
    2026: [date(2026, 2, 2), date(2026, 4, 27), date(2026, 7, 20), date(2026, 10, 12)],
}
BST_LEGACY_REASONS = {"Day end to avoid escalation": "Day end: avoid potential escalation",
                      "Day end: needs reset, negotiated time": "Day end: needs reset"}
ATT_DAY_COLOURS = {   # status: (fill, label for the key)
    "attended":   ("70AD47", "Attended"),
    "absent":     ("E06666", "Absent"),
    "transition": ("8E7CC3", "Transition (at the enrolled school)"),
    "noschool":   ("D9D9D9", "No school"),
}


def _att_cell_status(cell):
    """Status for a table cell; older saved tables stored text lines instead."""
    if cell.get("status"):
        return cell["status"]
    txt = " ".join(t for t, _ in cell.get("lines") or [])
    return "noschool" if "No school" in txt else "absent" if "Absent" in txt else "attended"


def transition_days(initials):
    """Dates the Transition Timetables tool has the student away from CLC (same rule as the Behaviour Support
    Tool's 'before vs after starting to split time between sites'). Empty set if that tool isn't deployed."""
    try:
        import transition_utils as tu
        rows = (tu.get_students_client().table(tu.TABLE_TIMETABLES).select("*")
                .eq("student_initials", initials).order("updated_at", desc=True).execute().data or [])
    except Exception:
        return set()
    if not rows:
        return set()
    tt = None
    for want in ("published", "active", "draft", "complete"):
        tt = next((r for r in rows if r.get("status") == want), None)
        if tt:
            break
    tt = tt or rows[0]
    try:
        view = tu.live_view(tt) if tu.is_live(tt) else tt
    except Exception:
        view = tt
    weeks = view.get("weeks")
    if isinstance(weeks, str):
        try:
            weeks = json.loads(weeks)
        except Exception:
            weeks = []
    if isinstance(weeks, dict):
        weeks = list(weeks.values())
    out = set()
    for wk in weeks or []:
        for d_ in (wk.get("days") or []) if isinstance(wk, dict) else []:
            loc = d_.get("loc") if isinstance(d_, dict) else None
            dd = _d(d_.get("date")) if isinstance(d_, dict) else None
            if loc and loc != "CLC" and dd:
                out.add(dd)
    return out


ATT_TABLE_STYLE = {"ci": "B91C1C", "event": "B45309", "absent": "166534", "time": "111827", "note": "374151", "muted": "6B7280"}


def _bst_att_state(row):
    """Attendance model exactly as the Behaviour Support Tool builds it (legacy fields converted)."""
    state = {"schedule": list(row.get("schedule") or []), "exceptions": [dict(e) for e in (row.get("exceptions") or [])
                                                                         if isinstance(e, dict) and isinstance(e.get("date"), str)]}
    if not state["schedule"]:
        pt_days = row.get("pt_days") or BST_DAYS_FULL
        sess = set()
        for o in row.get("pt_sessions") or ["Full day"]:
            sess |= {"Full day": set(BST_ATT_SESSIONS), "Morning only": {"Morning"}, "Middle of day only": {"Middle"},
                     "Afternoon only": {"Afternoon"}, "Morning + Middle": {"Morning", "Middle"},
                     "Middle + Afternoon": {"Middle", "Afternoon"}}.get(o, set())
        sess = [x for x in BST_ATT_SESSIONS if x in sess] or list(BST_ATT_SESSIONS)
        days_map = {BST_ATT_DAYS[i]: (sess if BST_DAYS_FULL[i] in pt_days else []) for i in range(5)}
        if any(v != list(BST_ATT_SESSIONS) for v in days_map.values()):
            state["schedule"] = [{"from": "2000-01-01", "days": days_map}]
    have = {e["date"] for e in state["exceptions"]}
    for d_ in row.get("absent_dates") or []:
        if isinstance(d_, str) and d_ not in have:
            state["exceptions"].append({"date": d_, "type": "Absent", "sessions": [], "reason": "", "note": ""})
    for e in state["exceptions"]:
        if e.get("reason") in BST_LEGACY_REASONS:
            e["reason"] = BST_LEGACY_REASONS[e["reason"]]
    return state


def _bst_version(state, d):
    vers = sorted(state.get("schedule") or [], key=lambda v: v.get("from", ""))
    if not vers:
        return None
    chosen = vers[0]
    for v in vers:
        if v.get("from", "") <= d.isoformat():
            chosen = v
    return chosen


def _bst_att_day(state, d):
    exc = next((e for e in state["exceptions"] if e.get("date") == d.isoformat()), None)
    ver = _bst_version(state, d)
    dn = BST_ATT_DAYS[d.weekday()] if d.weekday() < 5 else None
    planned = (list(BST_ATT_SESSIONS) if ver is None else list((ver.get("days") or {}).get(dn, []))) if dn else []
    if exc and exc.get("type") == "No school":
        return {"planned": [], "actual": [], "exc": exc, "no_school": True, "expected_start": ""}
    actual = planned
    if exc:
        actual = [] if exc.get("type") == "Absent" else [x for x in BST_ATT_SESSIONS if x in (exc.get("sessions") or [])]
    start_ = ((ver.get("starts") or {}).get(dn, "") if ver and dn else "")
    return {"planned": planned, "actual": actual, "exc": exc, "no_school": False, "expected_start": start_}


def _bst_clock(hhmm):
    m = re.match(r"^\s*(\d{1,2}):(\d{2})\s*(am|pm)?\s*$", hhmm or "", re.I)
    if not m:
        return None
    h, mi, suf = int(m.group(1)), m.group(2), (m.group(3) or "").lower()
    if not suf:
        suf = "pm" if (h >= 12 or h <= 6) else "am"
    return (f"{h - 12 if h > 12 else h}" + ("" if mi == "00" else f":{mi}"), suf)


def _bst_range_text(a_, b_):
    a, b = _bst_clock(a_), _bst_clock(b_)
    if not a or not b:
        return f"{a_}-{b_}"
    return f"{a[0]}{a[1] if a[1] == 'pm' else ''}-{b[0]}{b[1]}"


def _bst_term_week(d):
    for yr, starts in BST_TERM_STARTS.items():
        if d.year != yr:
            continue
        for i in range(len(starts) - 1, -1, -1):
            if d >= starts[i]:
                wk = (d - starts[i]).days // 7 + 1
                return (f"T{i + 1}", wk) if wk <= 10 else None
    return None


def _bst_day_times(day, exc):
    act = [x for x in BST_ATT_SESSIONS if x in day["actual"]]
    if not act:
        return ""
    exc = exc or {}
    start_ = exc.get("arrived") or day.get("expected_start") or BST_SESSION_TIMES[act[0]][0]
    end_ = exc.get("left") or BST_SESSION_TIMES[act[-1]][1]
    full = len(act) == len(BST_ATT_SESSIONS)
    contiguous = BST_ATT_SESSIONS.index(act[-1]) - BST_ATT_SESSIONS.index(act[0]) == len(act) - 1
    if full or (contiguous and (exc.get("left") or exc.get("arrived"))):
        return _bst_range_text(start_, end_)
    return " + ".join(BST_SESSION_LABEL[x] for x in act)


def _bst_cell_lines(r):
    L = []
    if r["no_school"]:
        return [["No school", "muted"]]
    if r["late_min"] and r["event"] != "Late arrival":
        L.append([f"Late arrival ({r['late_min']} min)", "event"])
    if r["event"] == "CI":
        L.append(["CI", "ci"])
        if r["ci_description"] or r["note"]:
            L.append([r["ci_description"] or r["note"], "note"])
    elif r["event"]:
        L.append([r["event"] + (f" ({r['late_min']} min)" if r["event"] == "Late arrival" and r["late_min"] else ""),
                  "ci" if r["event"] == "Re-entry meeting" else "event"])
        if r["note"]:
            L.append([r["note"], "note"])
    if r["status"] == "Absent":
        L.append(["Absent", "absent"])
        if r["note"] and not r["event"]:
            L.append([r["note"], "note"])
    elif r["times"]:
        L.append([r["times"], "time"])
    if r["event"] == "CI" and r["note"] and r["ci_description"]:
        L.append([r["note"], "note"])
    if r["quick_incidents"]:
        L.append([f"{r['quick_incidents']} incident(s) logged", "muted"])
    return L


def _scrub_names(text, stu, initials):
    out = str(text or "")
    for nm in {str(stu.get("first_name") or ""), str(stu.get("last_name") or "")}:
        nm = nm.strip()
        if len(nm) > 1 and nm != "-" and nm.upper() != initials.upper():
            out = re.sub(rf"(?<![A-Za-z]){re.escape(nm)}(?![A-Za-z])", initials, out, flags=re.I)
    return out


def bst_attendance_table(initials, start, end):
    """[{week_label, days: [cell or None]*5}] for the report, plus counts. Returns (table, problem)."""
    if _smartar_client() is None:
        return None, "Can't reach the Behaviour Support Tool's database right now."
    stu = bst_find_student(initials)
    if not stu:
        return None, f"No student filed as {initials} in the Behaviour Support Tool."
    sid = str(stu["id"])
    rows = _bst_rows("student_attendance", sid)
    if not rows:
        return None, f"No attendance has been recorded for {initials} in the Behaviour Support Tool."
    state = _bst_att_state(rows[0])
    quick, crit = defaultdict(int), defaultdict(list)
    for r in _bst_rows("incidents", sid):
        d_ = _d(r.get("date"))
        if d_:
            quick[d_] += 1
    for r in _bst_rows("critical_incidents", sid):
        d_ = _d(r.get("date") or r.get("incident_date") or r.get("created_at"))
        if d_:
            desc = " / ".join(_flat(r.get("primary_behaviour"))) or "Critical incident"
            crit[d_].append(re.sub(r"\s+", " ", desc).strip()[:110])
    # The WHOLE placement: from the placement start recorded in the Behaviour Support Tool (or the first
    # attendance/incident record), to today or the placement end (incl. extensions) if that has passed.
    today = date.today()
    rec_dates = [x for x in [_d(e.get("date")) for e in state["exceptions"]] + list(quick) + list(crit) if x]
    starts = [x for x in (_d(stu.get("placement_start")),) if x] or ([min(rec_dates)] if rec_dates else [])
    if start and start < today:                       # sidebar start counts if staff set one earlier
        starts.append(start)
    if not starts:
        return None, (f"{initials}'s placement start date isn't recorded in the Behaviour Support Tool — set the "
                      "Placement Start Date in the sidebar, then pull again.")
    start = min(starts)
    ends = [x for x in [_d(stu.get("placement_end"))] + [_d(e.get("to_date")) for e in _bst_rows("placement_extensions", sid)]
            + ([end] if end and end > start and end != today else []) if x]
    end = min(today, max(ends)) if ends and max(ends) < today else today
    if start > end:
        return None, "The placement hasn't started yet, so there's no attendance to show."
    weeks, counts = {}, {"attended": 0, "school_days": 0, "absent": 0, "transition": 0}
    trans = transition_days(initials)
    d_ = start - timedelta(days=start.weekday())
    while d_ <= end:
        in_term = (d_.year not in BST_TERM_STARTS) or _bst_term_week(d_) is not None     # skip school holidays
        if d_.weekday() < 5 and d_ >= start and in_term:
            day = _bst_att_day(state, d_)
            exc = day["exc"] or {}
            reason, note = exc.get("reason", "") or "", _scrub_names(exc.get("note", ""), stu, initials)
            cis = crit.get(d_, [])
            status = "No school" if day["no_school"] else ("Absent" if exc.get("type") == "Absent" else
                     ("Attended" if day["actual"] else ""))
            event = ""
            if reason == BST_CI_REASON or cis:
                event = "CI"
            elif reason == "Re-entry meeting":
                event = "Re-entry meeting"
            elif reason in BST_DAYEND_REASONS:
                event = reason
            elif exc.get("type") == "Arrived late" or exc.get("late_min"):
                event = "Late arrival"
            rec = {"no_school": day["no_school"], "status": status, "event": event, "note": note,
                   "times": "" if day["no_school"] else _bst_day_times(day, exc),
                   "ci_description": _scrub_names("; ".join(c for c in cis if c), stu, initials),
                   "late_min": int(_num(exc.get("late_min"))), "quick_incidents": quick.get(d_, 0)}
            if day["no_school"]:
                cell_status = "noschool"
            elif d_ in trans:
                cell_status = "transition"
            elif status == "Absent":
                cell_status = "absent"
            else:
                cell_status = "attended"       # includes part-time days off — shown as attended
            counts["transition"] += cell_status == "transition"
            if cell_status in ("attended", "absent"):
                counts["school_days"] += 1
                counts["attended"] += cell_status == "attended"
                counts["absent"] += cell_status == "absent"
            ws = d_ - timedelta(days=d_.weekday())
            tw = _bst_term_week(ws)
            wk = weeks.setdefault(ws.isoformat(), {"week_label": f"{tw[0]} Wk {tw[1]}" if tw else f"Wk of {ws.strftime('%-d %b')}",
                                                   "days": [None] * 5})
            wk["days"][d_.weekday()] = {"label": d_.strftime("%-d %b"), "status": cell_status}
        d_ += timedelta(days=1)
    if not weeks:
        return None, "No school days in the placement dates."
    return {"weeks": [weeks[k] for k in sorted(weeks)], "from": start.isoformat(), "to": end.isoformat(),
            "counts": counts}, None


def pull_attendance_table(initials, start, end):
    tbl, problem = bst_attendance_table(initials, start, end)
    if problem:
        st.session_state["tr_att_table_msg"] = problem
        return
    st.session_state["tr_att_table"] = tbl
    st.session_state["tr_att_table_on"] = True
    st.session_state["tr_att_table_msg"] = ""
    if not st.session_state.get("tr_days_att") and tbl["counts"]["school_days"]:
        st.session_state["tr_days_att"] = tbl["counts"]["attended"]
        st.session_state["tr_days_tot"] = tbl["counts"]["school_days"]


def att_table_key_html():
    return "".join(f"<span style='display:inline-block;margin:4px 12px 0 0;font-size:0.8rem'>"
                   f"<span style='display:inline-block;width:14px;height:14px;vertical-align:middle;margin-right:4px;"
                   f"background:#{c};border:1px solid #777'></span>{lbl}</span>" for c, lbl in ATT_DAY_COLOURS.values())


def att_table_html(tbl):
    import html as _h
    out = ["<table style='width:100%;border-collapse:collapse;font-size:0.8rem;table-layout:fixed'><tr>" +
           "".join(f"<th style='background:#323E4F;color:#fff;border:1px solid #444;padding:5px'>{h}</th>"
                   for h in ["Week"] + BST_DAYS_FULL) + "</tr>"]
    for wk in tbl["weeks"]:
        row = (f"<tr><td style='background:#EEF2EC;border:1px solid #444;padding:5px;text-align:center;font-weight:600'>"
               f"{_h.escape(wk['week_label'])}</td>")
        for cell in wk["days"]:
            if not cell:
                row += "<td style='border:1px solid #444;background:#f3f4f6'></td>"
                continue
            fill = ATT_DAY_COLOURS.get(_att_cell_status(cell), ATT_DAY_COLOURS["attended"])[0]
            fg = "#fff" if _att_cell_status(cell) in ("attended", "absent", "transition") else "#333"
            row += (f"<td style='border:1px solid #444;padding:5px;text-align:center;background:#{fill};color:{fg};"
                    f"font-weight:600'>{_h.escape(cell['label'])}</td>")
        out.append(row + "</tr>")
    return "".join(out) + "</table>" + att_table_key_html()


def pull_student_voice(initials):
    """Append the student voice recorded in the Behaviour Support support plan / starting profile."""
    stu = bst_find_student(initials) if _smartar_client() is not None else None
    if not stu:
        st.session_state["tr_voice_msg"] = f"No student filed as {initials} in the Behaviour Support Tool."
        return
    bits = []
    plan = (_bst_rows("support_plans", str(stu["id"])) or [{}])[0]
    if str(plan.get("student_voice") or "").strip():
        bits.append(str(plan["student_voice"]).strip())
    prof = ((_bst_rows("starting_profiles", str(stu["id"])) or [{}])[0].get("profile") or {})
    for k in ("student_voice", "what_student_says"):
        if str(prof.get(k) or "").strip():
            bits.append(str(prof[k]).strip())
    if not bits:
        st.session_state["tr_voice_msg"] = f"No student voice is recorded in {initials}'s Behaviour Support plan."
        return
    _append("tr_voice_text", _scrub_names("\n\n".join(dict.fromkeys(bits)), stu, initials))
    st.session_state["tr_voice_msg"] = ""

# ══════════════════════════════════════════════════════════════════════════════
# BEHAVIOUR SUPPORT TOOL DATA + AI DRAFTS
# Reads the Behaviour Support Tool's tables (same Supabase project as the
# SMARTAR Goal Builder) for the student matched by register initials, and asks
# Groq to draft text for four sections. Drafts are only suggestions: they're shown
# in italics and nothing goes into the report until staff Add (or Edit, then Add).
# Only initials and aggregated / staff-authored information are sent — no incident
# free-text descriptions, no names.
# ══════════════════════════════════════════════════════════════════════════════
BST_ATT_SESSIONS = ["Morning", "Middle", "Afternoon"]
BST_ATT_DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri"]
BST_DAYEND_REASONS = ("Day end: avoid potential escalation", "Day end: needs reset", "Day end: negotiated",
                      "Day end to avoid escalation", "Day end: needs reset, negotiated time")
BST_PLAN_FIELDS = ["strengths", "interests", "purpose", "early_warning_signs", "proactive_strategies_additional",
                   "teaching_strategies", "response_early_signs", "response_escalation", "post_incident_repair",
                   "reinforcement", "adjustments_supports", "short_term_goals", "student_voice", "recovery_time"]


def _bst_code(row):
    """Register code for a Behaviour Support student — same rule the tool uses for the Document Archive."""
    raw = (row.get("name") or "").strip()
    if raw and " " not in raw and raw.replace("-", "").isalpha() and 2 <= len(raw) <= 4:
        return raw.upper()
    first, last = (row.get("first_name") or "").strip(), (row.get("last_name") or "").strip()
    parts = [p for p in (f"{first} {last}".split() if first else raw.split()) if p and p != "-"]
    return "".join(p[0].upper() for p in parts[:2])


def bst_find_student(initials):
    """Behaviour Support student for a register code. Exact code first; then a student entered by full name whose
    name parts give the code (e.g. Lily Nora Martin → LNM); then a 2-letter code that is the start of this code
    (LN → LNM) when only one student fits — so longer, de-clashed register codes still match."""
    c = _smartar_client()
    if c is None:
        return None
    try:
        rows = c.table("students").select("*").execute().data or []
    except Exception:
        return None
    code = initials.upper()
    rows.sort(key=lambda r: bool(r.get("archived")))          # current placement first

    def all_parts(r):
        name = " ".join(x for x in [r.get("first_name") or "", r.get("last_name") or ""] if x and x != "-") or (r.get("name") or "")
        return "".join(w[0] for w in re.split(r"[\s\-]+", name) if w and w[0].isalpha()).upper()
    for test in (lambda r: _bst_code(r) == code,
                 lambda r: all_parts(r) == code or "".join(w[0] for w in re.split(r"[\s\-]+", r.get("name") or "")
                                                          if w and w[0].isalpha()).upper() == code):
        hits = [r for r in rows if test(r)]
        if hits:
            return hits[0]
    pref = [r for r in rows if len(_bst_code(r)) == 2 and code.startswith(_bst_code(r)) and len(code) > 2]
    current = [r for r in pref if not r.get("archived")] or pref
    return current[0] if len(current) == 1 else None


def _bst_rows(table, student_id, order=None):
    c = _smartar_client()
    try:
        q = c.table(table).select("*").eq("student_id", str(student_id))
        if order:
            q = q.order(order)
        return q.execute().data or []
    except Exception:
        return []


def _d(v):
    try:
        return date.fromisoformat(str(v)[:10])
    except Exception:
        return None


def _bst_attendance(att_row, start, end):
    """Same counting as the Behaviour Support Tool's attendance_summary(): weekly pattern + dated exceptions."""
    schedule = sorted(att_row.get("schedule") or [], key=lambda v: v.get("from", ""))
    exceptions = {str(e.get("date"))[:10]: e for e in (att_row.get("exceptions") or [])
                  if isinstance(e, dict) and isinstance(e.get("date"), str)}
    for d_ in att_row.get("absent_dates") or []:
        if isinstance(d_, str):
            exceptions.setdefault(d_[:10], {"date": d_, "type": "Absent", "sessions": []})

    def planned(day):
        if day.weekday() > 4:
            return []
        if not schedule:
            return list(BST_ATT_SESSIONS)
        chosen = schedule[0]
        for v in schedule:
            if v.get("from", "") <= day.isoformat():
                chosen = v
        return list((chosen.get("days") or {}).get(BST_ATT_DAYS[day.weekday()], []))

    out = {"expected_days": 0, "days_attended": 0, "absent_days": 0, "early_finishes": 0,
           "day_ends_to_avoid_escalation": 0, "late_arrivals": 0, "part_time_pattern": False}
    day = start
    while day <= end:
        exc = exceptions.get(day.isoformat())
        pl = planned(day)
        if pl and set(pl) != set(BST_ATT_SESSIONS):
            out["part_time_pattern"] = True
        if not (exc and exc.get("type") == "No school") and pl:
            out["expected_days"] += 1
            actual = pl
            if exc:
                actual = [] if exc.get("type") == "Absent" else [x for x in BST_ATT_SESSIONS if x in (exc.get("sessions") or [])]
                if exc.get("type") == "Absent":
                    out["absent_days"] += 1
                if exc.get("type") == "Arrived late" or exc.get("late_min"):
                    out["late_arrivals"] += 1
                if exc.get("type") == "Finished early":
                    out["early_finishes"] += 1
                    if exc.get("reason") in BST_DAYEND_REASONS:
                        out["day_ends_to_avoid_escalation"] += 1
            if actual:
                out["days_attended"] += 1
        day += timedelta(days=1)
    return out


def _flat(v):
    """Field values as a list of plain strings — Behaviour Support fields can hold a single value,
    a list (multi-select), a dict, or JSON text of either."""
    if v is None or v == "":
        return []
    if isinstance(v, str):
        t = v.strip()
        if t[:1] in "[{":
            try:
                return _flat(json.loads(t))
            except Exception:
                pass
        return [t] if t else []
    if isinstance(v, dict):
        for k in ("label", "name", "text", "value", "category"):
            if v.get(k):
                return _flat(v[k])
        return [str(x) for x in v.values() if isinstance(x, (str, int, float)) and str(x).strip()][:1]
    if isinstance(v, (list, tuple, set)):
        out = []
        for x in v:
            out.extend(_flat(x))
        return out
    return [str(v)]


def _num(v, default=0.0):
    """Number from 3, "3", "3 - Moderate" or ["3"]; default if there isn't one."""
    if isinstance(v, (list, tuple)):
        v = v[0] if v else None
    try:
        return float(v)
    except Exception:
        m_ = re.search(r"\d+(\.\d+)?", str(v or ""))
        return float(m_.group()) if m_ else default


def _bst_incident_summary(incidents, criticals, start, end):
    recs = []
    for r in incidents:
        dt = _d(r.get("date"))
        if dt and start <= dt <= end:
            recs.append({"date": dt, "behaviour": r.get("behaviour_type") or "",
                         "trigger": r.get("antecedent") or "", "session": r.get("session") or "", "critical": False,
                         "location": r.get("location") or "", "day": r.get("day_of_week") or dt.strftime("%A"),
                         "function": r.get("hypothesis_function") or "", "response": r.get("intervention") or "",
                         "minutes": r.get("duration_minutes")})
    for r in criticals:
        dt = _d(r.get("created_at"))
        if dt and start <= dt <= end:
            recs.append({"date": dt, "behaviour": "Critical incident",
                         "trigger": r.get("primary_context") or "", "session": r.get("primary_time") or "", "critical": True,
                         "location": r.get("primary_location") or "", "day": dt.strftime("%A"),
                         "function": r.get("primary_hypothesis_function") or "", "response": "", "minutes": None,
                         "critical_behaviour": r.get("primary_behaviour") or ""})
    if not recs:
        return {"total_incidents": 0}
    recs.sort(key=lambda x: x["date"])
    weeks = max(1, ((end - start).days + 1) / 7)
    mid = start + (end - start) / 2
    first = [r for r in recs if r["date"] <= mid]
    second = [r for r in recs if r["date"] > mid]
    half_weeks = max(1, weeks / 2)

    def top(key, rows, n=3):
        cnt = defaultdict(int)
        for r in rows:
            for v in _flat(r.get(key)):
                cnt[v] += 1
        return [k for k, _ in sorted(cnt.items(), key=lambda kv: -kv[1])[:n]]
    return {
        "total_incidents": len(recs), "critical_incidents": sum(r["critical"] for r in recs),
        "incidents_per_week_first_half_of_placement": round(len(first) / half_weeks, 1),
        "incidents_per_week_second_half_of_placement": round(len(second) / half_weeks, 1),
        "critical_first_half": sum(r["critical"] for r in first), "critical_second_half": sum(r["critical"] for r in second),
        "most_common_behaviours": top("behaviour", [r for r in recs if not r["critical"]]),
        "most_common_triggers": top("trigger", recs), "most_common_session": (top("session", recs, 1) or [""])[0],
        "most_common_locations": top("location", recs), "most_common_days": top("day", recs, 2),
        "likely_functions_of_behaviour": top("function", recs),
        "staff_responses_used": top("response", [r for r in recs if not r["critical"]], 4),
        "critical_incident_behaviours": [b_ for r in recs for b_ in _flat(r.get("critical_behaviour"))][:5],
        "average_incident_minutes": (round(sum(_num(r["minutes"]) for r in recs if _num(r.get("minutes"))) /
                                     max(1, sum(1 for r in recs if _num(r.get("minutes")))), 1)
                                     if any(_num(r.get("minutes")) for r in recs) else None),
        "last_incident": recs[-1]["date"].isoformat(),
        "days_since_last_incident": (end - recs[-1]["date"]).days,
    }


WOT_AI_MEANING = {
    "hyper": "Hyperarousal (fight/flight) — out of the window, escalated",
    "copingup": "Coping, early warning — leaving the window and escalating (the behaviours here ARE early warning signs)",
    "wot": "Window of Tolerance — regulated, calm and ready to learn",
    "copingdown": "Coping, early withdrawal — leaving the window and shutting down (the behaviours here ARE early warning signs)",
    "hypo": "Hypoarousal (freeze/shutdown) — out of the window, withdrawn",
}


def wot_for_ai():
    """The student's Window of Tolerance (as pulled into this report, else the latest in the WoT Builder), labelled so
    the AI reads Context as triggers, Behaviour descriptors as early warning signs, and Interventions as what helps."""
    wot = st.session_state.get("tr_wot")
    if not wot and st.session_state.get("_tr_student"):
        try:
            wot = load_wot_report(st.session_state["_tr_student"])
        except Exception:
            wot = None
    if not wot or not wot.get("data"):
        return None
    zones = {}
    for z in WOT_ZONES:
        d_ = wot["data"].get(z["id"]) or {}
        items = {"context_triggers": d_.get("context") or [], "behaviour_descriptors": d_.get("behaviour") or [],
                 "interventions_that_help": d_.get("interventions") or []}
        if any(items.values()):
            zones[WOT_AI_MEANING.get(z["id"], z["name"])] = {k: v for k, v in items.items() if v}
    out = {"zones": zones} if zones else {}
    reg = (st.session_state.get("tr_regulation") or "").strip()
    if reg:
        out["regulation_profile_notes"] = reg
    return out or None


def bst_context(initials, report_start=None, report_end=None):
    """Everything the AI drafts are allowed to use, for one student. Returns (context, problem)."""
    if _smartar_client() is None:
        return None, "Can't reach the Behaviour Support Tool's database right now."
    stu = bst_find_student(initials)
    if not stu:
        return None, f"No student filed as {initials} in the Behaviour Support Tool."
    sid = str(stu["id"])
    start = _d(stu.get("placement_start")) or report_start
    end = _d(stu.get("placement_end")) or report_end or date.today()
    for ext in _bst_rows("placement_extensions", sid):
        if _d(ext.get("to_date")) and _d(ext.get("to_date")) > end:
            end = _d(ext.get("to_date"))
    end = min(end, date.today())
    if report_start and report_end and report_start < report_end:     # the report's own dates win if set
        start, end = report_start, min(report_end, date.today())
    if not start or start > end:
        return None, f"{initials}'s placement start date isn't set in the Behaviour Support Tool (or in the sidebar)."
    att_rows = _bst_rows("student_attendance", sid)
    attendance = _bst_attendance(att_rows[0], start, end) if att_rows else None
    incidents = _bst_incident_summary(_bst_rows("incidents", sid), _bst_rows("critical_incidents", sid), start, end)
    plan_rows = _bst_rows("support_plans", sid)
    plan = {k: v for k, v in (plan_rows[0] if plan_rows else {}).items() if k in BST_PLAN_FIELDS and v}
    trials = []
    for t in _bst_rows("strategy_trials", sid, order="start_date"):
        obs = [o.get("text", "") for o in (t.get("observations") or []) if isinstance(o, dict)][-3:]
        trials.append({k: v for k, v in {"title": t.get("title"), "strategy": t.get("strategy"),
                                          "status": t.get("status"), "outcome": t.get("outcome"),
                                          "what_was_learned": t.get("conclusion"), "staff_observations": obs}.items() if v})
    prof_rows = _bst_rows("starting_profiles", sid)
    prof = (prof_rows[0].get("profile") if prof_rows else None) or {}
    profile = {k: prof.get(k) for k in ("what_helps", "what_doesnt_help", "tags") if prof.get(k)}
    ctx = {"student": initials, "placement": f"{start.isoformat()} to {end.isoformat()}",
           "attendance": attendance, "incidents": incidents, "support_plan": plan,
           "strategy_trials": trials, "starting_profile": profile,
           "smartar_goals": st.session_state.get("tr_goal_digest", []),
           "window_of_tolerance": wot_for_ai(),
           "strategies_already_in_this_report": {
               "teaching_strategies": list(st.session_state.get("tr_hits") or []),
               "restorative_strategies": list(st.session_state.get("tr_rp") or [])}}
    # never send a name: swap any first/last name held in the Behaviour Support record for the initials
    raw = json.dumps(ctx, default=str)
    for nm in {str(stu.get("first_name") or ""), str(stu.get("last_name") or "")}:
        nm = nm.strip()
        if len(nm) > 1 and nm != "-" and nm.upper() != initials.upper():
            raw = re.sub(rf"(?<![A-Za-z]){re.escape(nm)}(?![A-Za-z])", initials, raw)
    return json.loads(raw), None


# ── Groq (portal-standard resilient call) ────────────────────────────────────
_GROQ_MODEL_CHAIN = ["openai/gpt-oss-120b", "qwen/qwen3.6-27b", "llama-3.3-70b-versatile"]


def groq_ai_call(prompt, max_tokens=1200, temperature=0.2, system=None):
    api_key = _secret("GROQ_API_KEY", "groq.api_key")
    if not api_key:
        raise RuntimeError("AI isn't set up on this deployment (no GROQ_API_KEY).")
    from groq import Groq
    try:
        client = Groq(api_key=api_key)
    except TypeError:
        import httpx
        client = Groq(api_key=api_key, http_client=httpx.Client())
    messages = ([{"role": "system", "content": system}] if system else []) + [{"role": "user", "content": prompt}]
    last_err = None
    for model in _GROQ_MODEL_CHAIN:
        tokens = max_tokens
        for _ in range(2):
            try:
                kw = dict(model=model, messages=messages, max_tokens=tokens, temperature=temperature)
                if model == "qwen/qwen3.6-27b":
                    kw["reasoning_effort"] = "none"
                elif model.startswith("openai/gpt-oss"):
                    kw["reasoning_effort"] = "low"       # leave the token budget for the answer, not the thinking
                    kw["max_tokens"] = tokens + 1500
                content = (client.chat.completions.create(**kw).choices[0].message.content or "").strip()
                if not content:
                    last_err = RuntimeError(f"{model} returned an empty reply")
                    break                                 # try the next model
                return content
            except Exception as e:
                last_err = e
                if "413" in str(e) or "too large" in str(e).lower():
                    tokens = max(256, tokens // 2)
                    continue
                break
    raise last_err


def _parse_json(raw):
    """JSON from a model reply. Copes with code fences, raw line breaks inside strings, and — when there is no
    JSON at all — keeps the plain text as {"text": ...} so a written answer isn't lost."""
    raw = (raw or "").replace("```json", "").replace("```", "").strip()
    s_, e_ = raw.find("{"), raw.rfind("}")
    if s_ != -1 and e_ > s_:
        try:
            return json.loads(raw[s_:e_ + 1], strict=False)
        except Exception:
            pass
    return {"text": raw} if raw and not raw.startswith("{") else {}


def _text_from(out):
    """The draft text whatever the model called it: 'text', 'summary', 'literacy_summary', a list of paragraphs…"""
    if not isinstance(out, dict):
        return str(out or "").strip()
    for k in ("text", "summary", "literacy_summary", "numeracy_summary", "paragraphs", "content", "draft"):
        v = out.get(k)
        if v:
            return "\n\n".join(_flat(v)) if not isinstance(v, str) else v.strip()
    strs = [v for v in out.values() if isinstance(v, str) and len(v.strip()) > 20]
    lists = [v for v in out.values() if isinstance(v, list) and v and all(isinstance(x, str) for x in v)]
    return strs[0].strip() if strs else ("\n\n".join(lists[0]) if lists else "")


AI_SYSTEM = ("You write sections of student reports for Cowandilla Learning Centre, a trauma-informed alternative "
             "education setting using the Berry Street Education Model (BSEM) and restorative practice. Write in "
             "Australian English, third person, warm, professional and strengths-based. Refer to the student ONLY by "
             "the initials given. Use ONLY facts in the data provided — never invent events, numbers, people or "
             "strategies. If the data doesn't support something, leave it out. The Window of Tolerance, where given, is the "
             "record of the student's triggers (context), early warning signs (behaviour descriptors, especially in "
             "the two Coping zones) and the interventions that help. NEVER say the student had no triggers, no early "
             "warning signs or found nothing challenging: few or no incidents, or no critical incidents, means staff "
             "supported the student to stay in or return to their window — not that nothing was hard for them. "
             "Never mention incident severity, severity "
             "ratings or scores, or describe incidents as severe. Return ONLY valid JSON.")


_SEVERITY_RX = re.compile(r"\bseverit|\bsevere", re.I)
# claims the Window of Tolerance contradicts
_NO_TRIGGER_RX = re.compile(
    r"\b(?:no|without|lack of|absence of|did not (?:show|display|have|identify)|didn't (?:show|have))\s+(?:any\s+)?"
    r"(?:clear\s+|noted\s+|identified\s+|identifiable\s+|recorded\s+|obvious\s+|specific\s+|known\s+)?"
    r"(?:triggers?|early warning signs?|warning signs?|antecedents?|challenges|difficulties)"
    r"|\bno\s+(?:particular\s+)?(?:situations?|contexts?)\s+(?:were|was)\s+(?:challenging|difficult)"
    r"|\bdid not find [^.]{0,40}(?:challenging|difficult)", re.I)


def _drop_sentences(text, rx):
    out = []
    for para_ in str(text or "").split("\n"):
        out.append(" ".join(x for x in re.split(r"(?<=[.!?])\s+", para_) if not rx.search(x)))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


def _drop_severity(text):
    """Remove any sentence that mentions incident severity (the report never reports it)."""
    out = []
    for para_ in str(text or "").split("\n"):
        sents = re.split(r"(?<=[.!?])\s+", para_)
        out.append(" ".join(x for x in sents if not _SEVERITY_RX.search(x)))
    return re.sub(r"\n{3,}", "\n\n", "\n".join(out)).strip()


_SCORE_RX = re.compile(r"\d+\s*(?:/|out of)\s*\d+|\d+(?:\.\d+)?\s*(?:%|per ?cent)|\bscor(?:e|ed|ing)\b", re.I)


def _no_scores(text):
    """Last resort: strip a score, fraction or percentage (and the words that introduce it) from a sentence."""
    num = r"\d+\s*(?:/|out of)\s*\d+|\d+(?:\.\d+)?\s*(?:%|per ?cent)"
    t = re.sub(r"\s*\((?:[^()]*?(?:" + num + r")[^()]*?)\)", "", text, flags=re.I)        # "(12/14)", "(86%)"
    t = re.sub(r",?\s*\b(?:with a score of|a score of|scoring|scored|achieving|achieved|obtaining|on)\s+(?:"
               + num + r")(?:\s+overall)?", "", t, flags=re.I)
    t = re.sub(r"\b(?:" + num + r")\b", "", t, flags=re.I)
    t = re.sub(r"\s{2,}", " ", t)
    return re.sub(r"\s+([.,;:])", r"\1", t).strip()


def _rewrite_without_scores(items, initials):
    """Ask the AI once more to reword any skill summary that still quotes a score; regex clean-up as the fallback."""
    bad = [it for it in items if _SCORE_RX.search(it["text"])]
    if bad:
        try:
            ask = ("Rewrite each of these report sentences so they contain NO scores, numbers, fractions or percentages. "
                   f"Describe the level in words instead (e.g. '{initials} demonstrates a proficient ability to…', "
                   "'is developing…', 'is secure in…'). Keep the meaning and the next step. Return JSON: "
                   '{"items": [{"name": "<same name>", "text": "<rewritten>"}]}\n\n'
                   + json.dumps([{"name": it["name"], "text": it["text"]} for it in bad]))
            fixed = {str(x.get("name")): str(x.get("text") or "") for x in
                     (_parse_json(groq_ai_call(ask, system=AI_SYSTEM)).get("items") or []) if isinstance(x, dict)}
            for it in bad:
                if fixed.get(it["name"], "").strip():
                    it["text"] = fixed[it["name"]].strip()
        except Exception:
            pass
    for it in items:
        if _SCORE_RX.search(it["text"]):
            it["text"] = _no_scores(it["text"])
    return items


def _program_says_sy(text):
    """True / False from a program or year-level value, None if it doesn't say. SA high school starts at Year 7."""
    t = str(text or "").strip().upper()
    if not t:
        return None
    if t.startswith("SY") or any(w in t for w in ("SENIOR", "SECONDARY", "HIGH SCHOOL", "HIGH")):
        return True
    if t.startswith(("JP", "PY")) or any(w in t for w in ("JUNIOR", "PRIMARY", "RECEPTION")):
        return False
    m_ = re.search(r"(?:YEAR|YR|Y)\s*(\d{1,2})|^(\d{1,2})$", t)
    if m_:
        return int(m_.group(1) or m_.group(2)) >= 7
    return None


def detect_senior_years():
    """Best guess at the report's lens: register program, then the Behaviour Support record (program / year level),
    then the enrolled school's name. Returns (is_sy, reason)."""
    v = _program_says_sy(st.session_state.get("_tr_program"))
    if v is not None:
        return v, f"program in the Student Register: {st.session_state.get('_tr_program')}"
    stu_ = st.session_state.get("_tr_student") or {}
    ck = f"_tr_bst_prog_{stu_.get('initials')}"
    if ck not in st.session_state:
        try:
            row = bst_find_student(stu_.get("initials") or "") if stu_.get("initials") else None
        except Exception:
            row = None
        st.session_state[ck] = (row or {}).get("program"), (row or {}).get("year_level")
    bprog, byear = st.session_state[ck]
    for val, src in ((bprog, "program in the Behaviour Support Tool"), (byear, "year level in the Behaviour Support Tool")):
        v = _program_says_sy(val)
        if v is not None:
            return v, f"{src}: {val}"
    school = str(st.session_state.get("tr_school") or "")
    if re.search(r"high school|secondary|senior|\bcollege\b|\b7\s*-\s*12\b", school, re.I):
        return True, f"enrolled school: {school}"
    return False, "no program recorded — assumed primary"


def is_senior_years(program=None):
    """The lens the AI drafts use. A choice made in the sidebar always wins."""
    choice = st.session_state.get("tr_lens")
    if choice in ("High school (SY)", "Primary school (JP/PY)"):
        return choice.startswith("High")
    if program:
        v = _program_says_sy(program)
        if v is not None:
            return v
    return detect_senior_years()[0]


SY_LENS = (
    "This student is in the SENIOR YEARS (SY) program and is moving to, or returning to, a HIGH SCHOOL. Apply a "
    "secondary-school lens and age-respectful language throughout. Frame supports around high school structures: a "
    "timetable with several subject teachers, moving between classrooms, home group/mentor teacher, year level "
    "coordinator, wellbeing leader or student services, SSO support in class, and flexible or modified timetables. "
    "Use secondary terms — e.g. 'break-out space', 'somewhere to retreat to', 'a quiet space in student services', "
    "'time-out or exit pass', 'check-in with a trusted adult or mentor', 'self-directed regulation strategies', "
    "'movement break', 'headphones', 'personal timetable or task list' — and NEVER primary-school terms such as 'calm "
    "down corner/space', 'calm corner', 'sensory corner', 'brain breaks', 'sticker or reward charts', 'visual "
    "timetable', 'First/Then board', 'carpet time' or 'class teacher'. Emphasise student agency, being involved in "
    "their own plan, discreet supports that avoid embarrassment in front of peers, and building independence.")
PRIMARY_LENS = ("This student is in a PRIMARY program (Junior Primary or Primary Years) and is moving to a primary "
                "school: frame supports around a primary classroom and class teacher, using age-appropriate language.")
# a last-resort swap of the most common primary terms in SY drafts
SY_TERM_SWAPS = [
    (r"\bcalm[- ]?down (?:corner|space|area|room|zone)s?\b", "break-out space"),
    (r"\bcalm (?:corner|area)s?\b", "break-out space"),
    (r"\b(?:quiet|sensory|cosy) corners?\b", "quiet space to retreat to"),
    (r"\bbrain breaks?\b", "movement breaks"),
    (r"\bvisual (?:timetable|schedule)s?\b", "personal timetable"),
    (r"\b(?:first[ /-]?then|now[ /-]?next) (?:board|chart|card)s?\b", "task checklist"),
    (r"\b(?:sticker|reward|star) charts?\b", "goal-tracking system"),
    (r"\bclass(?:room)? teachers?\b", "subject teachers"),
    (r"\bcarpet time\b", "group time"),
]


def apply_lens_terms(text, program=None):
    if not text or not (_program_says_sy(program) if program else is_senior_years()):
        return text
    for rx, new in SY_TERM_SWAPS:
        text = re.sub(rx, lambda m: (new[0].upper() + new[1:])
                      if (m.start() == 0 or m.string[:m.start()].rstrip()[-1:] in ".!?\n") else new, text, flags=re.I)
    return text


def ai_draft(section, initials, ctx):
    """Ask Groq for one section. Returns a dict shaped for that section (validated)."""
    ctx = dict(ctx, program=ctx.get("program") or st.session_state.get("_tr_program") or "")
    data = json.dumps(ctx, default=str)
    if section == "hits":
        menu = json.dumps(HITS_ELEMENTS)
        prompt = (f"Data about student {initials}:\n{data}\n\nHigh Impact Teaching Strategies and their key elements:\n{menu}\n\n"
                  "Choose the strategies (max 4) that the data clearly shows supported this student's engagement in learning "
                  "(e.g. from support plan teaching strategies, successful strategy trials and staff observations). For each, "
                  "pick only the key elements the data supports (exact wording from the list) and write 2-3 sentences on how "
                  f"it supported {initials}. Return JSON: "
                  '{"items": [{"name": "<strategy, exactly as listed>", "elements": ["<exact element>"], "text": "<2-3 sentences>"}]}')
    elif section == "restorative":
        prompt = (f"Data about student {initials}:\n{data}\n\nRestorative strategies: {json.dumps(RP_OPTIONS)}\n\n"
                  "Choose the restorative strategies (max 4) that the data shows were used to build relational safety and "
                  f"connection or to repair after incidents (e.g. post-incident repair, recovery, student voice, trials). For each, "
                  f"write 2-3 sentences on how it supported {initials}. Return JSON: "
                  '{"items": [{"name": "<strategy, exactly as listed>", "text": "<2-3 sentences>"}]}')
    elif section == "attendance":
        prompt = (f"Attendance data for {initials} over the placement ({ctx.get('placement')}):\n{json.dumps(ctx.get('attendance'))}\n"
                  f"Other context:\n{json.dumps({k: ctx.get(k) for k in ('support_plan', 'strategy_trials')}, default=str)}\n\n"
                  "Write 2-3 sentences describing the attendance pattern (e.g. part-time timetable, absences, early finishes "
                  "or day ends used to avoid escalation, late arrivals), framed supportively. Do not restate the total days "
                  'attended (it is shown separately). Return JSON: {"text": "<2-3 sentences>"}')
    elif section == "sw":
        prompt = (f"Sounds-Write phonics assessment results for student {initials}:\n{data}\n\n"
                  "For EACH skill listed, write a 'summary of outcome' of 1-2 sentences for a report table, starting with "
                  f"the student's initials, e.g. '{initials} demonstrates a proficient ability to blend…' or '{initials} is "
                  "developing…'. Describe the level of skill in WORDS ONLY — e.g. emerging, developing, consolidating, "
                  "proficient, secure — and any growth from pre to post as improvement in words. Do NOT include any score, "
                  "number, fraction or percentage, and don't quote the band names (Mastered/Developing/Needs improvement). "
                  "Then give the next step for that skill in Sounds-Write terms (e.g. consolidating the initial code, "
                  "moving into the extended code, two- and multi-syllable words, automaticity). Use the exact skill names "
                  f"given. Write in the PRESENT tense throughout (e.g. '{initials} demonstrates…', '{initials} is "
                  "developing…') — never past tense such as 'demonstrated' or 'was able to'. Return JSON: "
                  '{"items": [{"name": "<skill, exactly as given>", "text": "<1-2 sentences>"}]}')
    elif section == "literacy":
        prompt = (f"Literacy assessment results for student {initials}:\n{data}\n\n"
                  "Write the Literacy summary for the report, covering Word Aware (vocabulary) and Sounds-Write "
                  "(phonics), as two short paragraphs (about 120-180 words in total):\n"
                  "1) The student's current literacy ability: vocabulary, and phonics skills (blending, segmenting, phoneme "
                  "manipulation, code knowledge, non-word reading) — strengths first, then the areas still developing, "
                  "and the growth from pre to post where both scores exist.\n"
                  "2) Start with 'Next steps:' — the next progression in the student's learning: what to teach next in "
                  "Sounds-Write and in Word Aware vocabulary, concrete enough for the next teacher to act on.\n"
                  "Describe ability in words, not scores or percentages, and don't list the skill names as a list. "
                  f"Write in the PRESENT tense throughout (e.g. '{initials} demonstrates…', '{initials} is developing…') — "
                  "never past tense. "
                  "Only use the results given; if a skill wasn't assessed, don't comment on it. Separate the paragraphs "
                  'with a blank line. Return JSON: {"text": "<paragraphs>"}')
    elif section == "biin":
        prompt = (f"Big Ideas in Number (BIiN) assessment results for student {initials}:\n{data}\n\n"
                  "For EACH big idea listed, write a comment of 2-3 sentences for the report, starting with the student's "
                  f"initials. Describe what the student can DO in plain words — e.g. '{initials} shows confidence in "
                  f"identifying and ordering numbers to 100 and is developing efficient ways to count larger collections' — "
                  "rather than listing the element names or codes again (they're already in the table above). Describe "
                  "the level in words only and any growth from pre to post as improvement in words; don't quote the result "
                  "labels (Mastered/Developing/Needs improvement). Then give the next step in that big idea's learning "
                  f"progression. Write in the PRESENT tense throughout (e.g. '{initials} demonstrates…', '{initials} is "
                  "developing…') — never past tense. Use the exact big idea names given and only the results given. "
                  "Return JSON: "
                  '{"items": [{"name": "<big idea, exactly as given>", "text": "<2-3 sentences>"}]}')
    elif section == "numeracy":
        prompt = (f"Big Ideas in Number (BIiN) assessment results for student {initials}:\n{data}\n\n"
                  "Write the Numeracy summary for the report as two short paragraphs (about 120-180 words in total):\n"
                  "1) The student's current numeracy ability across the big ideas assessed (trusting the count, place "
                  "value, multiplicative thinking, partitioning as relevant) — strengths first, then what is still "
                  "developing, and growth from pre to post where both results exist.\n"
                  "2) Start with 'Next steps:' — the next progression in the student's number learning, concrete "
                  "enough for the next teacher to act on.\n"
                  "Describe what the student can do in plain words rather than listing element names or codes, and don't "
                  "quote the result labels. "
                  f"Write in the PRESENT tense throughout (e.g. '{initials} demonstrates…', '{initials} is developing…') — "
                  "never past tense. "
                  "Only use the results given; don't comment on big ideas that weren't assessed. Separate the paragraphs "
                  'with a blank line. Return JSON: {"text": "<paragraphs>"}')
    elif section == "recommendations":
        prompt = (f"Data about student {initials}:\n{data}\n\nWrite Transition Recommendations for the staff at the school "
                  f"{initials} is moving to. Give 6-10 specific, practical recommendations drawn ONLY from the data: what to put "
                  "in place before and in the first weeks (e.g. relationship building, visual supports, timetable/attendance "
                  "build-up), teaching strategies that worked, early warning signs to watch for and how to respond, known "
                  "triggers/times/places to plan around, regulation and recovery supports, restorative repair after incidents, "
                  "strategy trials that worked (and any that made things harder, to avoid), and continuing the SMARTAR goals. "
                  "Each recommendation is one or two sentences, starting with an action verb. Return JSON: "
                  '{"items": ["<recommendation>", "..."]}')
    else:
        prompt = (f"Data about student {initials}:\n{data}\n\nWrite the Overall Progress Summary as 3 short paragraphs "
                  "(about 200-280 words in total), elaborating on what the Behaviour Support Tool shows about the student:\n"
                  "1) Who the student is and their behaviour profile: strengths and interests; from the Window of "
                  "Tolerance, the contexts/triggers that move them into the Coping zones and the early warning signs "
                  "(behaviour descriptors) that show it; the behaviours seen, the most common triggers, times, days and "
                  "places in the incident records, the likely functions of behaviour, and how "
                  "incidents changed from the first to the second half of the placement (frequency, critical "
                  "incidents, days since the last incident).\n"
                  "2) What helped: the interventions from the Window of Tolerance, support plan strategies and adjustments, "
                  "staff responses, regulation/recovery supports, "
                  "strategy trials and what was learned (including anything that didn't help), and SMARTAR goal progress.\n"
                  "3) Attendance and engagement, then a forward-looking closing on readiness for transition.\n"
                  "Only include points the data supports; skip any that it doesn't. Separate paragraphs with a blank line. "
                  'Return JSON: {"text": "<paragraphs>"}')
    sy_ = is_senior_years(ctx.get("program"))
    system_ = AI_SYSTEM + " " + (SY_LENS if sy_ else PRIMARY_LENS)
    ctx["program"] = "SY" if sy_ else (ctx.get("program") or "Primary")
    out = _parse_json(groq_ai_call(prompt, system=system_, max_tokens=1800 if section in ("summary", "recommendations") else 1200))
    for it in out.get("items") or []:                  # SY: secondary wording
        if isinstance(it, dict) and isinstance(it.get("text"), str):
            it["text"] = apply_lens_terms(it["text"], "SY" if sy_ else "PY")
    if isinstance(out.get("items"), list):
        out["items"] = [apply_lens_terms(x, "SY" if sy_ else "PY") if isinstance(x, str) else x for x in out["items"]]
    for k_ in [k for k, v in out.items() if isinstance(v, str)]:
        out[k_] = apply_lens_terms(out[k_], "SY" if sy_ else "PY")
    for it in out.get("items") or []:                  # no severity anywhere in a draft
        if isinstance(it, dict) and "text" in it:
            it["text"] = _drop_severity(it["text"])
    if isinstance(out.get("items"), list):
        out["items"] = [(_drop_severity(x) if isinstance(x, str) else x) for x in out["items"]]
        out["items"] = [x for x in out["items"] if not (isinstance(x, str) and not x.strip())]
    if section not in ("hits", "restorative", "sw", "biin", "recommendations") and not out.get("text"):
        out["text"] = _text_from(out)
    if "text" in out:
        out["text"] = _drop_severity(out["text"])
    if ctx.get("window_of_tolerance"):          # the WoT records triggers + early warning signs — never deny them
        if out.get("text"):
            out["text"] = _drop_sentences(out["text"], _NO_TRIGGER_RX)
        for it in out.get("items") or []:
            if isinstance(it, dict) and it.get("text"):
                it["text"] = _drop_sentences(it["text"], _NO_TRIGGER_RX)
    if section == "hits":
        items = []
        for it in out.get("items") or []:
            nm = next((h for h in HITS_OPTIONS if h.lower() == str(it.get("name", "")).strip().lower()), None)
            if nm and it.get("text"):
                els = [e for e in HITS_ELEMENTS[nm] if e.lower() in {str(x).strip().lower() for x in it.get("elements") or []}]
                items.append({"name": nm, "elements": els, "text": str(it["text"]).strip()})
        return {"items": items}
    if section == "biin":
        names = [b for b, _ in BIIN]
        assessed = {x["big_idea"] for x in ctx.get("big_ideas_in_number") or []}
        items = []
        for it in out.get("items") or []:
            nm = next((n_ for n_ in names if isinstance(it, dict) and n_.lower() == str(it.get("name", "")).strip().lower()), None)
            if nm and nm in assessed and it.get("text") and nm not in [x["name"] for x in items]:
                txt = re.sub(r"\s*\(\s*\d\.\d[^()]*\)", "", str(it["text"]))     # "(2.1 Number naming)"
                txt = re.sub(r"\b\d\.\d\s+", "", txt)                               # "2.1 Number naming" -> "Number naming"
                items.append({"name": nm, "text": re.sub(r"\s{2,}", " ", txt).strip()})
        return {"items": items}
    if section == "sw":
        names = [sk for sk, _ in SOUNDS_WRITE]
        items = []
        for it in out.get("items") or []:
            nm = next((n_ for n_ in names if n_.lower() == str(it.get("name", "")).strip().lower()
                       or n_.lower().startswith(str(it.get("name", "")).strip().lower()[:8])), None) \
                if isinstance(it, dict) and str(it.get("name", "")).strip() else None
            if nm and it.get("text") and nm not in [x["name"] for x in items]:
                items.append({"name": nm, "text": str(it["text"]).strip()})
        assessed = {x["skill"] for x in ctx.get("sounds_write") or []}
        return {"items": _rewrite_without_scores([x for x in items if x["name"] in assessed], initials)}
    if section == "restorative":
        items = []
        for it in out.get("items") or []:
            nm = next((r for r in RP_OPTIONS if r.lower() == str(it.get("name", "")).strip().lower()), None)
            if nm and it.get("text"):
                items.append({"name": nm, "text": str(it["text"]).strip()})
        return {"items": items}
    if section == "recommendations":
        recs_ = [x.lstrip("-•* ").strip() for x in _flat(out.get("items")) if x.lstrip("-•* ").strip()]
        return {"text": "\n".join(f"• {r_}" for r_ in recs_)} if recs_ else {"text": str(out.get("text") or "").strip()}
    res = {"text": str(out.get("text") or "").strip()}
    if section == "attendance" and ctx.get("attendance"):
        res["days_attended"] = ctx["attendance"]["days_attended"]
        res["expected_days"] = ctx["attendance"]["expected_days"]
    return res


LITERACY_SECTIONS = ("sw", "literacy", "biin", "numeracy")   # drafted from scores, not Behaviour Support data


def _pct(score, mx):
    try:
        return round(float(score) / float(mx) * 100)
    except Exception:
        return None


def literacy_context(initials):
    """Only the literacy assessment results entered in this report — no Behaviour Support data needed."""
    rows = st.session_state.get("tr_sw_latest") or st.session_state.get("tr_sw_base") or []
    sw = []
    for (skill, mx), r in zip(SOUNDS_WRITE, rows):
        pre, post = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip()
        if not (pre or post):
            continue
        sw.append({"skill": skill, "what_it_assesses": SOUNDS_WRITE_DESC.get(skill, ""), "max_score": mx,
                   "pre": pre or None, "post": post or None, "pre_percent": _pct(pre, mx), "post_percent": _pct(post, mx),
                   "band_now": (lambda p_: None if p_ is None else "Mastered" if p_ >= 90 else "Developing" if p_ >= 70
                                else "Needs improvement")(_pct(post or pre, mx)),
                   "teacher_notes": str(r.get("Summary") or "").strip() or None})
    wa = {k: (st.session_state.get(f"tr_vocab_{k}") or "").strip() for k in ("type", "pre", "post")}
    return {"student": initials, "program": st.session_state.get("_tr_program") or "",
            "word_aware_vocabulary": {k: v for k, v in wa.items() if v} or None,
            "sounds_write": sw,
            "score_bands": "Mastered 90-100%, Developing 70-89%, Needs improvement under 70%"}


def numeracy_context(initials):
    """Only the BIiN results entered in this report."""
    out = []
    for bi, (big_idea, elements) in enumerate(BIIN):
        rows = st.session_state.get(f"tr_biin{bi}_latest") or st.session_state.get(f"tr_biin{bi}_base") or []
        els = []
        for (code, name), r in zip(elements, rows):
            pre, post = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip()
            if pre or post:
                els.append({"element": f"{code} {name}", "pre": pre or None, "post": post or None})
        if els:
            out.append({"big_idea": big_idea, "elements_assessed": els,
                        "teacher_comment": (st.session_state.get(f"tr_biin_c_{bi}") or "").strip() or None})
    return {"student": initials, "program": st.session_state.get("_tr_program") or "", "big_ideas_in_number": out,
            "result_scale": "Mastered (90-100%), Developing (70-80%), Needs improvement (under 70%)"}


def run_ai_draft(section, initials, report_start, report_end):
    """Button callback: build the context, ask the AI, keep the draft for review."""
    st.session_state.pop(f"tr_aiedit_{section}", None)
    if section in LITERACY_SECTIONS:
        try:
            ctx = numeracy_context(initials) if section in ("biin", "numeracy") else literacy_context(initials)
            if section in ("biin", "numeracy") and not ctx["big_ideas_in_number"]:
                st.session_state[f"tr_ai_{section}"] = {"error": "Set Pre and/or Post results for at least one BIiN element first."}
                return
            if section == "sw" and not ctx.get("sounds_write"):
                st.session_state["tr_ai_sw"] = {"error": "Enter at least one Pre or Post score in the Sounds-Write table first."}
                return
            if section == "literacy" and not ctx.get("sounds_write") and not ctx.get("word_aware_vocabulary"):
                st.session_state["tr_ai_literacy"] = {"error": "Enter the Word Aware and/or Sounds-Write scores first."}
                return
            d_ = ai_draft(section, initials, ctx)
            if not d_.get("items") and not d_.get("text"):
                d_ = {"error": "The AI couldn't draft this from the scores entered."}
            st.session_state[f"tr_ai_{section}"] = d_
        except Exception as e:
            st.session_state[f"tr_ai_{section}"] = {"error": f"Couldn't create a draft: {e}"}
        return
    try:
        ctx, problem = bst_context(initials, report_start, report_end)
        if problem:
            st.session_state[f"tr_ai_{section}"] = {"error": problem}
            return
        if section == "attendance" and not ctx.get("attendance"):
            st.session_state[f"tr_ai_{section}"] = {"error": f"No attendance has been recorded for {initials} in the Behaviour Support Tool."}
            return
        d_ = ai_draft(section, initials, ctx)
        if not d_.get("items") and not d_.get("text"):
            d_ = {"error": "The AI didn't find enough in the Behaviour Support data to draft this section."}
        st.session_state[f"tr_ai_{section}"] = d_
    except Exception as e:
        st.session_state[f"tr_ai_{section}"] = {"error": f"Couldn't create a draft: {e}"}


def _append(key, text):
    cur = (st.session_state.get(key) or "").strip()
    st.session_state[key] = (cur + "\n\n" + text).strip() if cur else text


def accept_ai_draft(section):
    """Add (or add the edited version of) a draft to the report fields."""
    d_ = st.session_state.get(f"tr_ai_{section}") or {}
    editing = st.session_state.get(f"tr_aiedit_{section}")
    if section == "sw":
        rows = [dict(r) for r in (st.session_state.get("tr_sw_latest") or st.session_state.get("tr_sw_base") or
                                  [{"Pre": "", "Post": "", "Summary": ""} for _ in SOUNDS_WRITE])]
        names = [sk for sk, _ in SOUNDS_WRITE]
        for n_, it in enumerate(d_.get("items") or []):
            if editing and not st.session_state.get(f"tr_aikeep_{section}_{n_}", True):
                continue
            text = ((st.session_state.get(f"tr_aitext_{section}_{n_}") if editing else it["text"]) or "").strip()
            if text and it["name"] in names:
                rows[names.index(it["name"])]["Summary"] = text      # replaces that skill's summary
        st.session_state["tr_sw_base"] = rows
        st.session_state["tr_sw_latest"] = rows
        st.session_state["tr_sw_v"] = st.session_state.get("tr_sw_v", 0) + 1   # reload the table with the new text
        discard_ai_draft(section)
        st.session_state["tr_ai_added_note"] = "Added to the Summary column — check the wording in the table."
        return
    if section == "biin":
        names = [b for b, _ in BIIN]
        for n_, it in enumerate(d_.get("items") or []):
            if editing and not st.session_state.get(f"tr_aikeep_{section}_{n_}", True):
                continue
            text = ((st.session_state.get(f"tr_aitext_{section}_{n_}") if editing else it["text"]) or "").strip()
            if text and it["name"] in names:
                _append(f"tr_biin_c_{names.index(it['name'])}", text)
        discard_ai_draft(section)
        st.session_state["tr_ai_added_note"] = "Added to the comments under each big idea — check the wording."
        return
    if section in ("hits", "restorative"):
        list_key, opts = ("tr_hits", HITS_OPTIONS) if section == "hits" else ("tr_rp", RP_OPTIONS)
        chosen = list(st.session_state.get(list_key) or [])
        for n_, it in enumerate(d_.get("items") or []):
            if editing and not st.session_state.get(f"tr_aikeep_{section}_{n_}", True):
                continue
            text = (st.session_state.get(f"tr_aitext_{section}_{n_}") if editing else it["text"]) or ""
            if not text.strip():
                continue
            if it["name"] not in chosen:
                chosen.append(it["name"])
            i_ = opts.index(it["name"])
            if section == "hits":
                ek = f"tr_hits_el_{i_}"
                st.session_state[ek] = list(dict.fromkeys(list(st.session_state.get(ek) or []) + it.get("elements", [])))
                _append(f"tr_hits_c_{i_}", text.strip())
            else:
                _append(f"tr_rp_c_{i_}", text.strip())
        st.session_state[list_key] = [o for o in opts if o in chosen]
    else:
        text = (st.session_state.get(f"tr_aitext_{section}_0") if editing else d_.get("text")) or ""
        if section == "attendance":
            if d_.get("expected_days"):
                st.session_state["tr_days_att"] = int(d_.get("days_attended") or 0)
                st.session_state["tr_days_tot"] = max(1, int(d_["expected_days"]))
            if text.strip():
                _append("tr_att_comment", text.strip())
        elif text.strip():
            _append({"recommendations": "tr_recs", "literacy": "tr_vocab_summary", "numeracy": "tr_numeracy"}
                    .get(section, "tr_summary"), text.strip())
    discard_ai_draft(section)
    st.session_state["tr_ai_added_note"] = "Added to the report — check the wording below."


def discard_ai_draft(section):
    for k in list(st.session_state.keys()):
        if k in (f"tr_ai_{section}", f"tr_aiedit_{section}") or k.startswith(f"tr_aitext_{section}_") \
                or k.startswith(f"tr_aikeep_{section}_"):
            del st.session_state[k]


def edit_ai_draft(section):
    d_ = st.session_state.get(f"tr_ai_{section}") or {}
    st.session_state[f"tr_aiedit_{section}"] = True
    if section in ("hits", "restorative", "sw", "biin"):
        for n_, it in enumerate(d_.get("items") or []):
            st.session_state[f"tr_aitext_{section}_{n_}"] = it["text"]
            st.session_state[f"tr_aikeep_{section}_{n_}"] = True
    else:
        st.session_state[f"tr_aitext_{section}_0"] = d_.get("text", "")


def ai_draft_box(section, initials, report_start, report_end):
    """The '✨ Draft from Behaviour Support data' control + its italic suggestion with Add / Edit / Discard."""
    d_ = st.session_state.get(f"tr_ai_{section}")
    lit = section in LITERACY_SECTIONS
    if not d_:
        st.button({"sw": "✨ Draft skill summaries from the scores", "literacy": "✨ Draft literacy summary and next steps",
                   "biin": "✨ Draft a comment for each big idea", "numeracy": "✨ Draft numeracy summary and next steps"}
                  .get(section, "✨ Draft from Behaviour Support data"), key=f"tr_aibtn_{section}",
                  on_click=run_ai_draft, args=(section, initials, report_start, report_end),
                  help=("Uses AI to suggest wording from the assessment scores entered above. " if lit else
                        "Uses AI to suggest wording from this student's Behaviour Support Tool records. ")
                       + "Nothing is added until you choose Add.")
        if st.session_state.get("tr_ai_added_note"):
            st.caption("✅ " + st.session_state.pop("tr_ai_added_note"))
        return
    if d_.get("error"):
        st.warning(d_["error"])
        st.button("Close", key=f"tr_aiclose_{section}", on_click=discard_ai_draft, args=(section,))
        return
    with st.container(border=True):
        st.markdown(("**✨ AI draft from the assessment scores**" if lit else "**✨ AI draft from Behaviour Support data**")
                    + f" · {'🏫 high school (SY) lens' if is_senior_years() else 'primary school lens'}"
                    + " — *a suggestion only; check it before adding.*")
        editing = st.session_state.get(f"tr_aiedit_{section}")
        if section in ("hits", "restorative", "sw", "biin"):
            for n_, it in enumerate(d_.get("items") or []):
                if editing:
                    st.checkbox(f"Include **{it['name']}**", key=f"tr_aikeep_{section}_{n_}")
                    st.text_area(it["name"], key=f"tr_aitext_{section}_{n_}", height=90, label_visibility="collapsed")
                else:
                    els = (" — key elements: " + "; ".join(it["elements"])) if it.get("elements") else ""
                    st.markdown(f"**{it['name']}**{els}  \n*{it['text']}*")
        else:
            if section == "attendance" and d_.get("expected_days"):
                st.markdown(f"**From attendance records:** {d_['days_attended']} of {d_['expected_days']} expected days attended "
                            "(these numbers will fill the Days Attended / Total Days boxes).")
            if editing:
                st.text_area("Draft", key=f"tr_aitext_{section}_0", height=260 if section in ("summary", "recommendations", "literacy", "numeracy") else 130,
                             label_visibility="collapsed")
            elif d_.get("text"):
                st.markdown("\n\n".join(f"*{ln_.strip()}*" for ln_ in d_["text"].split("\n") if ln_.strip()))
        b1, b2, b3 = st.columns(3)
        b1.button("✅ Add edited version" if editing else "✅ Add to report", key=f"tr_aiadd_{section}", type="primary",
                  on_click=accept_ai_draft, args=(section,), use_container_width=True)
        if not editing:
            b2.button("✏️ Edit first", key=f"tr_aiedt_{section}", on_click=edit_ai_draft, args=(section,),
                      use_container_width=True)
        b3.button("🗑 Discard", key=f"tr_aidis_{section}", on_click=discard_ai_draft, args=(section,),
                  use_container_width=True)

# ══════════════════════════════════════════════════════════════════════════════
# DATA — SMARTAR GOAL BUILDER
# ══════════════════════════════════════════════════════════════════════════════
@st.cache_data(ttl=120, show_spinner=False)
def load_smartar_students():
    c = _smartar_client()
    if c is None:
        return None
    try:
        return c.table("smartar_students").select("*").order("student_name").execute().data or []
    except Exception:
        return None


def match_smartar_student(initials, smartar_students):
    """Register initials → SMARTAR student_name (the register writes its code
    into SMARTAR verbatim). Exact, case-insensitive."""
    key = initials.strip().upper()
    hits = [s for s in (smartar_students or []) if str(s.get("student_name") or "").strip().upper() == key]
    return hits[0] if len(hits) == 1 else None


def load_goals(smartar_name):
    """Active + archived goals, newest first (as the Builder's Progress Report)."""
    c = _smartar_client()
    if c is None:
        return []
    try:
        return (c.table("smartar_goals").select("*").eq("student_name", smartar_name)
                .order("created_at", desc=True).execute().data or [])
    except Exception:
        return []


def goal_date_range(goal):
    """Same rule as the Builder: start → archived_at for archived goals, start → today otherwise."""
    start = goal.get("start_date") or (goal.get("created_at") or "")[:10] or date.today().isoformat()
    if not goal.get("active", True) and goal.get("archived_at"):
        end = goal["archived_at"][:10]
    else:
        end = date.today().isoformat()
    return str(start)[:10], end


def load_goal_tracking(goal):
    """Tracking rows for the goal's own date range, limited to the sessions in
    its tracking period — exactly what the Builder's Progress Report charts."""
    c = _smartar_client()
    if c is None:
        return []
    from_d, to_d = goal_date_range(goal)
    sessions = SESSIONS_FOR_PERIOD.get(goal.get("tracking_period", "All Day"), ALL_SESSIONS)
    try:
        rows = (c.table("smartar_tracking").select("*").eq("goal_id", goal["id"])
                .gte("session_date", from_d).lte("session_date", to_d)
                .order("session_date").execute().data or [])
    except Exception:
        return []
    rows = [r for r in rows if r.get("session_time") in sessions]
    rows.sort(key=lambda r: (str(r.get("session_date")), str(r.get("recorded_at") or "")))
    return rows


def goal_stats(tracking):
    counts = {l: 0 for l in LEVEL_ORDER}
    for r in tracking:
        lvl = r.get("performance_level")
        if lvl in counts:
            counts[lvl] += 1
    total = sum(counts.values())
    pct = {l: (counts[l] / total * 100 if total else 0) for l in LEVEL_ORDER}
    at_or_above = round(sum(counts[l] for l in ("EXCEEDING", "ABOVE", "EXPECTED")) / total * 100) if total else 0
    # analyze_trend() from the Builder: first half vs second half average
    trend = "insufficient_data"
    if len(tracking) >= 4:
        mid = len(tracking) // 2
        a = sum(SCORE_MAP.get(r.get("performance_level", ""), 0) for r in tracking[:mid]) / mid
        b = sum(SCORE_MAP.get(r.get("performance_level", ""), 0) for r in tracking[mid:]) / (len(tracking) - mid)
        trend = "improving" if b - a > 0.5 else "declining" if b - a < -0.5 else "stable"
    # suggested current level = typical (median) level over the last 10 observations
    recent = [SCORE_MAP[r["performance_level"]] for r in tracking[-10:] if r.get("performance_level") in SCORE_MAP]
    suggested = SCORE_TO_LVL[int(statistics.median_low(recent))] if recent else "EXPECTED"
    dates = [str(r.get("session_date"))[:10] for r in tracking]
    return {"counts": counts, "total": total, "pct": pct, "at_or_above": at_or_above,
            "trend": trend, "suggested": suggested,
            "first": min(dates) if dates else None, "last": max(dates) if dates else None}


TREND_TEXT = {"improving": "📈 Improving", "declining": "📉 Declining", "stable": "➡️ Stable",
              "insufficient_data": "Not enough data for a trend"}


def pie_png(tracking, size_in=3.0):
    """The Builder's 'Distribution' pie (make_goal_chart_mpl, bottom-left panel),
    drawn on its own: same levels, colours, start angle and labels."""
    if not tracking:
        return None
    s = pd.Series([r.get("performance_level") for r in tracking])
    counts_d = s.value_counts().reindex(TRACK_LEVELS).dropna()
    counts_d = counts_d[counts_d > 0]
    if counts_d.empty:
        return None
    fig, ax = plt.subplots(figsize=(size_in, size_in), facecolor="white")
    _, _, autotexts = ax.pie(
        counts_d.values, labels=counts_d.index, colors=[MPL_COLOR[l] for l in counts_d.index],
        autopct="%1.0f%%", startangle=90, textprops={"fontsize": 8},
        wedgeprops={"edgecolor": "white", "linewidth": 1.5},
    )
    for at in autotexts:
        at.set_fontsize(8)
        at.set_fontweight("bold")
        at.set_color("white")
    ax.set_title("Distribution", fontsize=10, color=TEAL, fontweight="bold", loc="left", pad=6)
    ax.axis("equal")
    buf = BytesIO()
    fig.savefig(buf, format="png", dpi=170, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    return buf.getvalue()


def fmt_date(iso_str, long=True):
    if not iso_str:
        return ""
    try:
        d = date.fromisoformat(str(iso_str)[:10])
        return d.strftime("%d %B %Y" if long else "%d %b").lstrip("0")
    except Exception:
        return str(iso_str)[:10]


# ══════════════════════════════════════════════════════════════════════════════
# STATE — everything this page stores lives under "tr_" keys, so switching
# student can wipe it in one go (one student's details never carry over)
# ══════════════════════════════════════════════════════════════════════════════
def remove_goal(gid):
    st.session_state["tr_goal_sel"] = [x for x in (st.session_state.get("tr_goal_sel") or []) if x != gid]


def restore_goal(gid):
    sel = list(st.session_state.get("tr_goal_sel") or [])
    if gid not in sel:
        sel.append(gid)
    st.session_state["tr_goal_sel"] = sel


def reset_report_state():
    for k in list(st.session_state.keys()):
        if k.startswith("tr_"):
            del st.session_state[k]


def S(key, default=None):
    return st.session_state.get(f"tr_{key}", default)


def inc(section):
    """Is this section part of the current report type?"""
    rt = S("report_type", "Review Report")
    if rt == "Modified Report":
        return section in (S("sections") or [])
    if rt == "Review Report":
        return section in REVIEW_SECTIONS
    return True


# ── saved reports (student_reports table) ────────────────────────────────────
def load_saved_reports(student):
    c = _students_client()
    if c is None:
        return None
    try:
        return (c.table(REPORTS_TABLE).select("*").eq("student_register_id", student["id"])
                .order("updated_at", desc=True).execute().data or [])
    except Exception:
        return None          # table not created yet (or unreachable)


def _editor_state_rows(name):
    return S(f"{name}_latest") or S(f"{name}_base")


def snapshot():
    data = {}
    for k in list(st.session_state.keys()):
        if not k.startswith("tr_"):
            continue
        short = k[3:]
        if not SAVED_KEY_RE.match(short):
            continue
        v = st.session_state[k]
        if short in DATE_KEYS and isinstance(v, date):
            v = v.isoformat()
        data[short] = v
    data["editors"] = {name: _editor_state_rows(name) for name in EDITORS if _editor_state_rows(name)}
    return json.loads(json.dumps(data, default=str))


def personalise(rep_, initials, preferred, full_name, school):
    """Finalised copy: every whole-word use of the student's initials (including pulled SMARTAR goals and
    Window of Tolerance text, and "SD's") becomes the name chosen at finalising. Cover and footer use the
    full name. Never saved anywhere — built only for the download."""
    rx = re.compile(r"(?<![A-Za-z])" + re.escape(initials) + r"(?![A-Za-z])")
    skip = {"initials", "type", "sections", "program", "pie", "id", "archived_at", "first", "last",
            "tracking_period", "current", "updated_at", "pages", "style", "kind", "id"}

    def walk(v, key=None):
        if key in skip:
            return v
        if isinstance(v, str):
            return rx.sub(preferred, v)
        if isinstance(v, dict):
            return {k: walk(x, k) for k, x in v.items()}
        if isinstance(v, list):
            if len(v) == 2 and all(isinstance(x, str) for x in v) and v[1] in ATT_TABLE_STYLE:
                return [walk(v[0]), v[1]]
            return [walk(x) for x in v]
        if isinstance(v, tuple):
            return tuple(walk(x) for x in v)
        return v
    out = walk(rep_)
    out["name"], out["cover_name"], out["footer_name"], out["school"] = preferred, full_name, full_name, school
    return out


def apply_record(rec, note=None):
    """Load a saved report into the page (used as a button callback and on student pick)."""
    reset_report_state()
    st.session_state["_tr_ver"] = st.session_state.get("_tr_ver", 0) + 1
    data = rec.get("data") or {}
    for short, v in data.items():
        if short == "editors":
            continue
        if short in DATE_KEYS and v:
            try:
                v = date.fromisoformat(str(v)[:10])
            except Exception:
                continue
        st.session_state[f"tr_{short}"] = v
    for name, rows in (data.get("editors") or {}).items():
        st.session_state[f"tr_{name}_base"] = rows
        st.session_state[f"tr_{name}_latest"] = rows
    st.session_state["tr_report_type"] = rec.get("report_type") or data.get("report_type") or "Review Report"
    # reports saved before recommendations became an appendix / before Student Voice existed
    valid = {k for k, _ in SECTIONS}
    if isinstance(data.get("sections"), list):
        st.session_state["tr_sections"] = [k for k in data["sections"] if k in valid]
    if "app_recs" not in data and str(data.get("recs") or "").strip():
        st.session_state["tr_app_recs"] = True
    st.session_state["tr_record_id"] = rec.get("id")
    st.session_state["tr_record_type"] = st.session_state["tr_report_type"]
    st.session_state["tr_record_saved"] = rec.get("updated_at")
    st.session_state["tr_loaded_note"] = note or (
        f"Opened the {st.session_state['tr_report_type']} saved {fmt_date(rec.get('updated_at'))}"
        + (f" by {rec['updated_by']}" if rec.get("updated_by") else "") + ".")


def finalise_report(student, teacher):
    full = (st.session_state.get("tr_fin_full") or "").strip()
    pref = (st.session_state.get("tr_fin_pref") or "").strip()
    school = (st.session_state.get("tr_fin_school") or "").strip()
    if not full or not school:
        st.session_state["tr_fin_error"] = "Enter the student's full name and enrolled school to finalise."
        return
    st.session_state["tr_fin_error"] = ""
    st.session_state["tr_fin_pref"] = pref or full.split()[0]
    st.session_state["tr_school"] = school                 # the school is part of the saved report
    st.session_state["tr_finalised"] = {"at": datetime.utcnow().isoformat(), "by": teacher or "unknown"}
    st.session_state["tr_fin_ready"] = True
    ok, msg = save_report(student, teacher)
    st.session_state["tr_fin_saved_msg"] = msg if ok else f"Finalised, but the saved report wasn't updated: {msg}"


def start_transition_from_review():
    """Carry everything forward into a NEW Transition Report record; the Review stays as saved."""
    st.session_state["tr_report_type"] = "Transition Report"
    st.session_state["tr_record_id"] = None
    st.session_state["tr_record_type"] = None
    st.session_state["tr_loaded_note"] = ("Started a Transition Report from the Review Report — everything has been "
                                          "carried over. Save it to keep it; the Review Report stays as it was.")


def save_report(student, teacher):
    c = _students_client()
    if c is None:
        return False, "Can't reach the database right now."
    now = datetime.utcnow().isoformat()
    payload = {
        "student_register_id": student["id"], "student_initials": student["initials"],
        "report_type": S("report_type"), "sections": [k for k, _ in SECTIONS if inc(k)],
        "data": snapshot(), "updated_by": teacher or "unknown", "updated_at": now,
    }
    same_record = S("record_id") and S("record_type") == S("report_type")
    try:
        if same_record:
            res = c.table(REPORTS_TABLE).update(payload).eq("id", S("record_id")).execute()
        else:
            payload["created_by"] = teacher or "unknown"
            res = c.table(REPORTS_TABLE).insert(payload).execute()
        row = (res.data or [None])[0]
    except Exception as e:
        return False, f"Couldn't save ({e}). Has the `{REPORTS_TABLE}` table been created?"
    if row:
        st.session_state["tr_record_id"] = row.get("id")
    st.session_state["tr_record_type"] = S("report_type")
    st.session_state["tr_record_saved"] = now
    st.session_state.pop("tr_records", None)      # refresh the list
    return True, ("Saved." if same_record else f"Saved as a new {S('report_type')}.")


def editor(name, default_rows):
    """Data-editor rows that survive being hidden (Modified Report sections) and loading a saved report."""
    if S(f"{name}_hidden"):
        st.session_state[f"tr_{name}_base"] = S(f"{name}_latest")
        st.session_state[f"tr_{name}_v"] = S(f"{name}_v", 0) + 1
        st.session_state[f"tr_{name}_hidden"] = False
    base = S(f"{name}_base") or default_rows
    if len(base) != len(default_rows):
        base = default_rows
    key = f"tr_{name}_ed_{st.session_state.get('_tr_ver', 0)}_{S(f'{name}_v', 0)}"
    RENDERED_EDITORS.add(name)
    return base, key


RENDERED_EDITORS = set()


# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR — student by register initials
# ══════════════════════════════════════════════════════════════════════════════
st.title("📄 Transition Report Builder")
st.markdown("Generate comprehensive transition reports")

register = load_register()

with st.sidebar:
    st.header("Report Configuration")

    if register is None:
        st.error("Can't reach the Student Register right now.")
    elif not register:
        st.info("No current students on the register.")

if register is None:
    st.error("**Can't reach the Student Register**, so the student list can't load.")
    st.caption(f"Details: {REGISTER_ERROR}")
    if st.button("🔄 Try again"):
        st.rerun()
    st.stop()
if not register:
    st.info("There are no current students on the Student Register yet. Add students in the Student Register, "
            "then reload this page.")
    st.stop()

with st.sidebar:

    reg_by_id = {str(r["id"]): r for r in register}
    picked = st.selectbox(
        "Student (register initials) *",
        options=[""] + list(reg_by_id.keys()),
        format_func=lambda sid: "Choose student…" if not sid else
        f"{reg_by_id[sid]['initials']} · {reg_by_id[sid]['program']}".rstrip(" ·"),
        key="picker_sid",
    )
    if st.session_state.get("_tr_current_sid") != picked:
        reset_report_state()
        st.session_state["_tr_current_sid"] = picked
        if picked:
            _recs = load_saved_reports(reg_by_id[picked])
            st.session_state["tr_records"] = _recs
            if _recs:
                apply_record(_recs[0])          # open this student's most recent saved report
                st.session_state["tr_records"] = _recs
    if not picked:
        st.warning("Choose a student to continue")

if not picked:
    st.info("👈 **Choose a student** (by register initials) in the **Report Configuration** panel on the left to "
            "start or open their Review, Transition or Modified report.")
    st.caption("Can't see the panel? Click the **›** arrow at the top-left of the page to open it.")
    st.stop()

with st.sidebar:
    student = reg_by_id[picked]
    INITIALS = student["initials"]
    st.session_state["_tr_program"] = student.get("program") or ""
    st.session_state["_tr_student"] = {"id": student.get("id"), "initials": INITIALS}

    # keep entered values even while a section is hidden (Modified Report) — Streamlit
    # otherwise drops a widget's value when the widget isn't shown
    for _k in list(st.session_state.keys()):
        if _k.startswith("tr_") and (SAVED_KEY_RE.match(_k[3:]) or _k == "tr_print_name"):
            st.session_state[_k] = st.session_state[_k]
    st.session_state.setdefault("tr_report_type", "Review Report")
    st.session_state.setdefault("tr_report_date", date.today())
    st.session_state.setdefault("tr_pstart", date.today())
    st.session_state.setdefault("tr_pend", date.today())
    st.session_state.setdefault("tr_days_att", 0)
    st.session_state.setdefault("tr_days_tot", 1)

    st.markdown("---")
    st.radio("Report type", REPORT_TYPES, key="tr_report_type",
             captions=[REPORT_TYPE_HELP[t] for t in REPORT_TYPES])
    REPORT_TYPE = S("report_type")
    if REPORT_TYPE == "Modified Report":
        st.multiselect("Sections to include (the cover page is always included)", [k for k, _ in SECTIONS],
                       key="tr_sections", format_func=lambda k: SECTION_LABEL[k])
        if not S("sections"):
            st.warning("Choose the sections this Modified Report will include.")

    # ── saved reports for this student ──
    if "tr_records" not in st.session_state:
        st.session_state["tr_records"] = load_saved_reports(student)
    records = st.session_state["tr_records"]
    with st.expander(f"💾 Saved reports for {INITIALS}", expanded=True):
        if records is None:
            st.caption(f"Saved reports aren't set up yet — run this once in the Supabase SQL editor "
                       f"(the project with the Student Register):")
            st.code(REPORTS_TABLE_SQL, language="sql")
        elif not records:
            st.caption("Nothing saved yet for this student.")
        else:
            for rec in records:
                is_open = rec.get("id") == S("record_id")
                rc1, rc2 = st.columns([3, 1])
                _fin = (rec.get("data") or {}).get("finalised")
                rc1.markdown(f"{'**▶ ' if is_open else ''}{rec.get('report_type')}{'**' if is_open else ''}"
                             f"{' ✅ Finalised' if _fin else ''}  \n"
                             f"<span style='font-size:0.75rem;color:#777'>saved {fmt_date(rec.get('updated_at'))}"
                             f"{' · ' + rec['updated_by'] if rec.get('updated_by') else ''}</span>",
                             unsafe_allow_html=True)
                rc2.button("Open", key=f"tr_open_{rec.get('id')}", disabled=is_open,
                           on_click=apply_record, args=(rec,), use_container_width=True)
        if S("record_id") and S("record_type") == "Review Report" and REPORT_TYPE == "Review Report":
            st.button("➡️ Start the Transition Report from this Review", key="tr_to_transition",
                      on_click=start_transition_from_review, use_container_width=True)
        if S("record_id") and S("record_type") and S("record_type") != REPORT_TYPE:
            st.caption(f"Saving will create a new {REPORT_TYPE} — the {S('record_type')} stays as it was.")
        SAVE_SLOT = st.container()

    st.caption("Reports are saved with initials only. The student's name is added when you finalise "
               "(Generate tab) and is never saved.")
    DISPLAY_NAME = INITIALS
    WHO = INITIALS

    st.markdown("---")
    report_date = st.date_input("Report Date", key="tr_report_date")
    placement_start = st.date_input("Placement Start Date", key="tr_pstart")
    placement_end = st.date_input("Placement End Date", key="tr_pend")
    st.markdown("---")
    lc_teacher = st.text_input("LC Teacher Name", key="tr_teacher")
    enrolled_school = st.text_input("Enrolled School", key="tr_school")
    _sy_guess, _sy_why = detect_senior_years()
    st.radio("AI drafts are written for", ["Automatic", "Primary school (JP/PY)", "High school (SY)"], key="tr_lens",
             horizontal=False,
             help="Sets the lens for every AI draft (language, supports, recommendations). 'Automatic' uses the "
                  "student's program.")
    if S("lens", "Automatic") == "Automatic":
        st.caption(f"Automatic → **{'High school (SY)' if _sy_guess else 'Primary school'}** ({_sy_why}).")


tab1, tab2, tab3 = st.tabs(["📝 Report Sections", "👁️ Preview", "💾 Generate"])

# ══════════════════════════════════════════════════════════════════════════════
# TAB 1 — REPORT SECTIONS
# ══════════════════════════════════════════════════════════════════════════════
# values used later even when a section isn't part of this report type
report_goals = []
days_attended, total_days, attendance_pct = S("days_att", 0) or 0, S("days_tot", 1) or 1, 0.0

with tab1:
    st.header(f"{REPORT_TYPE}: {DISPLAY_NAME}")
    if S("loaded_note"):
        st.info(st.session_state.pop("tr_loaded_note"))
    if REPORT_TYPE == "Modified Report" and not S("sections"):
        st.info("Choose the sections to include in the sidebar — only the cover page is included so far.")
    _left_out = [SECTION_LABEL[k] for k, _ in SECTIONS if not inc(k)]
    if _left_out:
        st.caption(f"**Not in this {REPORT_TYPE}:** " + ", ".join(_left_out) + (
            " — tick them under *Sections to include* in the sidebar to add them."
            if REPORT_TYPE == "Modified Report" else
            " — switch the report type to Transition Report to include it."))

    if inc("literacy"):
        # ── LITERACY ─────────────────────────────────────────────────────────────
        st.subheader("📖 Literacy Progress")
        st.markdown("**Word Aware (Vocabulary)**")
        lc1, lc2, lc3 = st.columns(3)
        lc1.text_input("Pre-Assessment Type", key="tr_vocab_type")
        lc2.text_input("Pre Score", key="tr_vocab_pre", placeholder="/5")
        lc3.text_input("Post Score", key="tr_vocab_post", placeholder="/5")

        st.markdown("**Sounds-Write Assessments**")
        st.caption("Leave blank if not assessed")
        _sw_base, _sw_key = editor("sw", [{"Pre": "", "Post": "", "Summary": ""} for _ in SOUNDS_WRITE])
        sw_df = pd.DataFrame({
            "Skill": [s for s, _ in SOUNDS_WRITE],
            "Max Score": [m for _, m in SOUNDS_WRITE],
            "Pre": [str(r.get("Pre") or "") for r in _sw_base],
            "Post": [str(r.get("Post") or "") for r in _sw_base],
            "Summary": [str(r.get("Summary") or "") for r in _sw_base],
        })
        edited_sw = st.data_editor(
            sw_df, hide_index=True, use_container_width=True, key=_sw_key,
            disabled=["Skill", "Max Score"],
            column_config={"Pre": st.column_config.TextColumn(), "Post": st.column_config.TextColumn(),
                           "Summary": st.column_config.TextColumn(width="large")},
        )
        st.session_state["tr_sw_latest"] = edited_sw[["Pre", "Post", "Summary"]].fillna("").to_dict("records")
        ai_draft_box("sw", INITIALS, placement_start, placement_end)

        st.markdown("**Literacy summary — Word Aware and Sounds-Write**")
        st.caption("The student's current literacy ability and the next progression in their learning.")
        ai_draft_box("literacy", INITIALS, placement_start, placement_end)
        st.text_area("Literacy summary", key="tr_vocab_summary", height=150, label_visibility="collapsed",
                     placeholder="Current ability in vocabulary and phonics… Next steps: …")
        st.markdown("---")

    if inc("numeracy"):
        # ── NUMERACY ─────────────────────────────────────────────────────────────
        st.subheader("🔢 Numeracy Progress")
        st.markdown("**Big Ideas in Number (BIiN)**")
        st.caption(BIIN_LEGEND + ". Set Pre and/or Post for each element that was assessed — "
                   "only assessed elements appear on the report.")
        for bi, (big_idea, elements) in enumerate(BIIN):
            with st.expander(f"{big_idea} ({len(elements)} elements)", expanded=(bi < 2)):
                _b_base, _b_key = editor(f"biin{bi}", [{"Pre": "", "Post": ""} for _ in elements])
                ed = st.data_editor(
                    pd.DataFrame({"Element": [f"{c} {n}" for c, n in elements],
                                  "Pre": [str(r.get("Pre") or "") for r in _b_base],
                                  "Post": [str(r.get("Post") or "") for r in _b_base]}),
                    hide_index=True, use_container_width=True, key=_b_key, disabled=["Element"],
                    column_config={
                        "Element": st.column_config.TextColumn(width="medium"),
                        "Pre": st.column_config.SelectboxColumn(options=BIIN_RESULTS, width="small"),
                        "Post": st.column_config.SelectboxColumn(options=BIIN_RESULTS, width="small"),
                    },
                )
                st.session_state[f"tr_biin{bi}_latest"] = ed[["Pre", "Post"]].fillna("").to_dict("records")
                st.text_area(f"Comments — {big_idea}", key=f"tr_biin_c_{bi}", height=90,
                             placeholder=f"What the student can do in {big_idea.lower()}, and what's next…")
        ai_draft_box("biin", INITIALS, placement_start, placement_end)
        st.markdown("**Numeracy summary — Big Ideas in Number**")
        st.caption("The student's current numeracy ability and the next progression in their learning.")
        ai_draft_box("numeracy", INITIALS, placement_start, placement_end)
        st.text_area("Numeracy summary", key="tr_numeracy", height=150, label_visibility="collapsed",
                     placeholder="Current ability across the big ideas… Next steps: …")
        st.markdown("---")

    if inc("hits"):
        # ── HITS ─────────────────────────────────────────────────────────────────
        st.subheader("🎯 Pedagogical Strategies (HITS)")
        st.caption("Choose the High Impact Teaching Strategies that promoted positive engagement. For each one, "
                   "tick the key elements you used and say how it worked for this student.")
        ai_draft_box("hits", INITIALS, placement_start, placement_end)
        st.multiselect("Strategies that promoted positive engagement", HITS_OPTIONS, key="tr_hits")
        for strat in (S("hits", []) or []):
            hi = HITS_OPTIONS.index(strat)
            with st.container(border=True):
                st.markdown(f"**{strat}**")
                st.multiselect("Key elements used", HITS_ELEMENTS[strat], key=f"tr_hits_el_{hi}")
                st.text_area("How it supported the student", key=f"tr_hits_c_{hi}", height=90,
                             placeholder=f"e.g. what {strat.lower()} looked like for this student and the difference it made…")
        with st.expander("🖼️ How this will look on the report", expanded=bool(S("hits"))):
            st.image(make_hits_matrix_png({h_: S(f"hits_el_{HITS_OPTIONS.index(h_)}", []) or []
                                           for h_ in (S("hits", []) or [])}, dpi=110), use_container_width=True)
        st.markdown("---")

    if inc("restorative"):
        # ── RESTORATIVE ──────────────────────────────────────────────────────────
        st.subheader("🤝 Restorative Practice & Relational Safety")
        with st.expander("ℹ️ About relational safety (shown on the report)", expanded=False):
            fc1, fc2 = st.columns([1, 1])
            fc1.image(b64img(RP_FLOWER_JPG_B64), use_container_width=True)
            fc2.markdown(RP_BLURB_INTRO + "  \n\n*The adult:*  \n" +
                         "  \n".join(f"*{n}. {t}*" for n, t in enumerate(RP_BLURB_STEPS, start=1)))
            fc2.caption(RP_CITATION)
        ai_draft_box("restorative", INITIALS, placement_start, placement_end)
        st.multiselect("Restorative strategies used", RP_OPTIONS, key="tr_rp")
        for strat in (S("rp", []) or []):
            ri = RP_OPTIONS.index(strat)
            with st.container(border=True):
                pc_, tc_ = st.columns([1, 12])
                pc_.image(b64img(RP_PETAL_JPG_B64[strat]), width=48)
                tc_.text_area(strat, key=f"tr_rp_c_{ri}", height=90,
                              placeholder="How this strategy supported relational safety and connection for the student…")
        st.text_area("Other comments on restorative practice (optional)", key="tr_rp_comments", height=80)
        st.markdown("---")

    if inc("regulation"):
        # ── REGULATION PROFILE — pulled from the Window of Tolerance Builder ─────
        st.subheader("🌡️ Regulation Profile (Window of Tolerance)")
        if "tr_wot_lookup" not in st.session_state:
            st.session_state["tr_wot_lookup"] = load_wot_report(student)
        wot_found = st.session_state["tr_wot_lookup"]
        wot = S("wot")

        if wot:
            wc1, wc2, wc3 = st.columns([6, 1, 1])
            wc1.success(
                f"✓ Pulled from the Window of Tolerance Builder — **{INITIALS}** "
                f"({wot['status']}, updated {fmt_date(wot['updated_at'])}"
                f"{' by ' + wot['updated_by'] if wot['updated_by'] else ''}). "
                "Untick a zone to leave it out of this report."
            )
            if wc2.button("🔄 Refresh", key="tr_wot_refresh", use_container_width=True):
                fresh = load_wot_report(student)
                st.session_state["tr_wot_lookup"] = fresh
                st.session_state["tr_wot"] = fresh
                for z in WOT_ZONES:
                    st.session_state[f"tr_wotz_{z['id']}"] = bool(fresh and wot_has_content(fresh, z["id"]))
                st.rerun()
            if wc3.button("✖ Remove", key="tr_wot_remove", use_container_width=True):
                st.session_state.pop("tr_wot", None)
                st.rerun()

            for z in WOT_ZONES:
                zc = st.columns([1.3, 2, 2, 2])
                with zc[0]:
                    st.markdown(
                        f"<div style='background:{z['color']};color:#fff;border-radius:8px;padding:8px 10px;'>"
                        f"<b>{z['name']}</b><br><i style='font-size:0.8rem;opacity:.9'>{z['tag']}</i></div>",
                        unsafe_allow_html=True,
                    )
                    st.checkbox("Include", key=f"tr_wotz_{z['id']}")
                for i, (col, label) in enumerate(WOT_COLS, start=1):
                    items = wot["data"][z["id"]][col]
                    body = "".join(f"<li>{t}</li>" for t in items) if items else "<span style='color:#999'>—</span>"
                    zc[i].markdown(
                        f"<div style='background:{z['tint']};border-radius:8px;padding:8px 10px;font-size:0.85rem;min-height:70px;'>"
                        f"<div style='font-size:0.68rem;font-weight:700;text-transform:uppercase;color:#555;'>{label}</div>"
                        f"<ul style='margin:4px 0 0;padding-left:16px'>{body}</ul></div>",
                        unsafe_allow_html=True,
                    )

            if st.button("✍️ Draft summary from this profile", key="tr_wot_draft"):
                zones_on = {z["id"]: S(f"wotz_{z['id']}", False) for z in WOT_ZONES}
                st.session_state["tr_regulation"] = draft_wot_summary(wot, zones_on, WHO)
                st.rerun()
            st.caption("Writes a starting paragraph into the summary box below, replacing what's there — edit it as you like.")
        elif wot_found:
            wc1, wc2 = st.columns([5, 2])
            wc1.info(
                f"**Window of Tolerance report found** for {INITIALS} — {wot_found['status']}, "
                f"last updated {fmt_date(wot_found['updated_at'])}"
                f"{' by ' + wot_found['updated_by'] if wot_found['updated_by'] else ''}."
            )
            if wc2.button("Pull from Window of Tolerance Builder", type="primary",
                          key="tr_wot_pull", use_container_width=True):
                st.session_state["tr_wot"] = wot_found
                for z in WOT_ZONES:
                    st.session_state[f"tr_wotz_{z['id']}"] = wot_has_content(wot_found, z["id"])
                st.rerun()
        else:
            st.info(f"No Window of Tolerance report yet for {INITIALS}. Build one in the "
                    "Window of Tolerance Builder, or type the profile below.")

        st.text_area("Regulation Profile Summary", key="tr_regulation", height=130,
                     placeholder="Describe typical arousal patterns, triggers, and effective co-regulation strategies...")
        st.markdown("---")

    if inc("smartar"):
        # ── SMARTAR GOALS — pulled from the SMARTAR Goal Builder ─────────────────
        st.subheader("📊 Behaviour Progress: SMARTAR Goals")
        smartar_students = load_smartar_students()
        sm_student = None
        all_goals = []
        if smartar_students is None:
            st.warning("Can't reach the SMARTAR Goal Builder right now — goals can't be added to the report until it's reachable. Try reloading the page.")
        else:
            sm_student = match_smartar_student(INITIALS, smartar_students)
            if sm_student is None:
                same_prog = [s for s in smartar_students if s.get("program") and student["program"]
                             and str(student["program"]).upper().startswith(str(s["program"]).upper())]
                pool = same_prog or smartar_students
                st.warning(f"No SMARTAR Goal Builder student is filed as **{INITIALS}**. "
                           "If they're filed under a different code, choose them here:")
                names = [""] + sorted({str(s["student_name"]) for s in pool})
                if S("sm_override") not in names:
                    st.session_state["tr_sm_override"] = ""
                chosen = st.selectbox("SMARTAR student", names, key="tr_sm_override",
                                      format_func=lambda n: "Choose…" if not n else n)
                if chosen:
                    sm_student = next(s for s in pool if str(s["student_name"]) == chosen)
            if sm_student:
                if "tr_goals_cache" not in st.session_state or S("goals_cache_for") != sm_student["student_name"]:
                    st.session_state["tr_goals_cache"] = load_goals(sm_student["student_name"])
                    st.session_state["tr_goals_cache_for"] = sm_student["student_name"]
                all_goals = st.session_state["tr_goals_cache"]

        goal_by_id = {str(g["id"]): g for g in all_goals}
        if sm_student and all_goals:
            n_act = sum(1 for g in all_goals if g.get("active", True))
            gc1, gc2 = st.columns([5, 1])
            gc1.caption(f"SMARTAR Goal Builder student **{sm_student['student_name']}** · "
                        f"{n_act} active, {len(all_goals) - n_act} archived goal(s). "
                        "All are included — remove any you don't want on this report.")
            if gc2.button("🔄 Refresh goals", key="tr_goals_refresh", use_container_width=True):
                for k in ("tr_goals_cache", "tr_goals_cache_for", "tr_tracking_cache", "tr_goal_sel"):
                    st.session_state.pop(k, None)
                st.rerun()

            def _goal_label(gid):
                g = goal_by_id[gid]
                if g.get("active", True):
                    tag = "🟢 Active"
                else:
                    tag = f"🟠 Archived {fmt_date(g.get('archived_at'), long=False)}"
                txt = g.get("smartar_goal") or "No goal text"
                return f"{tag} — {txt[:90]}{'…' if len(txt) > 90 else ''}"

            # active goals first, then archived — newest first within each
            ordered = ([gid for gid, g in goal_by_id.items() if g.get("active", True)] +
                       [gid for gid, g in goal_by_id.items() if not g.get("active", True)])
            if "tr_goal_sel" not in st.session_state:
                st.session_state["tr_goal_sel"] = ordered
            else:
                known = set(S("goal_known") or [])
                new_ids = [gid for gid in ordered if known and gid not in known]
                kept = [gid for gid in S("goal_sel") if gid in goal_by_id]
                st.session_state["tr_goal_sel"] = kept + [gid for gid in new_ids if gid not in kept]
                if new_ids:
                    st.caption(f"✨ {len(new_ids)} goal(s) added in the SMARTAR Goal Builder since this report was saved "
                               "— included automatically.")
            st.session_state["tr_goal_known"] = ordered
            st.multiselect("Goals included in this report (active and archived)", ordered,
                           key="tr_goal_sel", format_func=_goal_label,
                           help="Click ✕ on a goal (or use 🗑 Remove from report on its card) to leave it off this report. "
                                "It stays in the SMARTAR Goal Builder.")
            removed = [gid for gid in ordered if gid not in set(S("goal_sel") or [])]
            if removed:
                with st.expander(f"🗑 Removed from this report ({len(removed)}) — add back", expanded=False):
                    for gid in removed:
                        r1, r2 = st.columns([6, 1])
                        r1.markdown(_goal_label(gid))
                        r2.button("↩ Add back", key=f"tr_goal_back_{gid}", on_click=restore_goal, args=(gid,),
                                  use_container_width=True)
        elif sm_student:
            st.info(f"No SMARTAR goals in the SMARTAR Goal Builder for {sm_student['student_name']} yet. "
                    "Add them in the SMARTAR Goal Builder, then reload this page.")

        _sel = set(S("goal_sel") or [])
        selected_ids = ([gid for gid, g in goal_by_id.items() if g.get("active", True) and gid in _sel] +
                        [gid for gid, g in goal_by_id.items() if not g.get("active", True) and gid in _sel]) if all_goals else []

        # tracking + stats are fetched once per goal and kept for this student
        tr_cache = st.session_state.setdefault("tr_tracking_cache", {})
        for gid in selected_ids:
            if gid not in tr_cache:
                tr_cache[gid] = load_goal_tracking(goal_by_id[gid])

        pulled_goals = []
        for n, gid in enumerate(selected_ids, start=1):
            g = goal_by_id[gid]
            tracking = tr_cache.get(gid, [])
            stats = goal_stats(tracking)
            active = g.get("active", True)
            with st.expander(f"Goal {n} {'🟢' if active else '🟠'} — {(g.get('smartar_goal') or '')[:80]}",
                             expanded=(n <= 3)):
                pc1, pc2 = st.columns([1, 2])
                png = pie_png(tracking)
                with pc1:
                    if png:
                        st.image(png, use_container_width=True)
                    else:
                        st.caption("No tracking recorded for this goal yet.")
                with pc2:
                    status_line = ("🟢 **Active goal**" if active else
                                   f"🟠 **Archived** {fmt_date(g.get('archived_at'))}"
                                   + (f" — {g['archive_reason']}" if g.get("archive_reason") else ""))
                    st.markdown(status_line)
                    if stats["total"]:
                        st.markdown(
                            f"{stats['total']} observations · {fmt_date(stats['first'], False)} → "
                            f"{fmt_date(stats['last'], False)} · tracking period: {g.get('tracking_period', 'All Day')}  \n"
                            f"{TREND_TEXT[stats['trend']]} · **{stats['at_or_above']}%** at Expected or better"
                        )
                    if g.get("exclusion_goal"):
                        st.markdown(f"**🏫 Exclusion goal:** {g['exclusion_goal']}")
                    st.markdown(f"**🎯 SMARTAR goal:** {g.get('smartar_goal') or '—'}")
                    st.caption("Goal wording comes from the SMARTAR Goal Builder — edit it there if it needs changing.")

                st.markdown("**Goal Attainment Scale** (from the SMARTAR Goal Builder)")
                for lvl in LEVEL_ORDER:
                    desc = g.get(GAS_COLUMN[lvl]) or ""
                    if desc:
                        st.markdown(f"<span style='color:{LEVEL_COLOR[lvl]};font-weight:600'>{LEVEL_EMOJI[lvl]} {lvl}</span> — {desc}",
                                    unsafe_allow_html=True)
                cur_key = f"tr_g_current_{gid}"
                if cur_key not in st.session_state:
                    st.session_state[cur_key] = stats["suggested"]
                st.selectbox("Current achievement level", LEVEL_ORDER, key=cur_key,
                             format_func=lambda l: f"{LEVEL_EMOJI[l]} {l}")
                if stats["total"]:
                    st.caption(f"Suggested from the last 10 observations: {LEVEL_EMOJI[stats['suggested']]} {stats['suggested']}")
                st.button("🗑 Remove this goal from the report", key=f"tr_goal_rm_{gid}", on_click=remove_goal, args=(gid,),
                          help="Leaves it off this report only — the goal stays in the SMARTAR Goal Builder. "
                               "You can add it back from 'Removed from this report'.")

            pulled_goals.append({
                "source": "builder", "id": gid, "active": active,
                "archived_at": g.get("archived_at"), "archive_reason": g.get("archive_reason") or "",
                "tracking_period": g.get("tracking_period", "All Day"),
                "excl": g.get("exclusion_goal") or "", "smartar": g.get("smartar_goal") or "",
                "gas": {lvl: g.get(GAS_COLUMN[lvl]) or "" for lvl in LEVEL_ORDER},
                "current": S(f"g_current_{gid}", "EXPECTED"),
                "stats": stats, "pie": png,
            })

        report_goals = pulled_goals
        st.session_state["tr_goal_digest"] = [
            {"goal": g_["smartar"], "status": "active" if g_["active"] else "archived",
             "current_level": g_["current"], "pct_at_expected_or_better": g_["stats"]["at_or_above"],
             "trend": g_["stats"]["trend"], "observations": g_["stats"]["total"]} for g_ in pulled_goals]
        st.markdown("---")

    # ── STUDENT VOICE ─────────────────────────────────────────────
    if inc("voice"):
        st.subheader("🗣️ Student Voice and Agency")
        st.caption(VOICE_BLURB + " Type it in, pull it from the Behaviour Support plan, and/or upload a photo of the "
                   "student's writing or a document.")
        st.button("📥 Pull student voice from the Behaviour Support plan", key="tr_voice_pull",
                  on_click=pull_student_voice, args=(INITIALS,))
        if st.session_state.get("tr_voice_msg"):
            st.warning(st.session_state["tr_voice_msg"])
        st.text_area("In the student's words", key="tr_voice_text", height=120,
                     placeholder="e.g. \"I'm proud that I can… What helps me is… I want my new teacher to know…\"")
        with st.expander(f"📎 Uploads — photos of writing, drawings, documents ({len(S('voice_files') or [])})",
                         expanded=bool(S("voice_files"))):
            upload_panel("tr_voice_files", "voice", False, "Caption (optional)",
                         "A photo of the student's writing or work, a PDF, a Word document or a text file.")
        st.markdown("---")

    # ── ATTENDANCE & SUMMARY ─────────────────────────────────────────────────
    if inc("attendance"):
        st.subheader("📅 Attendance")
        ai_draft_box("attendance", INITIALS, placement_start, placement_end)
        ac1, ac2 = st.columns(2)
        with ac1:
            days_attended = st.number_input("Days Attended", min_value=0, key="tr_days_att")
            total_days = st.number_input("Total Days", min_value=1, key="tr_days_tot")
        ac2.metric("Attendance Rate", f"{(days_attended / total_days * 100 if total_days else 0):.1f}%")
        st.text_area("Attendance comments (optional)", key="tr_att_comment", height=80,
                     placeholder="e.g. attendance pattern, part-time timetable, early finishes…")
        st.button("📋 Pull attendance table from the Behaviour Support Tool" if not S("att_table") else
                  "🔄 Refresh attendance table from the Behaviour Support Tool", key="tr_att_pull",
                  on_click=pull_attendance_table, args=(INITIALS, placement_start, placement_end),
                  help="A week-by-week (Mon–Fri) colour table for the whole placement: green attended, red absent, purple "
                       "transition days at the enrolled school (from the Transition Timetable).")
        if S("att_table_msg"):
            st.warning(S("att_table_msg"))
        if S("att_table"):
            tb_ = S("att_table")
            st.checkbox(f"Include the attendance table in the report ({fmt_date(tb_['from'])} – {fmt_date(tb_['to'])})",
                        key="tr_att_table_on")
            with st.expander("👁️ Attendance table", expanded=False):
                st.markdown(att_table_html(tb_), unsafe_allow_html=True)
    if inc("summary"):
        st.subheader("📝 Overall Progress Summary")
        ai_draft_box("summary", INITIALS, placement_start, placement_end)
        st.text_area("Overall Progress Summary", key="tr_summary", height=150, label_visibility="collapsed",
                     placeholder="Summarise key achievements, challenges, and demonstrated growth...")
    # ── APPENDICES (optional, any report type) ───────────────────────────────
    st.markdown("---")
    st.subheader("📎 Appendices (optional)")
    st.caption("Extras added at the end of the report, each under its own Appendix heading.")
    st.checkbox("Include **Transition Recommendations** as an appendix", key="tr_app_recs")
    if S("app_recs"):
        with st.container(border=True):
            st.markdown("**➡️ Transition Recommendations**")
            ai_draft_box("recommendations", INITIALS, placement_start, placement_end)
            st.text_area("Transition Recommendations", key="tr_recs", height=150, label_visibility="collapsed",
                         placeholder="Specific strategies, accommodations, or supports recommended for successful transition...")
    st.markdown("**Text appendices**")
    for aid in list(S("apps") or []):
        with st.container(border=True):
            t1, t2 = st.columns([6, 1])
            t1.text_input("Appendix title", key=f"tr_app_title_{aid}", placeholder="e.g. Speech Pathology summary")
            t2.button("✕ Remove", key=f"tr_app_rm_{aid}", on_click=remove_text_appendix, args=(aid,))
            st.text_area("Appendix text", key=f"tr_app_text_{aid}", height=120)
    st.button("➕ Add a text appendix", key="tr_app_add", on_click=add_text_appendix)
    st.markdown("**Uploads (visuals, work samples, documents)**")
    upload_panel("tr_uploads", "app", True, "Appendix title (required)",
                 "Photos or scans of work, visuals, a PDF, a Word document or a text file. Each becomes its own appendix.")
attendance_pct = days_attended / total_days * 100 if total_days else 0


# ══════════════════════════════════════════════════════════════════════════════
# GATHER EVERYTHING FOR PREVIEW / WORD
# ══════════════════════════════════════════════════════════════════════════════
def sounds_write_rows():
    rows = []
    saved = _editor_state_rows("sw") or []
    for (skill, mx), r in zip(SOUNDS_WRITE, saved):
        pre, post, summ = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip(), str(r.get("Summary") or "").strip()
        if not (pre or post or summ):
            continue
        change = ""
        try:
            change = f"{float(post) - float(pre):+g}"
        except Exception:
            pass
        rows.append({"skill": skill, "max": mx, "pre": pre, "post": post,
                     "change": change, "summary": summ})
    return rows


def biin_rows():
    """Assessed BIiN elements only (Pre and/or Post set), in framework order."""
    out = []
    for bi, (big_idea, elements) in enumerate(BIIN):
        for (code, name), r in zip(elements, _editor_state_rows(f"biin{bi}") or []):
            pre, post = str(r.get("Pre") or "").strip(), str(r.get("Post") or "").strip()
            if not (pre or post):
                continue
            prog = ""
            if pre in BIIN_RANK and post in BIIN_RANK:
                d = BIIN_RANK[post] - BIIN_RANK[pre]
                prog = "Improved" if d > 0 else "Maintained" if d == 0 else "Declined"
            out.append({"big_idea": big_idea, "element": f"{code} {name}", "pre": pre, "post": post, "progress": prog})
    return out


def collect_report(name_on_report):
    wot_on = None
    if S("wot"):
        wot_on = [z for z in WOT_ZONES if S(f"wotz_{z['id']}", False)]
    return {
        "type": REPORT_TYPE, "sections": {k for k, _ in SECTIONS if inc(k)},
        "name": name_on_report, "initials": INITIALS, "program": student["program"],
        "report_date": report_date, "pstart": placement_start, "pend": placement_end,
        "teacher": (lc_teacher or "").strip(), "school": (enrolled_school or "").strip(),
        "vocab": {"type": S("vocab_type", ""), "pre": S("vocab_pre", ""), "post": S("vocab_post", ""),
                  "summary": S("vocab_summary", "")},
        "sounds_write": sounds_write_rows(),
        "biin": biin_rows(), "biin_comments": [(bi_name, S(f"biin_c_{bi}", "") or "") for bi, (bi_name, _) in enumerate(BIIN)],
        "numeracy": S("numeracy", ""),
        "hits": [{"name": h, "elements": S(f"hits_el_{HITS_OPTIONS.index(h)}", []) or [],
                  "comment": S(f"hits_c_{HITS_OPTIONS.index(h)}", "") or ""} for h in (S("hits", []) or [])],
        "rp": [{"name": r_, "comment": S(f"rp_c_{RP_OPTIONS.index(r_)}", "") or ""} for r_ in (S("rp", []) or [])],
        "rp_comments": S("rp_comments", "") or "",
        "wot": S("wot"), "wot_zones": wot_on, "regulation": S("regulation", ""),
        "goals": report_goals,
        "attendance": (days_attended, total_days, attendance_pct),
        "summary": S("summary", ""), "recs": S("recs", ""), "att_comment": S("att_comment", "") or "",
        "att_table": S("att_table") if (inc("attendance") and S("att_table_on")) else None,
        "voice_text": (S("voice_text") or "") if inc("voice") else "",
        "voice_files": (S("voice_files") or []) if inc("voice") else [],
        "appendices": collect_appendices(),
    }


def collect_appendices():
    out = []
    if S("app_recs"):
        out.append({"title": "Transition Recommendations", "text": S("recs", "") or "", "pages": [], "bullets": True})
    for aid in S("apps") or []:
        t_, x_ = (S(f"app_title_{aid}") or "").strip(), (S(f"app_text_{aid}") or "").strip()
        if t_ or x_:
            out.append({"title": t_ or "Additional information", "text": x_, "pages": []})
    for it in S("uploads") or []:
        out.append({"title": it.get("title") or it.get("name") or "Attachment", "text": it.get("text") or "",
                    "pages": it.get("pages") or []})
    return out


# ══════════════════════════════════════════════════════════════════════════════
# WORD DOCUMENT
# ══════════════════════════════════════════════════════════════════════════════
def build_docx(rep):
    from docx import Document
    from docx.shared import Pt, Cm, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml import OxmlElement
    from docx.oxml.ns import qn

    def shade(cell, hex_colour):
        tcPr = cell._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear")
        shd.set(qn("w:color"), "auto")
        shd.set(qn("w:fill"), hex_colour.lstrip("#"))
        tcPr.append(shd)

    def hex_rgb(h):
        h = h.lstrip("#")
        return RGBColor(int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16))

    doc = Document()
    from docx.enum.section import WD_SECTION, WD_ORIENT
    cover_sec = doc.sections[0]
    cover_sec.page_height, cover_sec.page_width = Cm(29.7), Cm(21.0)
    for side in ("left_margin", "right_margin", "top_margin", "bottom_margin"):
        setattr(cover_sec, side, Cm(0))
    cover_sec.header_distance = cover_sec.footer_distance = Cm(0)
    sec = cover_sec
    base = doc.styles["Normal"]
    base.font.name = "Calibri"
    base.font.size = Pt(10.5)

    def heading(text):
        """Full-width navy header bar with white text (CLC report template style)."""
        gap = doc.add_paragraph()
        gap.paragraph_format.space_before = Pt(8)
        gap.paragraph_format.space_after = Pt(0)
        gap.paragraph_format.keep_with_next = True
        bar = doc.add_table(rows=1, cols=1)
        c_ = bar.cell(0, 0)
        shade(c_, HEADER_NAVY)
        p = c_.paragraphs[0]
        p.paragraph_format.space_before = Pt(4)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text)
        r.font.size = Pt(15)
        r.font.name = "Calibri Light"
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        after = doc.add_paragraph()
        after.paragraph_format.space_before = Pt(0)
        after.paragraph_format.space_after = Pt(2)
        after.paragraph_format.keep_with_next = True
        return p

    def sub(text):
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(2)
        p.paragraph_format.keep_with_next = True
        r = p.add_run(text.upper())
        r.bold = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    def blurb(text_, italic=False):
        p_ = doc.add_paragraph()
        p_.paragraph_format.space_after = Pt(6)
        p_.paragraph_format.keep_with_next = True
        r_ = p_.add_run(text_)
        r_.font.size = Pt(9.5)
        r_.italic = italic
        r_.font.color.rgb = RGBColor(0x44, 0x4B, 0x55)
        return p_

    def shade_par(par_, hex_colour):
        pPr = par_._p.get_or_add_pPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), hex_colour.lstrip("#"))
        pPr.append(shd)

    def keep_together(tbl, with_next_rows=True):
        """No row splits across a page, and (optionally) every row stays with the next — keeps a goal card whole."""
        rows_ = tbl.rows
        for ri_, row_ in enumerate(rows_):
            trPr = row_._tr.get_or_add_trPr()
            cs = OxmlElement("w:cantSplit"); cs.set(qn("w:val"), "true"); trPr.append(cs)
            if with_next_rows and ri_ < len(rows_) - 1:
                for cell_ in row_.cells:
                    for par_ in cell_.paragraphs:
                        par_.paragraph_format.keep_with_next = True

    def score_fill(score, mx):
        try:
            pct_ = float(score) / float(mx) * 100
        except Exception:
            return None
        return "B7DE9B" if pct_ >= 90 else "FFE38A" if pct_ >= 70 else "F4A9A3"

    def para(text, empty="Not entered."):
        p = doc.add_paragraph()
        if text and str(text).strip():
            p.add_run(str(text).strip())
        else:
            r = p.add_run(empty)
            r.italic = True
            r.font.color.rgb = RGBColor(0x99, 0x99, 0x99)
        return p

    def paras(text, empty="Not entered."):
        """One Word paragraph per line / paragraph, so drafted paragraphs and • bullets keep their layout."""
        lines = [ln.strip() for ln in str(text or "").split("\n") if ln.strip()]
        if not lines:
            return para("", empty)
        for ln in lines:
            p = para(ln)
            p.paragraph_format.space_after = Pt(4 if ln.startswith("•") else 8)
            if ln.startswith("•"):
                p.paragraph_format.left_indent = Cm(0.5)
                p.paragraph_format.first_line_indent = Cm(-0.4)

    def picture(b64, max_w_cm=17.0, max_h_cm=21.5):
        from PIL import Image as _Im
        raw = base64.b64decode(b64)
        try:
            w_px, h_px = _Im.open(BytesIO(raw)).size
        except Exception:
            return
        w_cm = max_w_cm
        if h_px / max(w_px, 1) * w_cm > max_h_cm:
            w_cm = max_h_cm * w_px / max(h_px, 1)
        pp = doc.add_paragraph()
        pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp.add_run().add_picture(BytesIO(raw), width=Cm(w_cm))

    def att_table(tbl_):
        widths = [Cm(2.4)] + [Cm(3.0)] * 5
        t_ = doc.add_table(rows=1, cols=6)
        t_.style = "Table Grid"
        t_.autofit = False
        hdr_ = t_.rows[0]
        trPr = hdr_._tr.get_or_add_trPr(); th = OxmlElement("w:tblHeader"); th.set(qn("w:val"), "true"); trPr.append(th)
        for i_, h_ in enumerate(["Week"] + BST_DAYS_FULL):
            c_ = hdr_.cells[i_]; c_.width = widths[i_]; shade(c_, HEADER_NAVY)
            c_.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            r_ = c_.paragraphs[0].add_run(h_); r_.bold = True; r_.font.size = Pt(8.5)
            r_.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        for wk in tbl_["weeks"]:
            row_ = t_.add_row()
            trPr = row_._tr.get_or_add_trPr(); cs = OxmlElement("w:cantSplit"); trPr.append(cs)
            row_.height = Cm(0.6)
            for i_ in range(6):
                row_.cells[i_].width = widths[i_]
                row_.cells[i_].vertical_alignment = 1          # centre
            wc = row_.cells[0]; shade(wc, "EEF2EC")
            wc.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            wr = wc.paragraphs[0].add_run(wk["week_label"]); wr.bold = True; wr.font.size = Pt(8.5)
            for i_, cell in enumerate(wk["days"]):
                c_ = row_.cells[i_ + 1]
                if not cell:
                    shade(c_, "F3F4F6"); continue
                stt = _att_cell_status(cell)
                shade(c_, ATT_DAY_COLOURS.get(stt, ATT_DAY_COLOURS["attended"])[0])
                c_.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                lb = c_.paragraphs[0].add_run(cell["label"]); lb.font.size = Pt(8.5); lb.bold = True
                lb.font.color.rgb = (RGBColor(0xFF, 0xFF, 0xFF) if stt in ("attended", "absent", "transition")
                                     else RGBColor(0x33, 0x33, 0x33))
        # colour key — one line of coloured squares
        kp = doc.add_paragraph()
        kp.paragraph_format.space_before = Pt(4)
        kp.paragraph_format.space_after = Pt(0)
        for fill, lbl in ATT_DAY_COLOURS.values():
            sq = kp.add_run("■ " if fill != "FFFFFF" else "□ ")
            sq.font.size = Pt(12)
            sq.font.color.rgb = hex_rgb(fill if fill != "FFFFFF" else "777777")
            lr = kp.add_run(lbl + "      ")
            lr.font.size = Pt(8)
        k_ = doc.add_paragraph()
        k_.paragraph_format.space_before = Pt(3)
        kr = k_.add_run("From the Behaviour Support Tool attendance records"
                        + (" and the Transition Timetable." if tbl_.get("counts", {}).get("transition") else "."))
        kr.italic = True; kr.font.size = Pt(7.5); kr.font.color.rgb = RGBColor(0x77, 0x77, 0x77)

    def table(rows, header=True, widths=None, size=9.5):
        t = doc.add_table(rows=len(rows), cols=len(rows[0]))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                cell = t.cell(i, j)
                cell.text = ""
                run = cell.paragraphs[0].add_run(str(val))
                run.font.size = Pt(size)
                if header and i == 0:
                    run.bold = True
                    shade(cell, "EEF2EC")
                if widths:
                    cell.width = widths[j]
        return t

    # ── cover page (every report type) — full-page artwork in its own section ──
    note = None                     # no list of included sections on the cover
    cover_png = make_cover_png(rep["type"], rep.get("cover_name") or rep["name"], rep["report_date"].strftime("%d/%m/%Y"),
                               rep["school"] or "", note=note)
    cp = doc.paragraphs[0] if doc.paragraphs else doc.add_paragraph()
    cp.paragraph_format.space_before = cp.paragraph_format.space_after = Pt(0)
    cp.paragraph_format.line_spacing = 1.0
    cp.add_run().add_picture(BytesIO(cover_png), width=Cm(21.0), height=Cm(29.55))

    body = doc.add_section(WD_SECTION.NEW_PAGE)
    body.page_height, body.page_width = Cm(29.7), Cm(21.0)
    body.left_margin = body.right_margin = Cm(1.8)
    body.top_margin = body.bottom_margin = Cm(1.6)
    body.header_distance = body.footer_distance = Cm(1.0)
    body.footer.is_linked_to_previous = False
    body.header.is_linked_to_previous = False
    sec = body

    # details strip at the top of page 2 (the cover only carries name / date / site, as on the template)
    fmt = lambda d: d.strftime("%d %B %Y").lstrip("0")
    strip = doc.add_table(rows=1, cols=4)
    strip.style = "Table Grid"
    for j_, (k_, v_) in enumerate([("Student", (rep.get("cover_name") or rep["name"]) + (f" ({rep['program']})" if rep["program"] else "")),
                                   ("School", rep["school"] or "—"), ("LC teacher", rep["teacher"] or "—"),
                                   ("Placement", f"{fmt(rep['pstart'])} – {fmt(rep['pend'])}")]):
        c_ = strip.cell(0, j_)
        shade(c_, "EEF2EC")
        kr_ = c_.paragraphs[0].add_run(k_.upper()); kr_.bold = True; kr_.font.size = Pt(7.5)
        kr_.font.color.rgb = RGBColor(0x55, 0x55, 0x55)
        c_.add_paragraph().add_run(v_).font.size = Pt(9.5)


    if "literacy" in rep["sections"]:
        # ── literacy ──
        heading("Literacy Progress")
        blurb(BLURB["literacy"])
        sub("Word Aware (Vocabulary)")
        blurb(BLURB["vocab"])
        v = rep["vocab"]
        if v["type"] or v["pre"] or v["post"]:
            table([["Assessment", "Pre", "Post"], [v["type"] or "—", v["pre"] or "—", v["post"] or "—"]])
        else:
            para("", empty="Not assessed.")
        sub("Linguistics and Phonics (Sounds-Write)")
        blurb(BLURB["sounds_write"])
        if rep["sounds_write"]:
            lg_ = doc.add_paragraph()
            lr_ = lg_.add_run(SCORE_LEGEND); lr_.font.size = Pt(8.5); lr_.italic = True
            swt = doc.add_table(rows=1 + len(rep["sounds_write"]), cols=5)
            swt.style = "Table Grid"
            for j_, h_ in enumerate(["Skill", "Pre", "Post", "Change", "Summary of outcome"]):
                c_ = swt.cell(0, j_); r_ = c_.paragraphs[0].add_run(h_); r_.bold = True; r_.font.size = Pt(9)
                shade(c_, "EEF2EC")
            for i_, s_ in enumerate(rep["sounds_write"], start=1):
                sk = swt.cell(i_, 0)
                r_ = sk.paragraphs[0].add_run(s_["skill"]); r_.bold = True; r_.font.size = Pt(9)
                if SOUNDS_WRITE_DESC.get(s_["skill"]):
                    d_ = sk.add_paragraph().add_run(SOUNDS_WRITE_DESC[s_["skill"]]); d_.italic = True; d_.font.size = Pt(8)
                for j_, val in ((1, s_["pre"]), (2, s_["post"])):
                    c_ = swt.cell(i_, j_)
                    c_.paragraphs[0].add_run(f"{val} / {s_['max']}" if val else "—").font.size = Pt(9)
                    if val and score_fill(val, s_["max"]):
                        shade(c_, score_fill(val, s_["max"]))
                swt.cell(i_, 3).paragraphs[0].add_run(s_["change"] or "—").font.size = Pt(9)
                swt.cell(i_, 4).paragraphs[0].add_run(s_["summary"] or "").font.size = Pt(9)
            for row_ in swt.rows:
                for j_, w in enumerate([Cm(4.6), Cm(2.0), Cm(2.0), Cm(1.6), Cm(7.2)]):
                    row_.cells[j_].width = w
        else:
            para("", empty="Not assessed.")
        sub("Literacy summary and next steps")
        paras(v["summary"])

    if "numeracy" in rep["sections"]:
        heading("Numeracy Progress")
        sub("Big Ideas in Number")
        blurb(BLURB["biin"])
        if rep["biin"]:
            lg = doc.add_paragraph()
            for label, fill in [("Mastered (90–100%)", "B7DE9B"), ("Developing (70–80%)", "FFE38A"), ("Needs improvement (< 70%)", "F4A9A3")]:
                r_ = lg.add_run(f"  {label}  ")
                r_.font.size = Pt(8.5)
                rPr = r_._element.get_or_add_rPr()
                shd = OxmlElement("w:shd"); shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto"); shd.set(qn("w:fill"), fill)
                rPr.append(shd)
                lg.add_run("  ")
            # one block of rows per big idea; Big idea and Summary cells are merged down the block
            comments = dict(rep["biin_comments"])
            blocks = []
            for bi_name, _ in BIIN:
                rows_ = [r for r in rep["biin"] if r["big_idea"] == bi_name]
                if rows_ or (comments.get(bi_name) or "").strip():
                    blocks.append((bi_name, rows_ or [{"element": "Not assessed", "pre": "", "post": "", "progress": ""}],
                                   (comments.get(bi_name) or "").strip()))
            n_rows = sum(len(r_) for _, r_, _ in blocks)
            bt = doc.add_table(rows=1 + n_rows, cols=6)
            bt.style = "Table Grid"
            bt.autofit = False
            widths = [Cm(2.5), Cm(3.4), Cm(2.4), Cm(2.4), Cm(1.8), Cm(5.4)]
            for j, h in enumerate(["Big idea", "Element", "Pre", "Post", "Progress", "Summary of outcome"]):
                c = bt.cell(0, j)
                run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
                shade(c, "EEF2EC")
            trPr = bt.rows[0]._tr.get_or_add_trPr(); th_ = OxmlElement("w:tblHeader"); th_.set(qn("w:val"), "true"); trPr.append(th_)
            ri = 1
            for bi_name, rows_, comment in blocks:
                first, last = ri, ri + len(rows_) - 1
                for row in rows_:
                    vals = [row["element"], row["pre"] or "—", row["post"] or "—", row["progress"] or ""]
                    for j, val in enumerate(vals, start=1):
                        c = bt.cell(ri, j)
                        run = c.paragraphs[0].add_run(val); run.font.size = Pt(8.5)
                        if row["element"] == "Not assessed":
                            run.italic = True
                        if j in (2, 3) and val in BIIN_FILL:
                            shade(c, BIIN_FILL[val])
                    tr_ = bt.rows[ri]._tr.get_or_add_trPr(); cs_ = OxmlElement("w:cantSplit"); tr_.append(cs_)
                    ri += 1
                bc = bt.cell(first, 0).merge(bt.cell(last, 0)) if last > first else bt.cell(first, 0)
                br = bc.paragraphs[0].add_run(bi_name); br.bold = True; br.font.size = Pt(9)
                sc = bt.cell(first, 5).merge(bt.cell(last, 5)) if last > first else bt.cell(first, 5)
                for k_, ln in enumerate([x.strip() for x in comment.split("\n") if x.strip()] or [""]):
                    p_ = sc.paragraphs[0] if k_ == 0 else sc.add_paragraph()
                    p_.add_run(ln).font.size = Pt(8.5)
                for cell_ in (bc, sc):
                    cell_.vertical_alignment = 0            # top
            for j, w in enumerate(widths):
                bt.columns[j].width = w                       # grid widths (Word + LibreOffice honour these)
            for row_ in bt.rows:
                for j, w in enumerate(widths):
                    row_.cells[j].width = w
        else:
            para("", empty="Not assessed.")
            for bi_name, comment in rep["biin_comments"]:      # comments without any results entered
                if comment.strip():
                    p = doc.add_paragraph()
                    p.paragraph_format.space_before = Pt(4)
                    p.add_run(f"{bi_name} — ").bold = True
                    p.add_run(comment.strip())
        if rep["numeracy"].strip():
            sub("Numeracy summary and next steps")
            paras(rep["numeracy"])

    if "hits" in rep["sections"]:
        heading("Pedagogical Strategies (HITS)")
        blurb(BLURB["hits"])
        chosen_ = {h["name"]: h["elements"] for h in rep["hits"]}
        mp_ = doc.add_paragraph()
        mp_.alignment = WD_ALIGN_PARAGRAPH.CENTER
        mp_.add_run().add_picture(BytesIO(make_hits_matrix_png(chosen_)), width=Cm(17.2))
        if rep["hits"]:
            cap_ = doc.add_paragraph()
            cr_ = cap_.add_run("Highlighted: the strategies and key elements that promoted positive engagement for this student.")
            cr_.italic = True; cr_.font.size = Pt(8.5)
            sub("Comments")
            ht = doc.add_table(rows=len(rep["hits"]), cols=2)
            ht.style = "Table Grid"
            for i, h in enumerate(rep["hits"]):
                sc = ht.cell(i, 0)
                sr = sc.paragraphs[0].add_run(h["name"]); sr.font.size = Pt(10)
                sr.font.color.rgb = RGBColor(0x7F, 0x60, 0x00)
                shade(sc, "FFD966")
                cc_ = ht.cell(i, 1)
                # key elements the teacher chose for this strategy, then how it supported the student
                if h["elements"]:
                    kh = cc_.paragraphs[0].add_run("Key elements used:"); kh.bold = True; kh.font.size = Pt(9)
                    for el in h["elements"]:
                        ep = cc_.add_paragraph()
                        ep.paragraph_format.left_indent = Cm(0.3)
                        ep.paragraph_format.space_after = Pt(0)
                        er = ep.add_run("• " + el); er.font.size = Pt(9)
                    hp = cc_.add_paragraph()
                    hp.paragraph_format.space_before = Pt(4)
                else:
                    hp = cc_.paragraphs[0]
                if h["comment"].strip():
                    hh = hp.add_run("How it supported the student: "); hh.bold = True; hh.font.size = Pt(9)
                cr = hp.add_run(h["comment"].strip() or ("—" if not h["elements"] else "")); cr.font.size = Pt(9.5)
            ht.autofit = False
            ht.columns[0].width, ht.columns[1].width = Cm(4.2), Cm(13.2)
            for row_ in ht.rows:
                row_.cells[0].width, row_.cells[1].width = Cm(4.2), Cm(13.2)
            keep_together(ht, with_next_rows=False)
        else:
            para("", empty="Not entered.")

    if "restorative" in rep["sections"]:
        heading("Restorative strategies promoting: Relational Safety and Relational Connection")
        ft = doc.add_table(rows=1, cols=2)
        fl_c, bl_c = ft.cell(0, 0), ft.cell(0, 1)
        fl_c.width, bl_c.width = Cm(8.6), Cm(8.8)
        fl_c.paragraphs[0].add_run().add_picture(b64img(RP_FLOWER_JPG_B64), width=Cm(8.3))
        bp = bl_c.paragraphs[0]
        br = bp.add_run(RP_BLURB_INTRO); br.font.size = Pt(9.5)
        ap = bl_c.add_paragraph(); ar = ap.add_run("The adult:"); ar.italic = True; ar.font.size = Pt(9.5)
        for n_, step in enumerate(RP_BLURB_STEPS, start=1):
            sp = bl_c.add_paragraph(); sr = sp.add_run(f"{n_}. {step}"); sr.italic = True; sr.font.size = Pt(9)
            sp.paragraph_format.space_after = Pt(3)
        cp_ = bl_c.add_paragraph(); cr_ = cp_.add_run(RP_CITATION); cr_.italic = True; cr_.font.size = Pt(7)
        keep_together(ft, with_next_rows=False)
        cr_.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
        sub("Comments")
        if rep["rp"]:
            ct = doc.add_table(rows=len(rep["rp"]), cols=2)
            ct.style = "Table Grid"
            for i_, r_ in enumerate(rep["rp"]):
                pc_, tc_ = ct.cell(i_, 0), ct.cell(i_, 1)
                pc_.width, tc_.width = Cm(1.8), Cm(15.6)
                pc_.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
                pc_.paragraphs[0].add_run().add_picture(b64img(RP_PETAL_JPG_B64[r_["name"]]), width=Cm(1.3))
                nr_ = tc_.paragraphs[0].add_run(r_["name"]); nr_.bold = True; nr_.font.size = Pt(10)
                tx_ = tc_.add_paragraph().add_run(r_["comment"].strip() or "—"); tx_.font.size = Pt(9.5)
            keep_together(ct, with_next_rows=False)
        if rep["rp_comments"].strip():
            para(rep["rp_comments"])
        elif not rep["rp"]:
            para("", empty="Not entered.")

    if "regulation" in rep["sections"]:
        # ── regulation profile — landscape so the four columns fit ──
        land = doc.add_section(WD_SECTION.NEW_PAGE)
        land.orientation = WD_ORIENT.LANDSCAPE
        land.page_width, land.page_height = Cm(29.7), Cm(21.0)
        land.left_margin = land.right_margin = Cm(1.5)
        land.top_margin = land.bottom_margin = Cm(1.2)
        heading("Regulation Profile (Window of Tolerance)")
        zones = rep["wot_zones"] or []
        if rep["wot"] and zones:
            # Pick the largest text size at which the whole table (plus the note and comments) fits on this
            # one landscape page. Rough line maths: Calibri averages ~0.0185 cm per character per point.
            col_w = [4.6, 7.4, 7.4, 7.4]                       # cm — 26.8 of the 26.9 cm between the margins
            avail = 21.0 - 1.2 - 1.2 - 2.2                     # page − margins − header bar & gaps
            reg_txt = (rep["regulation"] or "").strip()

            def lines_for(text, width_cm, pt):
                cpl = max(8, int((width_cm - 0.25) / (WOT_CHAR_CM * pt)))
                return sum(max(1, -(-len(part) // cpl)) for part in str(text).split("\n"))

            def table_height(pt, with_desc, with_reg):
                lh = pt * WOT_LINE_K * 0.0353
                h = lh * 1.2 + 0.12                            # header row
                for z in zones:
                    left = lh * 1.15 + lh * 0.9 + (lines_for(WOT_ZONE_DESC.get(z["id"], ""), col_w[0], pt - 1.5)
                                                   * (pt - 1.5) * WOT_LINE_K * 0.0353 if with_desc else 0)
                    cols_ = [sum(lines_for("• " + it, w_, pt) for it in (rep["wot"]["data"][z["id"]][c_] or ["—"])) * lh
                             for (c_, _), w_ in zip(WOT_COLS, col_w[1:])]
                    h += max([left] + cols_) + 0.14
                h += 0.55                                      # source note
                if with_reg and reg_txt:
                    rpt = pt + 0.5
                    h += lines_for(reg_txt, sum(col_w) - 0.5, rpt) * rpt * WOT_LINE_K * 0.0353 + 0.3
                return h
            # 1st choice: table + comments on the page at a readable size; otherwise keep the TABLE on one page
            # (comments then continue on the next page)
            fit_pt, with_desc = 5.5, False
            found = False
            for with_desc, with_reg, min_pt in ((True, True, 7.0), (False, True, 7.0), (True, False, 6.5), (False, False, 5.5)):
                for pt in (10.0, 9.5, 9.0, 8.5, 8.0, 7.5, 7.0, 6.5, 6.0, 5.5):
                    if pt < min_pt:
                        break
                    if table_height(pt, with_desc, with_reg) <= avail:
                        fit_pt, found = pt, True
                        break
                if found:
                    break
            fs = fit_pt
            t = doc.add_table(rows=1 + len(zones), cols=4)
            t.autofit = False
            tblPr = t._tbl.tblPr
            mar = OxmlElement("w:tblCellMar")
            for side, val in (("top", 30), ("bottom", 30), ("left", 70), ("right", 70)):
                e_ = OxmlElement(f"w:{side}"); e_.set(qn("w:w"), str(val)); e_.set(qn("w:type"), "dxa"); mar.append(e_)
            tblPr.append(mar)
            t.style = "Table Grid"
            hdr = ["Zone"] + [lbl for _, lbl in WOT_COLS]
            for j, h in enumerate(hdr):
                c = t.cell(0, j)
                run = c.paragraphs[0].add_run(h)
                run.bold = True
                run.font.size = Pt(fs + 0.5)
                shade(c, "EEF2EC")
            for i, z in enumerate(zones, start=1):
                zc = t.cell(i, 0)
                zr = zc.paragraphs[0].add_run(z["name"])
                zr.bold = True
                zr.font.size = Pt(fs + 1)
                zr.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                tg = zc.add_paragraph().add_run(z["tag"])
                tg.italic = True
                tg.font.size = Pt(fs - 0.5)
                tg.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                if with_desc:
                    zd = zc.add_paragraph().add_run(WOT_ZONE_DESC.get(z["id"], ""))
                    zd.font.size = Pt(max(5.5, fs - 1.5))
                    zd.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
                shade(zc, z["color"])
                for j, (col, _) in enumerate(WOT_COLS, start=1):
                    c = t.cell(i, j)
                    shade(c, z["tint"])
                    items = rep["wot"]["data"][z["id"]][col]
                    if not items:
                        c.paragraphs[0].add_run("—").font.size = Pt(fs)
                    for k, it in enumerate(items):
                        p = c.paragraphs[0] if k == 0 else c.add_paragraph()
                        run = p.add_run("• " + it)
                        run.font.size = Pt(fs)
            for row in t.rows:
                for j_, w_ in enumerate(col_w):
                    row.cells[j_].width = Cm(w_)
                for cell_ in row.cells:
                    for par_ in cell_.paragraphs:
                        par_.paragraph_format.space_before = Pt(0)
                        par_.paragraph_format.space_after = Pt(0)
                        par_.paragraph_format.line_spacing = 1.0
            keep_together(t, with_next_rows=True)
            note = doc.add_paragraph()
            note.paragraph_format.space_before = Pt(2)
            note.paragraph_format.space_after = Pt(2)
            nr = note.add_run(f"From the Window of Tolerance Builder ({rep['initials']}), "
                              f"updated {fmt_date(rep['wot']['updated_at'])}.")
            nr.italic = True
            nr.font.size = Pt(7.5)
            nr.font.color.rgb = RGBColor(0x77, 0x77, 0x77)
            if reg_txt:
                rp_ = para(reg_txt)
                for r_ in rp_.runs:
                    r_.font.size = Pt(fs + 0.5)
        else:
            para(rep["regulation"])

    if "regulation" in rep["sections"] and (any(k in rep["sections"] for k in ("smartar", "voice", "attendance", "summary"))
                                            or rep["appendices"]):
        port = doc.add_section(WD_SECTION.NEW_PAGE)
        port.orientation = WD_ORIENT.PORTRAIT
        port.page_width, port.page_height = Cm(21.0), Cm(29.7)
        port.left_margin = port.right_margin = Cm(1.8)
        port.top_margin = port.bottom_margin = Cm(1.6)

    if "smartar" in rep["sections"]:
        # ── SMARTAR goals ──
        heading("Behaviour Progress: SMARTAR Goals")
        blurb(BLURB["smartar"])
        if not rep["goals"]:
            para("", empty="No SMARTAR goals recorded in the SMARTAR Goal Builder.")
        else:
            ov = doc.add_table(rows=1 + len(rep["goals"]), cols=4)
            ov.style = "Table Grid"
            for j, h in enumerate(["#", "Exclusion goal", "Translated SMARTAR goal", "Status"]):
                c = ov.cell(0, j)
                run = c.paragraphs[0].add_run(h); run.bold = True; run.font.size = Pt(9)
                shade(c, "EEF2EC")
            for i, g in enumerate(rep["goals"], start=1):
                vals = [str(i), g["excl"] or "—", g["smartar"] or "—",
                        "Active" if g["active"] else f"Archived {fmt_date(g['archived_at'], long=False)}"]
                for j, val in enumerate(vals):
                    ov.cell(i, j).paragraphs[0].add_run(val).font.size = Pt(8.5)
            for row_ in ov.rows:
                for j, w in enumerate([Cm(0.8), Cm(5.2), Cm(9.0), Cm(2.4)]):
                    row_.cells[j].width = w
            sub("Goal Attainment Scale (GAS)")
            blurb(BLURB["gas"])

        for n, g in enumerate(rep["goals"], start=1):
            st_ = g["stats"]
            card = doc.add_table(rows=3, cols=2)
            card.style = "Table Grid"
            card.alignment = WD_TABLE_ALIGNMENT.CENTER
            # header bar — "Goal n 🟢/🟠 — status"
            hd = card.cell(0, 0).merge(card.cell(0, 1))
            shade(hd, "DDEFE3" if g["active"] else "FCE8CF")
            hr_ = hd.paragraphs[0].add_run(f"Goal {n}  ")
            hr_.bold = True; hr_.font.size = Pt(11)
            sr_ = hd.paragraphs[0].add_run(
                "🟢 Active goal" if g["active"] else
                f"🟠 Archived {fmt_date(g['archived_at'])}" + (f" — {g['archive_reason']}" if g["archive_reason"] else ""))
            sr_.font.size = Pt(9.5); sr_.bold = True
            sr_.font.color.rgb = hex_rgb("#2E7A48" if g["active"] else "#B9761A")
            # pie | details
            pic, det = card.cell(1, 0), card.cell(1, 1)
            pic.width, det.width = Cm(6.0), Cm(11.4)
            if g["pie"]:
                pic.paragraphs[0].add_run().add_picture(BytesIO(g["pie"]), width=Cm(5.6))
            else:
                nr_ = pic.paragraphs[0].add_run("No tracking recorded for this goal yet."); nr_.italic = True; nr_.font.size = Pt(9)
            d0 = det.paragraphs[0]
            _first = [True]

            def det_par():
                if _first[0]:
                    _first[0] = False
                    return d0
                return det.add_paragraph()
            if st_["total"]:
                _first[0] = False
                r_ = d0.add_run(f"{st_['total']} observations · {fmt_date(st_['first'], False)} → {fmt_date(st_['last'], False)} "
                                f"· tracking period: {g['tracking_period']}")
                r_.font.size = Pt(9)
                d1 = det.add_paragraph()
                r_ = d1.add_run(f"{TREND_TEXT[st_['trend']]} · "); r_.font.size = Pt(9)
                r_ = d1.add_run(f"{st_['at_or_above']}%"); r_.bold = True; r_.font.size = Pt(9)
                r_ = d1.add_run(" at Expected or better"); r_.font.size = Pt(9)
            if g["excl"].strip():
                de = det_par(); de.paragraph_format.space_before = Pt(6) if not de is d0 else Pt(0)
                r_ = de.add_run("🏫 Exclusion goal: "); r_.bold = True; r_.font.size = Pt(9.5)
                r_ = de.add_run(g["excl"].strip()); r_.font.size = Pt(9.5)
            dsm = det_par(); dsm.paragraph_format.space_before = Pt(6) if not dsm is d0 else Pt(0)
            r_ = dsm.add_run("🎯 SMARTAR goal: "); r_.bold = True; r_.font.size = Pt(9.5)
            r_ = dsm.add_run(g["smartar"].strip() or "—"); r_.font.size = Pt(9.5)
            # Goal Attainment Scale, current level highlighted
            gas_c = card.cell(2, 0).merge(card.cell(2, 1))
            gh = gas_c.paragraphs[0].add_run("Goal Attainment Scale")
            gh.bold = True; gh.font.size = Pt(9.5)
            for lvl in LEVEL_ORDER:
                desc = g["gas"].get(lvl, "")
                if not desc:
                    continue
                is_cur = g["current"] == lvl
                lp = gas_c.add_paragraph()
                lp.paragraph_format.space_after = Pt(1)
                lr = lp.add_run(f"{LEVEL_EMOJI[lvl]} {lvl}"); lr.bold = True; lr.font.size = Pt(9)
                lr.font.color.rgb = hex_rgb(LEVEL_COLOR[lvl])
                dr = lp.add_run(f" — {desc}"); dr.font.size = Pt(9); dr.bold = is_cur
                if is_cur:
                    cr = lp.add_run("   ◀ currently achieving"); cr.bold = True; cr.font.size = Pt(8.5)
                    cr.font.color.rgb = hex_rgb(LEVEL_COLOR[lvl])
                    shade_par(lp, "E3EFE8")
            for c_ in (pic, det, gas_c):
                for par_ in c_.paragraphs:
                    par_.paragraph_format.space_after = Pt(2)
            keep_together(card)
            doc.add_paragraph().paragraph_format.space_after = Pt(2)

    # ── student voice (only if something was entered) ──
    if "voice" in rep["sections"] and (rep["voice_text"].strip() or rep["voice_files"]):
        heading("Student Voice and Agency")
        blurb(VOICE_BLURB)
        if rep["voice_text"].strip():
            for ln in [x.strip() for x in rep["voice_text"].split("\n") if x.strip()]:
                vp = para(ln)
                vp.paragraph_format.left_indent = Cm(0.4)
                for r_ in vp.runs:
                    r_.italic = True
        for it in rep["voice_files"]:
            if it.get("title"):
                sub(it["title"])
            if it.get("text"):
                paras(it["text"])
            for pg in it.get("pages") or []:
                picture(pg, max_h_cm=12.0)

    # ── attendance + summaries ──
    if "attendance" in rep["sections"]:
        heading("Attendance")
        a, t_, pct = rep["attendance"]
        para(f"{rep['name']} attended the Learning Program {a} of {t_} days ({pct:.1f}%).")
        if rep.get("att_comment", "").strip():
            para(rep["att_comment"])
        if rep.get("att_table"):
            sub("Attendance by week")
            att_table(rep["att_table"])
    if "summary" in rep["sections"]:
        heading("Overall Progress Summary")
        paras(rep["summary"])
    # ── appendices: each on its own page ──
    for n_, ap in enumerate(rep["appendices"]):
        doc.add_page_break()
        letter = chr(65 + n_) if n_ < 26 else str(n_ + 1)
        heading(f"Appendix {letter}: {ap['title']}")
        if ap.get("text", "").strip() or not ap.get("pages"):
            paras(ap.get("text", ""))
        for k_, pg in enumerate(ap.get("pages") or []):
            if k_:
                doc.add_page_break()
            picture(pg, max_h_cm=22.5 if k_ or not ap.get("text") else 18.0)

    foot = sec.footer.paragraphs[0]
    foot.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = foot.add_run(f"{rep['type']} | Cowandilla Learning Centre LBU | {rep.get('footer_name') or rep['initials']} | "
                      f"Generated {datetime.now().strftime('%d %b %Y')}")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor(0x88, 0x88, 0x88)

    buf = BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ══════════════════════════════════════════════════════════════════════════════
# TAB 2 — PREVIEW
# ══════════════════════════════════════════════════════════════════════════════
with tab2:
    rep = collect_report(DISPLAY_NAME)
    st.header(f"{rep['type']}: {rep['name']}")
    st.markdown(
        f"**Report date:** {rep['report_date'].strftime('%d %B %Y').lstrip('0')} · "
        f"**Placement:** {rep['pstart'].strftime('%d %b %Y')} to {rep['pend'].strftime('%d %b %Y')}  \n"
        f"**LC teacher:** {rep['teacher'] or '—'} · **Enrolled school:** {rep['school'] or '—'}"
    )
    st.markdown("---")

    if "literacy" in rep["sections"]:
        st.markdown("#### Literacy Progress")
        st.caption(BLURB["literacy"])
        v = rep["vocab"]
        if v["pre"] or v["post"]:
            st.write(f"Word Aware ({v['type'] or 'assessment'}): pre {v['pre'] or '—'}, post {v['post'] or '—'}")
        if rep["sounds_write"]:
            st.dataframe(pd.DataFrame(rep["sounds_write"]).rename(columns={
                "skill": "Skill", "max": "Max", "pre": "Pre", "post": "Post", "change": "Change", "summary": "Summary"}),
                hide_index=True, use_container_width=True)
        if v["summary"]:
            st.markdown("**Literacy summary and next steps**")
            st.write(v["summary"])
    if "numeracy" in rep["sections"]:
        st.markdown("#### Numeracy Progress")
        st.caption(BLURB["biin"])
        if rep["biin"]:
            import html as _h
            _comments = dict(rep["biin_comments"])
            td = "border:1px solid #cfd6cc;padding:5px;vertical-align:top"
            html_ = ("<table style='width:100%;border-collapse:collapse;font-size:0.8rem'><tr>" +
                     "".join(f"<th style='{td};background:#EEF2EC;text-align:left'>{h}</th>"
                             for h in ["Big idea", "Element", "Pre", "Post", "Progress", "Summary of outcome"]) + "</tr>")
            for bi_name, _ in BIIN:
                rows_ = [r for r in rep["biin"] if r["big_idea"] == bi_name]
                com = (_comments.get(bi_name) or "").strip()
                if not rows_ and not com:
                    continue
                rows_ = rows_ or [{"element": "<i>Not assessed</i>", "pre": "", "post": "", "progress": ""}]
                for k_, r in enumerate(rows_):
                    html_ += "<tr>"
                    if k_ == 0:
                        html_ += f"<td rowspan='{len(rows_)}' style='{td};font-weight:600'>{_h.escape(bi_name)}</td>"
                    html_ += f"<td style='{td}'>{r['element']}</td>"
                    for v in (r["pre"], r["post"]):
                        bg = "#" + BIIN_FILL[v] if v in BIIN_FILL else "transparent"
                        html_ += f"<td style='{td};background:{bg}'>{_h.escape(v or '—')}</td>"
                    html_ += f"<td style='{td}'>{_h.escape(r['progress'] or '')}</td>"
                    if k_ == 0:
                        html_ += (f"<td rowspan='{len(rows_)}' style='{td}'>"
                                  + _h.escape(com).replace(chr(10), "<br>") + "</td>")
                    html_ += "</tr>"
            st.markdown(html_ + "</table>", unsafe_allow_html=True)
        else:
            st.write("_BIiN not assessed._")
            for bi_name, comment in rep["biin_comments"]:
                if comment.strip():
                    st.write(f"**{bi_name}** — {comment}")
        if rep["numeracy"]:
            st.markdown("**Numeracy summary and next steps**")
            st.write(rep["numeracy"])
    if "hits" in rep["sections"]:
        st.markdown("#### Pedagogical Strategies (HITS)")
        st.caption(BLURB["hits"])
        st.image(make_hits_matrix_png({h["name"]: h["elements"] for h in rep["hits"]}, dpi=110), use_container_width=True)
        if not rep["hits"]:
            st.write("_None selected_")
        for h in rep["hits"]:
            st.markdown(f"**{h['name']}**" + ("" if not h["elements"] else "  \n" + "  \n".join("• " + e for e in h["elements"])))
            if h["comment"]:
                st.write(h["comment"])
    if "restorative" in rep["sections"]:
        st.markdown("#### Restorative strategies promoting: Relational Safety and Relational Connection")
        fpc, fbc = st.columns([1, 1])
        fpc.image(b64img(RP_FLOWER_JPG_B64), use_container_width=True)
        fbc.caption(RP_BLURB_INTRO + " The adult: " + " ".join(f"{n}. {t}" for n, t in enumerate(RP_BLURB_STEPS, start=1)))
        if not rep["rp"]:
            st.write("_None selected_")
        for r_ in rep["rp"]:
            pc_, tc_ = st.columns([1, 14])
            pc_.image(b64img(RP_PETAL_JPG_B64[r_["name"]]), width=44)
            tc_.markdown(f"**{r_['name']}**  \n{r_['comment'] or '—'}")
        if rep["rp_comments"]:
            st.write(rep["rp_comments"])

    if "regulation" in rep["sections"]:
        st.markdown("#### Regulation Profile (Window of Tolerance)")
        if rep["wot"] and rep["wot_zones"]:
            html = ("<table style='width:100%;border-collapse:collapse;font-size:0.82rem'><tr>"
                    + "".join(f"<th style='border:1px solid #cfd6cc;background:#EEF2EC;padding:5px;text-align:left'>{h}</th>"
                              for h in ["Zone"] + [l for _, l in WOT_COLS]) + "</tr>")
            for z in rep["wot_zones"]:
                html += (f"<tr><td style='border:1px solid #cfd6cc;background:{z['color']};color:#fff;padding:6px;width:18%'>"
                         f"<b>{z['name']}</b><br><i style='font-size:0.75rem'>{z['tag']}</i></td>")
                for col, _ in WOT_COLS:
                    items = rep["wot"]["data"][z["id"]][col]
                    body = "<ul style='margin:0;padding-left:16px'>" + "".join(f"<li>{t}</li>" for t in items) + "</ul>" if items else "—"
                    html += f"<td style='border:1px solid #cfd6cc;background:{z['tint']};padding:6px;vertical-align:top'>{body}</td>"
                html += "</tr>"
            st.markdown(html + "</table>", unsafe_allow_html=True)
        st.write(rep["regulation"] or ("" if rep["wot_zones"] else "_Not entered._"))

    if "smartar" in rep["sections"]:
        st.markdown("#### Behaviour Progress: SMARTAR Goals")
        st.caption(BLURB["smartar"])
        if not rep["goals"]:
            st.write("_No goals entered._")
        for n, g in enumerate(rep["goals"], start=1):
            st.markdown(f"**Goal {n}**" + (" — 🟢 Active" if g["active"] else f" — 🟠 Archived {fmt_date(g['archived_at'])}"))
            if g["excl"].strip():
                st.write(f"**Exclusion goal:** {g['excl']}")
            st.write(f"**SMARTAR goal:** {g['smartar']}")
            if g["source"] == "builder":
                c1, c2 = st.columns([1, 2])
                if g["pie"]:
                    c1.image(g["pie"], use_container_width=True)
                s_ = g["stats"]
                if s_["total"]:
                    c2.write(f"{s_['total']} observations, {fmt_date(s_['first'])} to {fmt_date(s_['last'])}. "
                             f"{s_['at_or_above']}% at Expected or better. {TREND_TEXT[s_['trend']]}")
            st.write("**Current level:** " + LEVEL_EMOJI[g["current"]] + " " + g["current"]
                     + (f" — {g['gas'][g['current']]}" if g["gas"].get(g["current"]) else ""))

    if "voice" in rep["sections"] and (rep["voice_text"].strip() or rep["voice_files"]):
        st.markdown("#### Student Voice and Agency")
        st.caption(VOICE_BLURB)
        if rep["voice_text"].strip():
            st.markdown("\n\n".join(f"> *{x.strip()}*" for x in rep["voice_text"].split("\n") if x.strip()))
        for it in rep["voice_files"]:
            if it.get("title"):
                st.markdown(f"**{it['title']}**")
            if it.get("text"):
                st.write(it["text"])
            for pg in it.get("pages") or []:
                st.image(base64.b64decode(pg), width=420)

    if "attendance" in rep["sections"]:
        st.markdown("#### Attendance")
        a, t_, pct = rep["attendance"]
        st.write(f"{a} of {t_} days ({pct:.1f}%)")
        if rep.get("att_comment"):
            st.write(rep["att_comment"])
        if rep.get("att_table"):
            st.markdown(att_table_html(rep["att_table"]), unsafe_allow_html=True)
    if "summary" in rep["sections"]:
        st.markdown("#### Overall Progress Summary")
        st.write(rep["summary"] or "_Not entered._")
    for n_, ap in enumerate(rep["appendices"]):
        st.markdown(f"#### Appendix {chr(65 + n_) if n_ < 26 else n_ + 1}: {ap['title']}")
        if ap.get("text"):
            st.write(ap["text"])
        for pg in ap.get("pages") or []:
            st.image(base64.b64decode(pg), use_container_width=True)
        if not ap.get("text") and not ap.get("pages"):
            st.write("_Not entered._")
    if not rep["sections"]:
        st.info("Only the cover page is included so far — choose sections in the sidebar.")


# ══════════════════════════════════════════════════════════════════════════════
# TAB 3 — GENERATE
# ══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.header(f"Generate {REPORT_TYPE}")
    rep = collect_report(DISPLAY_NAME)
    filled = {
        "literacy": bool(rep["vocab"]["summary"] or rep["vocab"]["pre"] or rep["sounds_write"]),
        "numeracy": bool(rep["biin"] or rep["numeracy"]), "hits": bool(rep["hits"]),
        "restorative": bool(rep["rp"] or rep["rp_comments"]),
        "regulation": bool(rep["regulation"] or rep["wot_zones"]), "smartar": bool(rep["goals"]),
        "attendance": rep["attendance"][0] > 0, "summary": bool(rep["summary"]),
        "voice": bool(rep["voice_text"].strip() or rep["voice_files"]),
    }
    checks = [("Cover page — LC Teacher", bool(rep["teacher"])), ("Cover page — Enrolled School", bool(rep["school"]))]
    checks += [(SECTION_LABEL[k], filled[k]) for k, _ in SECTIONS if k in rep["sections"]]
    checks += [(f"Appendix {chr(65 + n_) if n_ < 26 else n_ + 1}: {ap['title']}", bool(ap.get("text") or ap.get("pages")))
               for n_, ap in enumerate(rep["appendices"])]
    cc = st.columns(2)
    for i, (label, ok) in enumerate(checks):
        cc[i % 2].markdown(("✅ " if ok else "⬜ ") + label)

    if not rep["teacher"]:
        st.error("Please enter the LC Teacher name in the sidebar.")
    else:
        today_tag = datetime.now().strftime("%Y%m%d")
        type_tag = REPORT_TYPE.replace(" ", "_")

        # ── 1. Draft — initials only ──
        st.markdown("### 1 · Draft (initials only)")
        st.caption(f"Use while the report is being built. Everything shows **{INITIALS}** — no names.")
        docx_bytes = build_docx(rep)
        st.download_button(
            f"📄 Download draft {REPORT_TYPE} (Word)", data=docx_bytes, use_container_width=True,
            file_name=f"{INITIALS}_{type_tag}_DRAFT_{today_tag}.docx", key="tr_dl_draft",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

        # ── 2. Finalise — add the student's name ──
        st.markdown("---")
        st.markdown("### 2 · Finalise report")
        if S("finalised"):
            fin = S("finalised")
            st.success(f"✅ This {REPORT_TYPE} was finalised on {fmt_date(fin.get('at'))} by {fin.get('by', '')}. "
                       "If you change anything, finalise again to download an updated final copy.")
        st.caption("Finalising adds the student's name for the copy that goes to the school. The name replaces "
                   f"**{INITIALS}** everywhere in the report (cover page uses the full name). The name is **never "
                   "saved** — the saved report and the Document Archive copy stay initials-only, so you'll re-enter "
                   "the name if you finalise again later.")
        st.session_state.setdefault("tr_fin_school", S("school", "") or "")
        with st.form("tr_fin_form", border=True):
            fc1, fc2 = st.columns(2)
            fc1.text_input("Student's full name *", key="tr_fin_full", placeholder="e.g. Samuel Demo")
            fc2.text_input("Name to use in the report", key="tr_fin_pref",
                           placeholder="Leave blank to use their first name — or a preferred name, e.g. Sam")
            st.text_input("Enrolled school *", key="tr_fin_school")
            st.form_submit_button(f"✅ Finalise {REPORT_TYPE}", type="primary", use_container_width=True,
                                  on_click=finalise_report, args=(student, (lc_teacher or "").strip()))
        if S("fin_error"):
            st.error(S("fin_error"))
        if S("fin_saved_msg"):
            st.caption(S("fin_saved_msg"))

        if S("fin_ready") and (S("fin_full") or "").strip():
            full_ = S("fin_full").strip()
            pref_ = (S("fin_pref") or "").strip() or full_.split()[0]
            final_rep = personalise(collect_report(INITIALS), INITIALS, pref_, full_, S("fin_school").strip())
            final_bytes = build_docx(final_rep)
            safe_ = re.sub(r"[^A-Za-z0-9]+", "_", full_).strip("_")
            st.download_button(
                f"📄 Download FINAL {REPORT_TYPE} for {pref_} (Word)", data=final_bytes, type="primary",
                use_container_width=True, file_name=f"{safe_}_{type_tag}_{today_tag}.docx", key="tr_dl_final",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
            st.caption(f"“{INITIALS}” has been replaced with “{pref_}” throughout; the cover page shows “{full_}”.")

        # ── 3. Document Archive — always initials-only ──
        st.markdown("---")
        st.markdown("### 3 · File to the Document Archive")
        if not ARCHIVE_AVAILABLE:
            st.caption("The Document Archive isn't available on this deployment.")
        else:
            st.caption(f"Files an initials-only copy into {INITIALS}'s Document Archive folder"
                       + (" (marked final)." if S("finalised") else "."))
            if st.button("Save to Document Archive", key="tr_archive_btn"):
                saved = archive_document(
                    source_tool="Transition Report Builder",
                    doc_type=REPORT_TYPE,
                    title=f"{REPORT_TYPE} — {INITIALS} — {datetime.now():%d %b %Y}" + (" (Final)" if S("finalised") else " (Draft)"),
                    file_bytes=docx_bytes,
                    filename=f"{INITIALS}_{type_tag}_{'FINAL' if S('finalised') else 'DRAFT'}_{today_tag}.docx",
                    student_initials=INITIALS,
                    created_by=rep["teacher"] or "unknown",
                )
                if saved:
                    st.success(f"🗄️ Saved to {INITIALS}'s Document Archive folder.")
                else:
                    st.error("⚠️ Could NOT save to the Document Archive — the report was NOT filed. "
                             "You can still download it above.")

# editors not shown this run (Modified Report sections switched off) keep their rows for next time
for _name in EDITORS:
    if _name not in RENDERED_EDITORS and S(f"{_name}_latest") is not None:
        st.session_state[f"tr_{_name}_hidden"] = True

with SAVE_SLOT:
    _same = S("record_id") and S("record_type") == REPORT_TYPE
    if st.button(f"💾 Save {REPORT_TYPE}" if _same or not S("record_id") else f"💾 Save as new {REPORT_TYPE}",
                 key="tr_save_btn", type="primary", use_container_width=True, disabled=records is None):
        ok, msg = save_report(student, (lc_teacher or "").strip())
        (st.success if ok else st.error)(msg)
        if ok:
            st.toast(f"{REPORT_TYPE} saved for {INITIALS}")
    if S("record_saved"):
        st.caption(f"Last saved {fmt_date(S('record_saved'))}. Save regularly — the report is built up over the placement.")

st.markdown("---")
st.caption("Transition Report Builder · Review, Transition and Modified reports | Cowandilla Learning Centre LBU")
