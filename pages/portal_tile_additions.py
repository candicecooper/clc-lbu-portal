# ════════════════════════════════════════════════════════════════════════════
# PORTAL HOME — add these tiles to your Safety & Behaviour section
# (or create a new "ACCEPT Program" section)
# ════════════════════════════════════════════════════════════════════════════

# ── Option A: add to existing Safety & Behaviour section ─────────────────────
# Find your existing tile list for Safety & Behaviour and append:

{
    "label": "Scatter Plot Tracker",
    "icon": "📊",
    "desc": "ACCEPT Program frequency tracking — record and analyse targeted behaviour across the school day",
    "page": "scatter_plot_tracker",
},
{
    "label": "Schedule Analysis",
    "icon": "🗂️",
    "desc": "ACCEPT Program schedule analysis — log observations by grouping, task type, and time for functional pattern analysis",
    "page": "student_schedule_analysis",
},


# ── Option B: new ACCEPT Program section ─────────────────────────────────────
# Add a new section dict to your SECTIONS list:

{
    "title": "📋 ACCEPT Program",
    "colour": TEAL,   # or "#2A5C7A" to differentiate slightly
    "tiles": [
        {
            "label": "Scatter Plot Tracker",
            "icon": "📊",
            "desc": "Record and analyse targeted behaviour frequency across daily time intervals",
            "page": "scatter_plot_tracker",
        },
        {
            "label": "Schedule Analysis",
            "icon": "🗂️",
            "desc": "Log behaviour observations by grouping arrangement, task type, and time for FBA-style pattern analysis",
            "page": "student_schedule_analysis",
        },
    ],
},


# ════════════════════════════════════════════════════════════════════════════
# FILE PLACEMENT
# ════════════════════════════════════════════════════════════════════════════
#
# Place the two .py files in your pages/ directory:
#
#   clc-lbu-portal/
#   ├── Home.py                          ← add tiles here
#   ├── pages/
#   │   ├── ...existing pages...
#   │   ├── XX_scatter_plot_tracker.py   ← rename XX to next number
#   │   └── XX_student_schedule_analysis.py
#   └── ...
#
# If you use numbered page filenames (e.g. 01_Daily_Bulletin.py) just
# prefix these with the next available number.
#
# ════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════════
#
# These pages use only packages already in your portal:
#   streamlit, pandas, plotly, supabase-py
#
# No new pip installs required.
