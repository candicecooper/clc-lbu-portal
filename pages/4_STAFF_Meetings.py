from theme import apply_clc_theme
import streamlit as st
from supabase import create_client
import datetime
import hashlib
import json
import os
import re
import time
import uuid

# For transcript upload
try:
    import docx
    DOCX_AVAILABLE = True
except:
    DOCX_AVAILABLE = False

# ── Groq token-budget guard ────────────────────────────────────────────────
# The Groq account is on the on_demand tier. Groq enforces this per model —
# openai/gpt-oss-120b's actual cap on this account is 8,000 tokens/minute
# total, shared across prompt + requested output (earlier this was assumed
# to be 12,000, which was wrong and let requests through that Groq then
# rejected with a 413 "Request too large" error).
# A safety margin is applied on top of the 8,000 cap because the
# chars-per-token estimate below is approximate, and transcripts (speaker
# labels, timestamps, cross-talk) tend to tokenize less efficiently than
# plain prose — so a text that "fits" by this estimate can still occasionally
# run slightly over the real count without some headroom.
GROQ_TPM_LIMIT = 8000

def _fit_to_groq_budget(text: str, max_tokens: int, prompt_overhead_tokens: int = 400,
                         tpm_limit: int = GROQ_TPM_LIMIT) -> tuple[str, bool]:
    """Truncate text so prompt_overhead + text + max_tokens stays under the
    account's TPM limit, with a safety margin. Returns (possibly-truncated
    text, was_truncated)."""
    CHARS_PER_TOKEN = 4  # rough estimate for English text
    SAFETY_MARGIN = 0.85  # headroom for the estimate above being approximate
    input_token_budget = (tpm_limit - max_tokens - prompt_overhead_tokens) * SAFETY_MARGIN
    char_budget = max(0, int(input_token_budget)) * CHARS_PER_TOKEN
    if len(text) <= char_budget:
        return text, False
    return text[:char_budget], True

# ── Meeting Minutes structure ──────────────────────────────────────────────
# Minutes are organised exactly the same way the Agenda section (further
# down the page) already is: one block per Standing Item (the same labels as
# STANDING_AGENDA_ITEMS), one block per THIS meeting's specific Additional
# Agenda Items, and a dynamic "Any Other Items" block for anything raised
# that wasn't on the agenda at all. Manual Entry and AI-from-Transcript both
# produce/edit this same structure, so the two entry methods are
# interchangeable and minutes always land "in the standing item box it
# correlates to" rather than a separately-named scheme.
_NIL_TEXT = "Nil discussed this meeting."
_BLOCK_SEP = "\n\n---\n\n"

# Before this restructure, minutes used a fixed six-section scheme with
# slightly different names to the Agenda section's Standing Items. Kept here
# ONLY so minutes saved under the old scheme still show something sensible
# when a meeting is reopened for editing — new minutes never use these
# labels. "Other Business" has no safe 1:1 mapping onto a Standing Item, so
# it's carried over as a legacy block instead of being guessed at.
_LEGACY_SECTION_TO_STANDING_ITEM = {
    "Manager's Business": "Manager Info",
    "Transition Coordinator": "Transition Coordinator Info",
    "Finance": "Finance",
    "WHS": "WHS (Work Health & Safety)",
    "PAC": "PAC (Personnel Advisory Committee)",
}


def _slugify(text: str) -> str:
    """Turn a label into a stable, widget-key-safe slug."""
    return re.sub(r'[^a-z0-9]+', '_', (text or '').lower()).strip('_') or 'item'


def _clean_agenda_label(label: str) -> str:
    """Strip the '📌 ' prefix and '— submitted by …' suffix some additional
    agenda items carry, leaving just the plain topic text for use as a
    minutes heading."""
    text = (label or "").strip()
    if text.startswith("📌"):
        text = text[1:].strip()
    text = re.split(r"\s+—\s+submitted by\s+", text)[0].strip()
    return text or "(untitled item)"


def _parse_minutes_blocks(minutes_text: str) -> list:
    """Parse a combined minutes string into an ordered list of blocks:
    [{"kind": "standing"|"additional"|"other"|"legacy", "label": str,
      "raised_by": str, "minutes": str, "action": str, "origin": str}, …]

    Recognises the current '## STANDING: x' / '## ADDITIONAL: x' /
    '## OTHER: x | RAISED BY: y' heading convention, and falls back to
    treating a plain '## Heading' (the old fixed six-section format) as a
    legacy block so older saved minutes don't just vanish."""
    blocks = []
    if not minutes_text:
        return blocks
    for raw_block in minutes_text.split(_BLOCK_SEP):
        raw_block = raw_block.strip()
        if not raw_block or not raw_block.startswith("## "):
            continue
        heading_line, _, body = raw_block.partition("\n")
        heading_line = heading_line[3:].strip()
        body = body.strip()

        m = re.match(r"^(STANDING|ADDITIONAL|OTHER):\s*(.*)$", heading_line, re.DOTALL)
        if m:
            kind_raw, rest = m.group(1), m.group(2).strip()
            raised_by = ""
            if kind_raw == "OTHER":
                parts = re.split(r"\s*\|\s*RAISED BY:\s*", rest, maxsplit=1)
                label = parts[0].strip()
                raised_by = parts[1].strip() if len(parts) > 1 else ""
            else:
                label = rest
            kind = {"STANDING": "standing", "ADDITIONAL": "additional", "OTHER": "other"}[kind_raw]
        else:
            kind, label, raised_by = "legacy", heading_line, ""

        action = ""
        action_match = re.search(r"\n?ACTION:\s*(.*)$", body, re.DOTALL)
        if action_match:
            action_text = action_match.group(1).strip()
            body = body[:action_match.start()].strip()
            if action_text and action_text.lower() != "none":
                action = action_text
        if body == _NIL_TEXT:
            body = ""

        blocks.append({"kind": kind, "label": label, "raised_by": raised_by,
                        "minutes": body, "action": action, "origin": "saved"})
    return blocks


def _build_minutes_text(blocks: list) -> str:
    """Combine minutes blocks (same shape _parse_minutes_blocks returns) back
    into one storable markdown document."""
    parts = []
    for b in blocks:
        kind = b.get("kind", "additional")
        label = (b.get("label") or "").strip() or "(untitled item)"
        if kind == "standing":
            heading = f"STANDING: {label}"
        elif kind == "other":
            raised_by = (b.get("raised_by") or "Unknown").strip() or "Unknown"
            heading = f"OTHER: {label} | RAISED BY: {raised_by}"
        elif kind == "legacy":
            heading = label
        else:
            heading = f"ADDITIONAL: {label}"
        body = (b.get("minutes") or "").strip() or _NIL_TEXT
        action = (b.get("action") or "").strip()
        content = body + "\n\nACTION: " + (action if action else "None")
        parts.append(f"## {heading}\n\n{content}")
    return _BLOCK_SEP.join(parts)


def _seed_minutes_blocks(minutes_text: str, additional_item_labels: list) -> list:
    """Build the full working set of minutes blocks for THIS meeting: one per
    Standing Item, one per this meeting's current Additional Agenda Items,
    plus any 'Any Other Items' / legacy blocks already saved — seeding each
    from whatever was previously saved under that label."""
    parsed = _parse_minutes_blocks(minutes_text)
    by_standing, by_additional, others, legacy = {}, {}, [], []
    for b in parsed:
        if b["kind"] == "standing":
            by_standing[b["label"].strip().lower()] = b
        elif b["kind"] == "additional":
            by_additional[b["label"].strip().lower()] = b
        elif b["kind"] == "other":
            others.append(b)
        else:
            mapped = _LEGACY_SECTION_TO_STANDING_ITEM.get(b["label"].strip())
            if mapped and not by_standing.get(mapped.strip().lower(), {}).get("minutes"):
                by_standing[mapped.strip().lower()] = {**b, "kind": "standing", "label": mapped}
            else:
                legacy.append(b)

    blocks = []
    for label in STANDING_AGENDA_ITEMS:
        existing = by_standing.get(label.strip().lower())
        blocks.append(existing or {"kind": "standing", "label": label, "raised_by": "",
                                    "minutes": "", "action": "", "origin": "new"})

    for raw_label in additional_item_labels or []:
        clean = _clean_agenda_label(raw_label)
        existing = by_additional.get(clean.strip().lower())
        blocks.append(existing or {"kind": "additional", "label": clean, "raised_by": "",
                                    "minutes": "", "action": "", "origin": "new"})

    blocks.extend(others)
    blocks.extend(legacy)
    return blocks


def _sync_additional_minutes_blocks(blocks: list, additional_item_labels: list) -> None:
    """Add a minutes block for any Additional Agenda Item that doesn't have
    one yet (e.g. added after the Minutes section was first opened). Never
    removes a block, so minutes already written are never lost even if the
    agenda item is later removed."""
    existing = {b["label"].strip().lower() for b in blocks if b["kind"] == "additional"}
    for raw_label in additional_item_labels or []:
        clean = _clean_agenda_label(raw_label)
        if clean.strip().lower() not in existing:
            blocks.append({"kind": "additional", "label": clean, "raised_by": "",
                            "minutes": "", "action": "", "origin": "new"})
            existing.add(clean.strip().lower())


def _minutes_display_markdown(minutes_text: str) -> str:
    """Render stored minutes (new or legacy format) as clean markdown for
    read-only display — strips the internal STANDING:/ADDITIONAL:/OTHER:
    heading markup and bolds each item's Action line, instead of showing
    the raw storage format. Used by the Meeting Archive card and the
    on-screen 'Preview combined minutes' expander; the Word download goes
    through _build_minutes_docx_bytes instead, which parses the same way."""
    blocks = _parse_minutes_blocks(minutes_text)
    if not blocks:
        return minutes_text or ""
    parts = []
    for b in blocks:
        label = (b.get('label') or '').strip() or '(untitled item)'
        if b.get('kind') == 'other':
            raised_by = (b.get('raised_by') or '').strip()
            heading = f"Other Item: {label}" + (f" (raised by {raised_by})" if raised_by else "")
        else:
            heading = label
        body = (b.get('minutes') or '').strip() or _NIL_TEXT
        action = (b.get('action') or '').strip()
        chunk = f"#### {heading}\n\n{body}"
        if action:
            chunk += f"\n\n**Action:** {action}"
        parts.append(chunk)
    return "\n\n---\n\n".join(parts)


def _minutes_block_widget_keys(block: dict, key_prefix: str, idx: int) -> tuple:
    slug = _slugify(block.get("label", ""))
    base = f"{key_prefix}_{block.get('kind', 'x')}_{slug}_{idx}"
    return f"{base}_minutes", f"{base}_action"


def _sync_all_minutes_widgets_from_blocks(blocks: list, key_prefix: str) -> None:
    """Push every block's current minutes/action values into their widget
    session_state keys, numbered the SAME way _render_minutes_block_fields
    does (each kind indexed separately, starting at 0). MUST be called
    before any of those widgets are instantiated in this script run — e.g.
    at the very top of the Agenda section, before the Standing Items loop
    — since this is used right after something (like an AI generation step)
    mutates `blocks` data directly, outside the normal widget flow: once a
    widget key already exists, Streamlit ignores a fresh `value=` on rerun,
    so this is what actually makes the new values show up."""
    for kind in ("standing", "additional", "other", "legacy"):
        for i, b in enumerate([x for x in blocks if x["kind"] == kind]):
            m_key, a_key = _minutes_block_widget_keys(b, key_prefix, i)
            st.session_state[m_key] = b.get("minutes", "")
            st.session_state[a_key] = b.get("action", "")


def _all_minutes_widget_keys(blocks: list, key_prefix: str) -> list:
    """All (minutes, action) widget keys currently in use across `blocks`,
    computed the SAME way _render_minutes_blocks_editor numbers them — each
    kind (standing/additional/other/legacy) indexed separately, starting at
    0 — so callers that need to pop stale widget state (e.g. Clear draft)
    always match exactly what's actually on screen."""
    keys = []
    for kind in ("standing", "additional", "other", "legacy"):
        for i, b in enumerate([x for x in blocks if x["kind"] == kind]):
            keys.extend(_minutes_block_widget_keys(b, key_prefix, i))
    return keys


def _render_minutes_block_fields(blocks: list, b: dict, idx: int, key_prefix: str,
                                  allow_delete: bool = False, show_heading: bool = True) -> None:
    """Render one block's heading (optional) + editable (minutes + action)
    pair, mutating `b` in place (and, if `allow_delete` and the user removes
    it, `blocks` too). Shared by the Agenda section's Standing Item boxes
    (show_heading=False, since the expander title already names the item)
    and the Minutes section's Additional/Other Items editor below, so every
    item lands in the same style of fields."""
    if show_heading:
        heading = f"**{b['label']}**"
        if b.get("raised_by"):
            heading += f"  \n*Raised by {b['raised_by']}*"
        col_h, col_del = st.columns([8, 1]) if allow_delete else (st.container(), None)
        with col_h:
            st.markdown(heading)
        if allow_delete:
            with col_del:
                if st.button("🗑️", key=f"{key_prefix}_del_{idx}", help="Remove this item"):
                    blocks.remove(b)
                    st.rerun()
    m_key, a_key = _minutes_block_widget_keys(b, key_prefix, idx)
    b["minutes"] = st.text_area(
        f"Minutes — {b['label']}", value=b.get("minutes", ""), height=110,
        key=m_key, label_visibility="collapsed",
        placeholder="What was discussed, and any decisions made? Leave blank if not discussed."
    )
    b["action"] = st.text_input(
        f"Action — {b['label']}", value=b.get("action", ""),
        key=a_key, label_visibility="collapsed",
        placeholder='Action (optional) — who\'s doing what, e.g. "Jacqui — update the WHS checklist by Friday"'
    )
    st.write("")


def _render_minutes_blocks_editor(blocks: list, key_prefix: str) -> None:
    """Render one editable (minutes + action) pair per Additional/Other/
    legacy block, mutating `blocks` in place. Used identically by Manual
    Entry and by the AI-from-Transcript review step, so both methods land
    in the same fields. Standing Items are NOT rendered here — they render
    directly inside their own box in the Agenda section above instead, so
    each item's minutes live in exactly one place rather than two."""

    additional = [b for b in blocks if b["kind"] == "additional"]
    other = [b for b in blocks if b["kind"] == "other"]
    legacy = [b for b in blocks if b["kind"] == "legacy"]

    if additional:
        st.markdown("##### Additional Agenda Items")
        for i, b in enumerate(additional):
            _render_minutes_block_fields(blocks, b, i, key_prefix)

    st.markdown("##### Any Other Items")
    st.caption("Topics raised that weren't on the agenda — picked up automatically from the "
               "transcript, or add one yourself.")
    for i, b in enumerate(other):
        _render_minutes_block_fields(blocks, b, i, key_prefix, allow_delete=True)

    _new_other_topic_key = f"{key_prefix}_new_other_topic"
    _new_other_by_key = f"{key_prefix}_new_other_by"
    _clear_other_flag = f"{key_prefix}_clear_new_other"
    if st.session_state.get(_clear_other_flag):
        st.session_state[_new_other_topic_key] = ""
        st.session_state[_new_other_by_key] = ""
        st.session_state[_clear_other_flag] = False
    with st.expander("➕ Add an 'Any Other Item'", expanded=False):
        col_o1, col_o2, col_o3 = st.columns([3, 2, 1])
        with col_o1:
            _new_other_topic = st.text_input("Topic", key=_new_other_topic_key,
                                              label_visibility="collapsed",
                                              placeholder="Topic raised")
        with col_o2:
            _new_other_by = st.text_input("Raised by", key=_new_other_by_key,
                                           label_visibility="collapsed",
                                           placeholder="Raised by (optional)")
        with col_o3:
            if st.button("Add", key=f"{key_prefix}_add_other_btn", use_container_width=True):
                if _new_other_topic.strip():
                    blocks.append({"kind": "other", "label": _new_other_topic.strip(),
                                   "raised_by": _new_other_by.strip(), "minutes": "",
                                   "action": "", "origin": "manual"})
                    st.session_state[_clear_other_flag] = True
                    st.rerun()

    if legacy:
        st.markdown("##### Other saved notes")
        st.caption("Carried over from before this meeting's minutes were restructured.")
        for i, b in enumerate(legacy):
            _render_minutes_block_fields(blocks, b, i, key_prefix)


def _sync_minutes_actions_to_global(blocks: list, actions_list: list) -> None:
    """Push each minutes block's inline Action line into the trackable
    Actions list below, so extracted/typed actions show up there too —
    keyed by a stable 'source' tag so re-running this doesn't duplicate
    entries, editing the inline text updates the matching action, and
    clearing the inline text removes it again. Owner/due date/done that the
    user has since edited directly in the Actions list are left alone."""
    existing_by_source = {a.get('source'): a for a in actions_list if a.get('source')}
    active_sources = set()
    for b in blocks:
        action_text = (b.get('action') or '').strip()
        if not action_text:
            continue
        source = f"minutes:{b['kind']}:{b['label'].strip().lower()}"
        active_sources.add(source)
        if '—' in action_text:
            owner, what = action_text.split('—', 1)
        elif ' - ' in action_text:
            owner, what = action_text.split(' - ', 1)
        else:
            owner, what = '', action_text
        owner, what = owner.strip() or 'Unassigned', what.strip() or action_text
        if source in existing_by_source:
            a = existing_by_source[source]
            a['action'], a['owner'] = what, owner
        else:
            actions_list.append({
                "uid": uuid.uuid4().hex, "action": what, "owner": owner,
                "due_date": "", "done": False, "source": source,
            })
    actions_list[:] = [a for a in actions_list
                        if not a.get('source') or a.get('source') in active_sources]


# ── CLC-LBU document theme ──────────────────────────────────────────────────
# Same teal + Segoe UI look already used for the on-screen minutes preview
# (see the .clc-minutes CSS below) and the "Back to Staff Portal" sidebar
# button, so the downloaded Word doc matches the rest of the tool.
_CLC_TEAL = "1A7A7A"
_CLC_TEAL_LIGHT = "EAF5F5"
_CLC_GRAY = "6B7280"
_CLC_TEXT = "1A1A1A"
_CLC_BORDER = "D9DEE2"


def _docx_shade_cell(cell, hex_fill):
    """Set a table cell's background fill colour."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), hex_fill)
    tcPr.append(shd)


def _docx_cell_borders(cell, color=_CLC_BORDER, sz=4):
    """Give a table cell a thin single-colour border on all four sides."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    tcPr = cell._tc.get_or_add_tcPr()
    borders = OxmlElement('w:tcBorders')
    for edge in ('top', 'left', 'bottom', 'right'):
        el = OxmlElement(f'w:{edge}')
        el.set(qn('w:val'), 'single')
        el.set(qn('w:sz'), str(sz))
        el.set(qn('w:color'), color)
        borders.append(el)
    tcPr.append(borders)


def _docx_bottom_rule(paragraph, color=_CLC_TEAL, sz=16):
    """Add a coloured rule under a paragraph — used as a heading underline
    instead of a horizontal-rule table."""
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = OxmlElement('w:pBdr')
    bottom = OxmlElement('w:bottom')
    bottom.set(qn('w:val'), 'single')
    bottom.set(qn('w:sz'), str(sz))
    bottom.set(qn('w:space'), '4')
    bottom.set(qn('w:color'), color)
    pBdr.append(bottom)
    pPr.append(pBdr)


def _docx_set_cell_text(cell, text, bold=False, color=_CLC_TEXT, size=10.5, align=None):
    from docx.shared import Pt, RGBColor
    cell.text = ""
    p = cell.paragraphs[0]
    if align is not None:
        p.alignment = align
    run = p.add_run(text)
    run.bold = bold
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(color)
    run.font.name = "Segoe UI"


def _docx_section_heading(doc, text, size=13):
    """A coloured, underlined heading used for each minutes/actions section —
    built manually (rather than doc.add_heading) so the colour always matches
    the CLC teal regardless of the template's built-in heading colours."""
    from docx.shared import Pt, RGBColor
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(16)
    p.paragraph_format.space_after = Pt(4)
    run = p.add_run(text)
    run.bold = True
    run.font.size = Pt(size)
    run.font.color.rgb = RGBColor.from_string(_CLC_TEAL)
    run.font.name = "Segoe UI"
    _docx_bottom_rule(p, color=_CLC_BORDER, sz=6)
    return p


def _build_minutes_docx_bytes(meeting: dict):
    """Build a professionally styled Word document from a meeting record (or
    the in-progress form data) for download. Uses the same CLC-LBU teal +
    Segoe UI theme as the rest of the tool. Returns None if python-docx isn't
    available."""
    if not DOCX_AVAILABLE:
        return None
    from io import BytesIO
    from docx.shared import Pt, Inches, RGBColor
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT

    doc = docx.Document()

    # ── Base typography ──────────────────────────────────────────────────
    normal = doc.styles['Normal']
    normal.font.name = "Segoe UI"
    normal.font.size = Pt(10.5)
    normal.font.color.rgb = RGBColor.from_string(_CLC_TEXT)

    section = doc.sections[0]
    section.left_margin = Inches(0.9)
    section.right_margin = Inches(0.9)
    section.top_margin = Inches(0.7)
    section.bottom_margin = Inches(0.8)

    # ── Letterhead ───────────────────────────────────────────────────────
    eyebrow = doc.add_paragraph()
    eyebrow.alignment = WD_ALIGN_PARAGRAPH.CENTER
    er = eyebrow.add_run("COWANDILLA LEARNING CENTRE  ·  LEARNING & BEHAVIOUR UNIT")
    er.bold = True
    er.font.size = Pt(9)
    er.font.color.rgb = RGBColor.from_string(_CLC_GRAY)
    er.font.name = "Segoe UI"

    title = doc.add_paragraph()
    title.alignment = WD_ALIGN_PARAGRAPH.CENTER
    title.paragraph_format.space_before = Pt(2)
    title.paragraph_format.space_after = Pt(12)
    tr = title.add_run("Staff Meeting Minutes")
    tr.bold = True
    tr.font.size = Pt(24)
    tr.font.color.rgb = RGBColor.from_string(_CLC_TEAL)
    tr.font.name = "Segoe UI"
    _docx_bottom_rule(title, color=_CLC_TEAL, sz=18)

    # ── Meeting details card ─────────────────────────────────────────────
    details = [
        ("Date", meeting.get('meeting_date', '') or '—'),
        ("Term / Week", f"{meeting.get('term', '')} · Week {meeting.get('week_number', '')}"),
        ("Minute Taker", meeting.get('minute_taker', '') or '—'),
        ("Attendees", meeting.get('attendees', '') or 'Not recorded'),
        ("Apologies", meeting.get('apologies', '') or 'None'),
    ]
    if meeting.get('acknowledgement_done'):
        details.append((
            "Acknowledgement of Country",
            f"Completed — led by {meeting.get('acknowledgement_by', '') or 'not recorded'}"
        ))

    table = doc.add_table(rows=len(details), cols=2)
    table.alignment = WD_TABLE_ALIGNMENT.CENTER
    table.autofit = False
    for i, (label, value) in enumerate(details):
        cells = table.rows[i].cells
        cells[0].width = Inches(1.9)
        cells[1].width = Inches(4.7)
        _docx_shade_cell(cells[0], _CLC_TEAL_LIGHT)
        _docx_set_cell_text(cells[0], label, bold=True, color=_CLC_TEAL, size=9.5)
        _docx_set_cell_text(cells[1], str(value), size=10)
        _docx_cell_borders(cells[0])
        _docx_cell_borders(cells[1])

    doc.add_paragraph()

    # ── Minutes sections ─────────────────────────────────────────────────
    # Parsed with the same generic block parser the on-screen editor uses, so
    # a "STANDING: x" / "ADDITIONAL: x" / "OTHER: x | RAISED BY: y" heading
    # renders as a clean section title with its Action line picked out and
    # bolded, while minutes saved under the older fixed six-section scheme
    # still render fine too (as plain headings, via the "legacy" fallback).
    minutes_text = meeting.get('minutes', '') or ''
    for b in _parse_minutes_blocks(minutes_text):
        label = (b.get('label') or '').strip() or '(untitled item)'
        if b.get('kind') == 'other':
            raised_by = (b.get('raised_by') or '').strip()
            heading = f"Other Item: {label}" + (f" (raised by {raised_by})" if raised_by else "")
        else:
            heading = label
        _docx_section_heading(doc, heading)

        body = (b.get('minutes') or '').strip() or _NIL_TEXT
        for para in body.split('\n'):
            para = para.strip()
            if not para:
                continue
            bp = doc.add_paragraph()
            bp.paragraph_format.space_after = Pt(4)
            if para.startswith(('- ', '• ')):
                bp.style = doc.styles['List Bullet']
                bp.add_run(para[2:].strip())
            else:
                bp.add_run(para)

        action_text = (b.get('action') or '').strip()
        if action_text:
            ap = doc.add_paragraph()
            ap.paragraph_format.space_before = Pt(2)
            ap.paragraph_format.space_after = Pt(4)
            ar = ap.add_run(f"Action: {action_text}")
            ar.bold = True
            ar.font.color.rgb = RGBColor.from_string(_CLC_TEAL)

    # ── Actions ───────────────────────────────────────────────────────────
    raw_actions = meeting.get('actions')
    try:
        actions_list = json.loads(raw_actions) if isinstance(raw_actions, str) else (raw_actions or [])
    except Exception:
        actions_list = []
    if actions_list:
        _docx_section_heading(doc, "Actions")
        atable = doc.add_table(rows=1, cols=3)
        atable.autofit = True
        hdr = atable.rows[0].cells
        for c, label in zip(hdr, ("Action", "Owner", "Due Date")):
            _docx_shade_cell(c, _CLC_TEAL)
            _docx_set_cell_text(c, label, bold=True, color="FFFFFF", size=10)
            _docx_cell_borders(c, color=_CLC_TEAL)
        for a in actions_list:
            row = atable.add_row().cells
            _docx_set_cell_text(row[0], a.get('action', ''), size=10)
            _docx_set_cell_text(row[1], a.get('owner', ''), size=10)
            _docx_set_cell_text(row[2], a.get('due_date', ''), size=10)
            for c in row:
                _docx_cell_borders(c)

    # ── Meeting Attachments (names only — files live in the portal) ──────
    raw_meeting_attachments = meeting.get('meeting_attachments')
    try:
        meeting_attachments_list = json.loads(raw_meeting_attachments) if isinstance(raw_meeting_attachments, str) else (raw_meeting_attachments or [])
    except Exception:
        meeting_attachments_list = []
    if meeting_attachments_list:
        ap = doc.add_paragraph()
        ap.paragraph_format.space_before = Pt(8)
        ar = ap.add_run("Meeting Attachments: ")
        ar.bold = True
        ap.add_run(", ".join(a.get('name', 'file') for a in meeting_attachments_list))

    # ── Professional Development ─────────────────────────────────────────
    pd_title_val = meeting.get('pd_title', '') or ''
    pd_attendees_val = meeting.get('pd_attendees', '') or ''
    pd_absent_val = meeting.get('pd_absent', '') or ''
    pd_notes_val = meeting.get('pd_notes', '') or ''
    raw_pd_attachments = meeting.get('pd_attachments')
    try:
        pd_attachments_list = json.loads(raw_pd_attachments) if isinstance(raw_pd_attachments, str) else (raw_pd_attachments or [])
    except Exception:
        pd_attachments_list = []

    if pd_title_val.strip() or pd_attendees_val.strip() or pd_absent_val.strip() or pd_notes_val.strip() or pd_attachments_list:
        _docx_section_heading(doc, "Professional Development")

        if pd_title_val.strip():
            sp = doc.add_paragraph()
            sp.paragraph_format.space_after = Pt(6)
            sr = sp.add_run("Session: ")
            sr.bold = True
            sp.add_run(pd_title_val.strip())

        pd_details = []
        if pd_attendees_val.strip():
            pd_details.append(("PD Attendees", pd_attendees_val))
        if pd_absent_val.strip():
            pd_details.append(("PD Absent", pd_absent_val))
        if pd_details:
            pdtable = doc.add_table(rows=len(pd_details), cols=2)
            pdtable.alignment = WD_TABLE_ALIGNMENT.CENTER
            pdtable.autofit = False
            for i, (label, value) in enumerate(pd_details):
                cells = pdtable.rows[i].cells
                cells[0].width = Inches(1.9)
                cells[1].width = Inches(4.7)
                _docx_shade_cell(cells[0], _CLC_TEAL_LIGHT)
                _docx_set_cell_text(cells[0], label, bold=True, color=_CLC_TEAL, size=9.5)
                _docx_set_cell_text(cells[1], str(value), size=10)
                _docx_cell_borders(cells[0])
                _docx_cell_borders(cells[1])
            doc.add_paragraph()

        if pd_notes_val.strip():
            np_heading = doc.add_paragraph()
            np_heading.paragraph_format.space_before = Pt(4)
            nhr = np_heading.add_run("PD Notes:")
            nhr.bold = True
            for para in pd_notes_val.split('\n'):
                para = para.strip()
                if not para:
                    continue
                bp = doc.add_paragraph()
                bp.paragraph_format.space_after = Pt(4)
                if para.startswith(('- ', '• ')):
                    bp.style = doc.styles['List Bullet']
                    bp.add_run(para[2:].strip())
                else:
                    bp.add_run(para)

        if pd_attachments_list:
            ap = doc.add_paragraph()
            ap.paragraph_format.space_before = Pt(4)
            ar = ap.add_run("PD Attachments: ")
            ar.bold = True
            ap.add_run(", ".join(a.get('name', 'file') for a in pd_attachments_list))

    # ── Attachments note — files aren't embedded in this document ─────────
    if meeting_attachments_list or pd_attachments_list:
        note_p = doc.add_paragraph()
        note_p.paragraph_format.space_before = Pt(12)
        note_run = note_p.add_run(
            "📎 Attached files are stored in the CLC-LBU Staff Portal, not in this document — "
            "log in to the Staff Portal → STAFF Meetings tool to view or download them."
        )
        note_run.italic = True
        note_run.font.size = Pt(9)
        note_run.font.color.rgb = RGBColor.from_string(_CLC_GRAY)
        note_run.font.name = "Segoe UI"

    # ── Footer ────────────────────────────────────────────────────────────
    footer_p = section.footer.paragraphs[0]
    footer_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr = footer_p.add_run("Cowandilla Learning Centre  ·  Learning and Behaviour Unit  ·  Staff Meeting Minutes")
    fr.font.size = Pt(8)
    fr.font.color.rgb = RGBColor.from_string(_CLC_GRAY)
    fr.font.name = "Segoe UI"

    buf = BytesIO()
    doc.save(buf)
    buf.seek(0)
    return buf.getvalue()

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(page_title="STAFF Meetings | CLC-LBU", page_icon="👥", layout="wide")
apply_clc_theme()

from staff_auth import require_staff_auth, staff_logout_button
require_staff_auth("STAFF Meetings", "👥")
staff_logout_button("sidebar")

# ── Back to Portal ─────────────────────────────────────────────────────────────
st.sidebar.markdown(
    '<a href="https://16cefb77.clc-portal.pages.dev/" target="_self" style="display:block;text-align:center;'
    'background:#1A7A7A;color:white;font-weight:600;font-size:0.85rem;'
    'padding:0.5rem;border-radius:8px;text-decoration:none;margin-bottom:0.5rem;">'
    '🏠 Back to Staff Portal</a>',
    unsafe_allow_html=True
)

# ── Supabase Connections ──────────────────────────────────────────────────────
# STAFF Meetings uses TWO databases:
# 1. MEETINGS database (cmqyrfekxgjdtuloseri) - for meeting records and agenda items
# 2. OPERATIONAL database (lvzaebjrxrgguypqvdcq) - for bulletin (clc_events)

# Primary connection: MEETINGS database (meeting records, agenda items)
SUPABASE_URL_MEETINGS = st.secrets.get("SUPABASE_URL_MEETINGS", st.secrets["SUPABASE_URL"])
SUPABASE_KEY_MEETINGS = st.secrets.get("SUPABASE_KEY_MEETINGS", st.secrets["SUPABASE_KEY"])
SUPABASE_SERVICE_KEY_MEETINGS = st.secrets.get("SUPABASE_SERVICE_KEY_MEETINGS", SUPABASE_KEY_MEETINGS)

supabase = create_client(SUPABASE_URL_MEETINGS, SUPABASE_SERVICE_KEY_MEETINGS)

# Secondary connection: OPERATIONAL database (for bulletin)
SUPABASE_URL_OPERATIONAL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY_OPERATIONAL = st.secrets["SUPABASE_KEY"]
SUPABASE_SERVICE_KEY_OPERATIONAL = st.secrets.get("SUPABASE_SERVICE_KEY", SUPABASE_KEY_OPERATIONAL)

supabase_ops = create_client(SUPABASE_URL_OPERATIONAL, SUPABASE_SERVICE_KEY_OPERATIONAL)

GROQ_KEY = st.secrets.get("GROQ_API_KEY", "")

# ── Staff roster (for click-to-select attendance) ──────────────────────────────
# Primary source is a small `staff_roster` table in the MEETINGS Supabase
# project, editable from the "⚙️ Staff List" tab (add/remove names in the app,
# no code or Render changes needed). Falls back to the STAFF_NAMES secret, then
# to a hardcoded list, if that table doesn't exist yet or can't be reached.
STAFF_ROSTER_TABLE_SQL = """
create table if not exists staff_roster (
    id bigint generated by default as identity primary key,
    name text not null unique,
    created_at timestamptz not null default now()
);
""".strip()

def _parse_staff_roster(raw: str) -> list:
    if not raw:
        return []
    parts = re.split(r'[,;\n]+', str(raw))
    seen = set()
    names = []
    for p in parts:
        name = p.strip()
        if name and name not in seen:
            seen.add(name)
            names.append(name)
    return names

# Last-resort fallback so attendance always shows a clickable list even if
# neither the database table nor the STAFF_NAMES secret is available — edit
# this list directly here if anyone is missing, wrong, or has left.
DEFAULT_STAFF_ROSTER = [
    "Candice Cooper", "Annette Balestrin", "Ben Selga", "Ben Sutton", "Brenton",
    "Caitie", "Cheryl", "Jacqui", "Naomi", "Tom", "Vinnie",
]

def _load_staff_roster_rows():
    """Returns (rows, table_exists) — rows is [{'id':..,'name':..}, ...] ordered
    by name, or ([], False) if the staff_roster table doesn't exist yet."""
    try:
        result = supabase.table('staff_roster').select('*').order('name').execute()
        return (result.data or []), True
    except Exception:
        return [], False

def _add_staff_member(name: str):
    name = (name or '').strip()
    if not name:
        return False, "Enter a name first."
    try:
        supabase.table('staff_roster').insert({"name": name}).execute()
        return True, None
    except Exception as e:
        return False, str(e)

def _delete_staff_member(staff_id):
    try:
        supabase.table('staff_roster').delete().eq('id', staff_id).execute()
        return True, None
    except Exception as e:
        return False, str(e)

_staff_roster_rows, _staff_roster_table_exists = _load_staff_roster_rows()
_staff_names_secret = st.secrets.get("STAFF_NAMES", "")

if _staff_roster_table_exists and _staff_roster_rows:
    STAFF_ROSTER = [r['name'] for r in _staff_roster_rows]
    STAFF_ROSTER_SOURCE = "Staff List tab (database)"
elif _parse_staff_roster(_staff_names_secret):
    STAFF_ROSTER = _parse_staff_roster(_staff_names_secret)
    STAFF_ROSTER_SOURCE = "STAFF_NAMES secret"
else:
    STAFF_ROSTER = DEFAULT_STAFF_ROSTER
    STAFF_ROSTER_SOURCE = "built-in default list"


def _render_roster_attendance(label_prefix: str, key_prefix: str, roster: list,
                               seed_present: str, seed_apologies: str):
    """Click-to-select attendance from the staff roster instead of free text.
    key_prefix MUST already include the current meeting id — like every
    other per-meeting widget in this file, an un-namespaced key would freeze
    on whichever meeting first rendered it and ignore every other meeting's
    saved data afterwards.
    Returns (present_str, apologies_str) as comma-joined names, in the same
    plain-string format the rest of the app (docx export, Archive display,
    PD pre-fill) already expects — no data model changes needed downstream.
    Seeding an existing meeting's checkboxes is a best-effort NAME MATCH
    against its old free-text fields (this app has stored attendance as
    free text until now), so a name typo'd differently in old data won't
    auto-check — that's what the "Other" box below is for.
    """
    if not roster:
        # No roster configured (STAFF_NAMES secret not set) — fall back to
        # the original free-text boxes rather than showing an empty picker.
        present = st.text_area(f"{label_prefix} Present", value=seed_present or '', height=80,
                                key=f"{key_prefix}_present_text",
                                placeholder="List staff members present...")
        absent = st.text_area(f"{label_prefix} Apologies", value=seed_apologies or '', height=60,
                               key=f"{key_prefix}_apologies_text",
                               placeholder="List staff members with apologies...")
        return present, absent

    seed_present = seed_present or ''
    seed_apologies = seed_apologies or ''

    default_present = [n for n in roster if n in seed_present]
    default_apologies = [n for n in roster if n in seed_apologies and n not in default_present]

    st.caption(f"Click to add names for {label_prefix.lower()} attendance.")
    col_p, col_a = st.columns(2)
    with col_p:
        present_names = st.multiselect(
            f"{label_prefix} Present", options=roster, default=default_present,
            key=f"{key_prefix}_present_ms"
        )
    with col_a:
        apology_names = st.multiselect(
            f"{label_prefix} Apologies", options=roster, default=default_apologies,
            key=f"{key_prefix}_apologies_ms"
        )

    col_extra1, col_extra2 = st.columns(2)
    with col_extra1:
        extra_present = st.text_input(
            "Other present (not on the list above)", key=f"{key_prefix}_present_extra",
            placeholder="e.g. relief staff, visitors"
        )
    with col_extra2:
        extra_apologies = st.text_input(
            "Other apologies (not on the list above)", key=f"{key_prefix}_apologies_extra"
        )

    present = ", ".join(present_names + ([extra_present.strip()] if extra_present.strip() else []))
    apologies = ", ".join(apology_names + ([extra_apologies.strip()] if extra_apologies.strip() else []))
    return present, apologies


# ── Supabase Storage attachment helpers ────────────────────────────────────────
# Attachments previously only saved file *metadata* (name/size/type) — nothing
# was ever uploaded anywhere, so "Add All Files" looked like it worked but
# there was never a file to open afterwards. These helpers actually upload the
# bytes to Supabase Storage (in the MEETINGS project, alongside the meeting
# records) and hand back a storage path to save with the metadata, plus a
# signed URL for opening/downloading.
MEETING_ATTACHMENTS_BUCKET = "meeting-attachments"
PD_ATTACHMENTS_BUCKET = "pd-attachments"


def _ensure_bucket(bucket_name: str):
    """Create the storage bucket if it doesn't exist yet. Safe to call any
    time — quietly no-ops if it's already there (or gets created between the
    check and the call)."""
    try:
        supabase.storage.create_bucket(bucket_name, options={"public": False})
    except Exception:
        pass


def _upload_attachment(bucket_name: str, folder: str, file) -> dict:
    """Upload one Streamlit UploadedFile to Supabase Storage.
    Returns {"path": ...} on success or {"error": ...} on failure."""
    safe_name = re.sub(r'[^A-Za-z0-9._-]', '_', file.name)
    path = f"{folder}/{int(time.time() * 1000)}_{safe_name}"
    file_bytes = file.getvalue()
    content_type = file.type or "application/octet-stream"
    try:
        supabase.storage.from_(bucket_name).upload(
            path, file_bytes, {"content-type": content_type}
        )
        return {"path": path}
    except Exception as e1:
        # Most likely cause of a first-ever upload failing: the bucket
        # doesn't exist yet. Create it and retry once before giving up.
        try:
            _ensure_bucket(bucket_name)
            supabase.storage.from_(bucket_name).upload(
                path, file_bytes, {"content-type": content_type}
            )
            return {"path": path}
        except Exception as e2:
            return {"error": f"{type(e2).__name__}: {e2}  (first attempt: {type(e1).__name__}: {e1})"}


def _extract_signed_url_value(result):
    """Pull the signed URL out of whatever shape create_signed_url() returned
    — different supabase-py/storage3 versions hand back a plain dict, a
    pydantic model, or different key casing."""
    if result is None:
        return None
    if isinstance(result, dict):
        return result.get('signedURL') or result.get('signedUrl') or result.get('signed_url')
    return (
        getattr(result, 'signedURL', None)
        or getattr(result, 'signedUrl', None)
        or getattr(result, 'signed_url', None)
    )


def _decode_jwt_role(token: str) -> str:
    """Best-effort decode of a Supabase API key's `role` claim (anon /
    authenticated / service_role), with no signature check — this is only to
    show which key is actually configured, not to validate it. A repeated
    'new row violates row-level security policy' error on Storage uploads is
    only possible if the key in use is NOT service_role (service_role bypasses
    RLS entirely at the Postgres level, unconditionally) — so this settles
    that question directly instead of guessing from Render/Supabase dashboards."""
    try:
        import base64
        payload_b64 = token.split('.')[1]
        padded = payload_b64 + '=' * (-len(payload_b64) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded))
        return payload.get('role', 'unknown (no role claim)')
    except Exception:
        return "couldn't decode — is this a valid Supabase API key?"


def _attachment_signed_url(bucket_name: str, path: str, expires_in: int = 3600):
    """Return (url, error). url is a temporary signed download URL, or None
    on failure; error is the raw exception/diagnostic text when it fails, so
    a failure can be shown to the user instead of disappearing silently."""
    if not path:
        return None, "No file path stored for this attachment."
    try:
        result = supabase.storage.from_(bucket_name).create_signed_url(path, expires_in)
        url = _extract_signed_url_value(result)
        if not url:
            return None, f"Supabase returned no signed URL ({result!r})."
        if not (url.startswith('http://') or url.startswith('https://')):
            # Some supabase-py versions return a URL relative to the storage
            # API host instead of a full URL — normalise it defensively so a
            # relative path doesn't silently produce a dead link.
            base = SUPABASE_URL_MEETINGS.rstrip('/')
            rel = url if url.startswith('/') else '/' + url
            if not rel.startswith('/storage/v1'):
                rel = '/storage/v1' + rel
            url = base + rel
        return url, None
    except Exception as e:
        return None, f"{type(e).__name__}: {e}"


def _delete_attachment(bucket_name: str, path: str):
    """Best-effort delete of the stored file when an attachment is removed
    from a meeting. Never raises — a storage hiccup shouldn't block removing
    the metadata row."""
    if not path:
        return
    try:
        supabase.storage.from_(bucket_name).remove([path])
    except Exception:
        pass


def _render_attachment_link(att: dict, bucket_name: str):
    """Render one attachment's name/description plus an Open link when the
    file was actually uploaded to storage. Attachments saved before this fix
    only ever had metadata (no 'path'), so those are flagged as needing a
    re-upload rather than shown as a dead link."""
    name = att.get('name') or att.get('filename') or 'Unnamed file'
    desc = att.get('description') or ''
    label = f"📎 **{name}**" + (f" — {desc}" if desc else "")
    path = att.get('path')
    if path:
        url, err = _attachment_signed_url(bucket_name, path)
        if url:
            st.markdown(f"{label}  \n[🔗 Open / Download]({url})")
        else:
            st.markdown(f"{label}  \n:orange[Couldn't generate a link for this file.]")
            st.caption(f"⚠️ {err}")
    else:
        st.markdown(f"{label}  \n:gray[Added before file upload was enabled — no file stored. Delete and re-upload to attach it.]")

# ── Term normalisation ─────────────────────────────────────────────────────────
# Staff Meetings stores term as "T2"; Staff Bulletin stores it as "Term 2".
# These helpers keep the two tools in sync.

def normalise_term_long(raw: str) -> str:
    """Convert ANY term format to 'Term N' (used by Staff Bulletin).
    Handles: 'T2', '2', 'term2', 'Term 2', 'TERM2', etc."""
    import re
    raw = str(raw).strip()
    m = re.search(r'(\d)', raw)
    if m:
        return f"Term {m.group(1)}"
    return raw

def normalise_term_short(raw: str) -> str:
    """Convert ANY term format to 'TN' (used by Staff Meetings)."""
    import re
    raw = str(raw).strip()
    m = re.search(r'(\d)', raw)
    if m:
        return f"T{m.group(1)}"
    return raw


def _meeting_year_term_group(meeting: dict):
    """Group/sort key for the Meeting Archive: (year, term number), newest
    first. Falls back to 0 for anything unparseable so odd/legacy records
    still show up (under an 'Unknown' heading) instead of erroring out."""
    date_str = meeting.get('meeting_date') or ''
    try:
        year = datetime.date.fromisoformat(str(date_str)).year
    except Exception:
        year = 0
    term_match = re.search(r'(\d)', normalise_term_short(meeting.get('term', '')))
    term_num = int(term_match.group(1)) if term_match else 0
    return (year, term_num)


def _meeting_week_sort_key(meeting: dict):
    """Sort key for ordering meetings within a term — by week number where
    possible, falling back to the meeting date."""
    try:
        return (0, int(re.search(r'\d+', str(meeting.get('week_number', ''))).group()))
    except Exception:
        return (1, meeting.get('meeting_date', '') or '')

# ── BSEM Icebreakers (5-minute activities) ────────────────────────────────────
# A larger, varied pool — picked by _bsem_icebreaker_for() below rather than a
# plain week-number index, so Week 1 of Term 2 doesn't show the identical
# activity as Week 1 of Term 1, 3 and 4 (which is what "week_idx = week - 1"
# against an 11-item list used to do).
BSEM_ICEBREAKERS = [
    {
        "name": "Two Truths and a Lie",
        "instructions": "Each person shares three statements about themselves - two true, one false. Group guesses which is the lie.",
        "time": "5 mins"
    },
    {
        "name": "Gratitude Round",
        "instructions": "Each person shares one thing they're grateful for this week (personal or professional).",
        "time": "5 mins"
    },
    {
        "name": "Brain Break: Draw Your Weekend",
        "instructions": "60 seconds to draw something from your weekend. Share with the group.",
        "time": "5 mins"
    },
    {
        "name": "Quick Check-In: Rate Your Week",
        "instructions": "Rate your week 1-10 and share one word to describe it.",
        "time": "5 mins"
    },
    {
        "name": "Wins & Learnings",
        "instructions": "Share one win and one thing you learned this week.",
        "time": "5 mins"
    },
    {
        "name": "Would You Rather?",
        "instructions": "Facilitator poses a 'Would you rather...' question. Quick votes and brief sharing.",
        "time": "5 mins"
    },
    {
        "name": "Rose, Thorn, Bud",
        "instructions": "Share: Rose (highlight), Thorn (challenge), Bud (something you're looking forward to).",
        "time": "5 mins"
    },
    {
        "name": "Quick Movement Break",
        "instructions": "Stand up stretch or brief movement activity. Can be led by different staff member each week.",
        "time": "5 mins"
    },
    {
        "name": "Shout-Outs",
        "instructions": "Acknowledge someone who helped you this week or did something great.",
        "time": "5 mins"
    },
    {
        "name": "What's In Your Cup?",
        "instructions": "Share what's filling your emotional cup or draining it this week.",
        "time": "5 mins"
    },
    {
        "name": "Reflection Round",
        "instructions": "One word to describe this term. Quick round-robin.",
        "time": "5 mins"
    },
    {
        "name": "Weather Report Check-In",
        "instructions": "Describe your current mood as a weather forecast (sunny, stormy, foggy, etc.) and why.",
        "time": "5 mins"
    },
    {
        "name": "Desert Island",
        "instructions": "If stranded on a desert island, what three items would you bring and why?",
        "time": "5 mins"
    },
    {
        "name": "High Five / Low Five",
        "instructions": "Share one high point and one low point from the past week — no fixing, just listening.",
        "time": "5 mins"
    },
    {
        "name": "This or That",
        "instructions": "Facilitator reads quick-fire 'this or that' pairs (tea or coffee, beach or mountains). Group calls out their pick.",
        "time": "5 mins"
    },
    {
        "name": "Name That Tune",
        "instructions": "Play 10-second snippets of a few songs. Group guesses the title or artist.",
        "time": "5 mins"
    },
    {
        "name": "Grounding Breath",
        "instructions": "A short guided breathing exercise (in for 4, hold for 4, out for 4) to settle the room before business starts.",
        "time": "5 mins"
    },
    {
        "name": "One Word Check-In",
        "instructions": "Go around the room — each person offers a single word for how they're arriving today.",
        "time": "5 mins"
    },
    {
        "name": "Appreciation Pass",
        "instructions": "Each person names one colleague (not themselves) and briefly says what they appreciate about working with them.",
        "time": "5 mins"
    },
    {
        "name": "Photo Share",
        "instructions": "Each person shares (or describes) one photo on their phone from the past week and why it's there.",
        "time": "5 mins"
    },
    {
        "name": "Two-Minute Doodle",
        "instructions": "Everyone doodles whatever comes to mind for two minutes, then a few volunteers show what they drew.",
        "time": "5 mins"
    },
    {
        "name": "Would You Rather: School Edition",
        "instructions": "School-themed 'would you rather' questions (e.g. yard duty in the rain or a double photocopier queue).",
        "time": "5 mins"
    },
    {
        "name": "Three Good Things",
        "instructions": "Each person names three small good things that happened this week, work or personal.",
        "time": "5 mins"
    },
    {
        "name": "Object Show and Tell",
        "instructions": "Each person grabs the nearest object on their desk and shares a 10-second story about it.",
        "time": "5 mins"
    },
    {
        "name": "Energy Check",
        "instructions": "Rate your energy 1-10 with a thumbs gesture, then one or two people briefly explain their number.",
        "time": "5 mins"
    },
    {
        "name": "Favourite Thing About This Term So Far",
        "instructions": "Quick round-robin — one favourite moment or win from the term so far.",
        "time": "5 mins"
    },
]


def _bsem_icebreaker_for(meeting_date, term, week_number) -> dict:
    """Pick the BSEM activity for this specific meeting. Deterministic (same
    meeting always suggests the same activity when reopened) but spread
    across the whole pool using the meeting's year + term + week as the
    seed — unlike a plain '(week - 1) % len(list)' index, this means Week 1
    of Term 1, 2, 3 and 4 don't all land on the same activity."""
    try:
        wk = int(week_number)
    except Exception:
        wk = 1
    try:
        year = meeting_date.year
    except Exception:
        year = datetime.date.today().year
    seed = f"{year}-{normalise_term_short(term)}-{wk}"
    idx = int(hashlib.md5(seed.encode()).hexdigest(), 16) % len(BSEM_ICEBREAKERS)
    return BSEM_ICEBREAKERS[idx]

# ── BSEM activity field encoding ────────────────────────────────────────────────
# The DB only has one "icebreaker" text column. Rather than add a new column,
# a "different activity" choice is encoded as a small header prefix on that
# same field, followed by any free-text notes on the next line. Old plain-text
# values never start with this marker, so they always parse as "suggested"
# with the notes intact — fully backward compatible.
_BSEM_DIFFERENT_PREFIX = "[[BSEM_DIFFERENT|"

def _parse_bsem_field(raw: str):
    """Returns (mode, name, explanation, notes) from a stored icebreaker value."""
    raw = raw or ''
    if raw.startswith(_BSEM_DIFFERENT_PREFIX):
        try:
            header, rest = raw.split("]]", 1)
            _, name, explanation = header.split("|", 2)
            return "different", name.strip(), explanation.strip(), rest.lstrip("\n")
        except Exception:
            pass
    return "suggested", "", "", raw

def _build_bsem_field(mode: str, name: str, explanation: str, notes: str) -> str:
    if mode == "different":
        header = f"{_BSEM_DIFFERENT_PREFIX}{name}|{explanation}]]"
        return f"{header}\n{notes}" if notes else header
    return notes

# Standing agenda items
STANDING_AGENDA_ITEMS = [
    "Transition Coordinator Info",
    "Manager Info",
    "PAC (Personnel Advisory Committee)",
    "WHS (Work Health & Safety)",
    "Social Club",
    "Finance"
]

# ── Session state ──────────────────────────────────────────────────────────────
if 'current_staff_meeting_id' not in st.session_state:
    st.session_state.current_staff_meeting_id = None

# ══════════════════════════════════════════════════════════════════════════════
# HEADER
# ══════════════════════════════════════════════════════════════════════════════

st.title("👥 STAFF MEETINGS")
st.caption("Weekly All-Staff Meetings · DfE Format")

# ── Storage connection diagnostics ──────────────────────────────────────────
# Attachment uploads have been hitting a Storage RLS "row violates row-level
# security policy" error that policy changes haven't fixed. That error is
# only possible if the configured key is NOT service_role — service_role
# bypasses Storage RLS unconditionally, no policy can make it happen. Rather
# than keep guessing which key Render actually has configured, decode its
# role claim directly and say so plainly.
_meetings_key_role = _decode_jwt_role(SUPABASE_SERVICE_KEY_MEETINGS)
if _meetings_key_role != "service_role":
    st.error(
        f"⚠️ **Attachment uploads will keep failing with a row-level security error.** "
        f"The Supabase key configured for `SUPABASE_SERVICE_KEY_MEETINGS` has role "
        f"**`{_meetings_key_role}`**, not `service_role` — so Storage's row-level "
        f"security is being enforced against it (no policy can override this; only "
        f"the real service_role key bypasses it). In Render's Environment tab, set "
        f"`SUPABASE_SERVICE_KEY_MEETINGS` to the **service_role** secret from "
        f"Supabase (MEETINGS project → Settings → API) — not the anon/public key — "
        f"and redeploy."
    )

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# MEETING SELECTOR
# ══════════════════════════════════════════════════════════════════════════════

st.subheader("📅 Select Meeting")

# Fetch existing meetings
try:
    # NOTE: this used to be .limit(20) — once more than 20 meetings existed
    # in total, the oldest ones silently stopped appearing in BOTH the
    # "Choose a meeting" dropdown below and the Meeting Archive tab, with no
    # error or warning. That's almost certainly why a meeting you'd worked on
    # repeatedly seemed to vanish — it's very unlikely to be deleted, just no
    # longer inside the most-recent-20 window this query returned. Raised the
    # cap generously; a school year of weekly meetings is nowhere near this.
    result = supabase.table('staff_meetings').select('*').order('meeting_date', desc=True).limit(500).execute()
    existing_meetings = result.data if result.data else []
except Exception as e:
    st.warning(f"Could not load meetings: {e}")
    existing_meetings = []

meeting_options = ["➕ New Meeting"] + [
    # normalise_term_short already returns "T3" etc — the term field itself
    # is stored WITH the "T" prefix, so prepending another literal "T" here
    # used to produce labels like "TT3" everywhere a meeting was listed.
    f"{m['meeting_date']} - {normalise_term_short(m.get('term', '?'))} W{m.get('week_number', '?')} - {m.get('minute_taker', 'Unknown')}"
    for m in existing_meetings
]

# ── "Edit / Add to This Meeting" jump from the Meeting Archive tab ─────────
# Streamlit won't let a script set `st.session_state["staff_meeting_selector"]`
# in the SAME run where the button that requests it lives, because that
# selectbox is instantiated further down the page — assigning to its key
# after it's already rendered raises StreamlitWidgetAlreadyInstantiatedError.
# So the archive button only stashes the requested label in a plain
# (non-widget) session_state slot and reruns; THIS code, which runs before
# the selectbox exists at all, is what actually applies the jump.
if "_pending_meeting_jump" in st.session_state:
    st.session_state["staff_meeting_selector"] = st.session_state.pop("_pending_meeting_jump")

selected_option = st.selectbox("Choose a meeting", options=meeting_options, key="staff_meeting_selector")

if selected_option == "➕ New Meeting":
    selected_record = None
    st.session_state.current_staff_meeting_id = None
else:
    idx = meeting_options.index(selected_option) - 1
    selected_record = existing_meetings[idx]
    st.session_state.current_staff_meeting_id = selected_record['id']
    
    # Delete meeting option (only for existing meetings)
    with st.expander("🗑️ Delete This Meeting", expanded=False):
        st.warning("⚠️ **Warning:** This will permanently delete this meeting record!")
        
        delete_confirmation = st.text_input(
            "Type 'DELETE' to confirm deletion",
            key="delete_confirm",
            placeholder="Type DELETE here"
        )
        
        col_del1, col_del2 = st.columns([1, 3])
        with col_del1:
            if st.button("🗑️ Delete Meeting", type="secondary", disabled=(delete_confirmation != "DELETE")):
                try:
                    supabase.table('staff_meetings').delete().eq('id', st.session_state.current_staff_meeting_id).execute()
                    st.success("✅ Meeting deleted successfully!")
                    st.session_state.current_staff_meeting_id = None
                    st.rerun()
                except Exception as e:
                    st.error(f"⚠️ Could not delete meeting: {e}")
        
        with col_del2:
            if delete_confirmation != "DELETE":
                st.caption("Type DELETE above to enable deletion")

st.markdown("---")

# ══════════════════════════════════════════════════════════════════════════════
# TABS: CURRENT MEETING / ARCHIVE
# ══════════════════════════════════════════════════════════════════════════════

tab1, tab2, tab3 = st.tabs(["📝 Current Meeting", "📚 Meeting Archive", "⚙️ Staff List"])

with tab2:
    st.subheader("📚 Past STAFF Meetings")
    
    if existing_meetings:
        # Group into terms instead of one long flat list. Each term gets a
        # real table (aligned header + data rows via st.columns, since
        # Streamlit's own st.table/st.dataframe can't hold a clickable
        # button in a cell) — clicking "Open" in a row's own last column
        # reveals that meeting's full detail directly beneath its row, so
        # the click-to-open lives inside the table itself rather than in a
        # separate list elsewhere on the page.
        _archive_groups = {}
        for _m in existing_meetings:
            _archive_groups.setdefault(_meeting_year_term_group(_m), []).append(_m)
        _sorted_meetings = []
        for _key in sorted(_archive_groups.keys(), reverse=True):
            _sorted_meetings.extend(sorted(_archive_groups[_key], key=_meeting_week_sort_key))

        # Flag weeks with more than one saved record for the same term/year —
        # a known historical bug (autosave duplicating a record on a session
        # reset) has left blank "stub" duplicates alongside real ones before.
        # We never delete these automatically (a stub could turn out to hold
        # the only copy of something); this just makes them impossible to
        # miss so the existing per-meeting delete button below can remove
        # the empty one with confidence.
        _week_counts = {}
        for _m in existing_meetings:
            _wkey = (*_meeting_year_term_group(_m), str(_m.get('week_number', '')).strip())
            _week_counts[_wkey] = _week_counts.get(_wkey, 0) + 1

        _archive_col_ratios = [1, 1.3, 1.8, 1.1, 1.2, 1]

        for _idx, meeting in enumerate(_sorted_meetings):
            _group_key = _meeting_year_term_group(meeting)
            _is_new_group = _idx == 0 or _meeting_year_term_group(_sorted_meetings[_idx - 1]) != _group_key
            if _is_new_group:
                _year, _term_num = _group_key
                if _term_num:
                    _term_label = f"Term {_term_num}, {_year}"
                elif _year:
                    _term_label = f"{_year} — term not recorded"
                else:
                    _term_label = "⚠️ Date/term missing on these records — check them below"
                _term_group_meetings = _archive_groups[_group_key]
                st.markdown(
                    f'<div style="margin-top:28px;margin-bottom:0;padding:8px 14px;'
                    f'background:#{_CLC_TEAL};border-radius:6px 6px 0 0;'
                    f'font-family:&quot;Segoe UI&quot;,Arial,sans-serif;'
                    f'font-size:16px;font-weight:700;color:white;">'
                    f'🗓️ {_term_label} &nbsp;·&nbsp; {len(_term_group_meetings)} meeting(s)</div>',
                    unsafe_allow_html=True
                )
                # Header row for this term's table, column-aligned with the
                # data rows below via the same st.columns ratios.
                _hcols = st.columns(_archive_col_ratios, gap="small")
                for _hc, _htext in zip(_hcols, ["Week", "Date", "Minute Taker", "Minutes", "Attachments", ""]):
                    _hc.markdown(
                        f'<div style="background:#{_CLC_TEAL_LIGHT};padding:6px 8px;'
                        f'border-bottom:2px solid #{_CLC_TEAL};font-family:&quot;Segoe UI&quot;,Arial,sans-serif;'
                        f'font-size:12.5px;font-weight:700;color:#{_CLC_TEAL};">{_htext}</div>',
                        unsafe_allow_html=True
                    )

            _has_min = bool((meeting.get('minutes') or '').strip())
            _att_count = 0
            for _field in ('meeting_attachments', 'pd_attachments'):
                try:
                    _raw = meeting.get(_field)
                    _parsed = json.loads(_raw) if isinstance(_raw, str) else (_raw or [])
                    _att_count += len(_parsed)
                except Exception:
                    pass
            _wkey = (*_group_key, str(meeting.get('week_number', '')).strip())
            _is_dup = _week_counts.get(_wkey, 1) > 1
            _open_key = f"_archive_row_open_{meeting['id']}"
            _is_open = st.session_state.get(_open_key, False)

            _row_bg = "#FFF4E1" if _is_dup else ("#FAFBFC" if _idx % 2 else "white")
            _cell = (f'background:{_row_bg};padding:8px;border-bottom:1px solid #{_CLC_BORDER};'
                     f'font-family:&quot;Segoe UI&quot;,Arial,sans-serif;font-size:13.5px;')
            _rcols = st.columns(_archive_col_ratios, gap="small")
            _week_text = f"⚠️ Week {meeting.get('week_number', '?')}" if _is_dup else f"Week {meeting.get('week_number', '?')}"
            _rcols[0].markdown(f'<div style="{_cell}">{_week_text}</div>', unsafe_allow_html=True)
            _rcols[1].markdown(f'<div style="{_cell}">{meeting.get("meeting_date", "")}</div>', unsafe_allow_html=True)
            _rcols[2].markdown(f'<div style="{_cell}">{meeting.get("minute_taker", "Unknown")}</div>', unsafe_allow_html=True)
            _rcols[3].markdown(f'<div style="{_cell}text-align:center;">{"✅" if _has_min else "—"}</div>', unsafe_allow_html=True)
            _rcols[4].markdown(f'<div style="{_cell}text-align:center;">{_att_count if _att_count else "—"}</div>', unsafe_allow_html=True)
            with _rcols[5]:
                st.markdown(
                    f'<div style="background:{_row_bg};padding:2px 0 2px 4px;'
                    f'border-bottom:1px solid #{_CLC_BORDER};">', unsafe_allow_html=True
                )
                if st.button("▾ Close" if _is_open else "▸ Open", key=f"toggle_archived_{meeting['id']}",
                             use_container_width=True):
                    st.session_state[_open_key] = not _is_open
                    st.rerun()
                st.markdown('</div>', unsafe_allow_html=True)

            if _is_open:
                with st.container(border=True):
                    st.write(f"**Attendees:** {meeting.get('attendees', 'Not recorded')}")
                    st.write(f"**Apologies:** {meeting.get('apologies', 'None')}")
                
                    st.markdown("---")
                    st.write("**📄 Minutes:**")
                    meeting_minutes = meeting.get('minutes', 'No minutes recorded')
                    if meeting_minutes and meeting_minutes != 'No minutes recorded':
                        st.markdown('''<style>
    .clc-minutes { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 14px !important; line-height: 1.7 !important; color: #1a1a1a !important; }
    .clc-minutes p, .clc-minutes li, .clc-minutes td, .clc-minutes th, .clc-minutes strong, .clc-minutes em { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 14px !important; }
    .clc-minutes h1,.clc-minutes h2,.clc-minutes h3,.clc-minutes h4 { font-family: "Segoe UI", Arial, sans-serif !important; font-size: 15px !important; font-weight: 700 !important; margin-top: 1em; }
    .clc-minutes table { border-collapse: collapse; width: 100%; }
    .clc-minutes th { background: #f0f0f0; padding: 6px 10px; border: 1px solid #ddd; }
    .clc-minutes td { padding: 6px 10px; border: 1px solid #ddd; }
    </style>''', unsafe_allow_html=True)
                        st.markdown(f'<div class="clc-minutes">' + _minutes_display_markdown(meeting_minutes) + '</div>', unsafe_allow_html=True)
                    else:
                        st.info("No minutes recorded for this meeting")
                
                    # Actions / Attachments / PD are intentionally NOT duplicated here —
                    # they only ever matter in the context of editing the meeting, so
                    # click "Edit / Add to This Meeting" below to see and work with them
                    # rather than cluttering this quick-view card.

                    # ── Edit + download + delete this archived meeting ──────────────
                    st.markdown("---")
                    col_arc_edit, col_arc_dl, col_arc_del = st.columns([1.3, 1, 1])
                    with col_arc_edit:
                        if st.button("✏️ Edit / Add to This Meeting", key=f"edit_archived_{meeting['id']}",
                                     type="primary", use_container_width=True):
                            _edit_label = (
                                f"{meeting['meeting_date']} - {normalise_term_short(meeting.get('term', '?'))} "
                                f"W{meeting.get('week_number', '?')} - {meeting.get('minute_taker', 'Unknown')}"
                            )
                            st.session_state["_pending_meeting_jump"] = _edit_label
                            st.session_state.current_staff_meeting_id = meeting['id']
                            st.success(
                                "✅ Loaded. Click the **📝 Current Meeting** tab at the top of the page "
                                "to continue editing this meeting — it's now pre-selected there."
                            )
                            st.rerun()
                    with col_arc_dl:
                        if DOCX_AVAILABLE and (meeting.get('minutes') or '').strip():
                            st.download_button(
                                "📥 Download Minutes (.docx)",
                                data=_build_minutes_docx_bytes(meeting),
                                file_name=f"Staff_Meeting_Minutes_{meeting.get('meeting_date', '')}.docx",
                                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                                use_container_width=True,
                                key=f"download_archived_{meeting['id']}"
                            )
                        else:
                            st.button("📥 Download Minutes (.docx)", disabled=True,
                                      use_container_width=True, key=f"download_archived_disabled_{meeting['id']}")

                    with col_arc_del:
                        confirm_key = f"confirm_delete_archived_{meeting['id']}"
                        if st.session_state.get(confirm_key):
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("⚠️ Confirm delete", key=f"confirm_del_{meeting['id']}",
                                            type="secondary", use_container_width=True):
                                    try:
                                        supabase.table('staff_meetings').delete().eq('id', meeting['id']).execute()
                                        st.success("✅ Deleted.")
                                        st.session_state[confirm_key] = False
                                        st.rerun()
                                    except Exception as e:
                                        st.error(f"⚠️ Could not delete: {e}")
                            with col_no:
                                if st.button("Cancel", key=f"cancel_del_{meeting['id']}", use_container_width=True):
                                    st.session_state[confirm_key] = False
                                    st.rerun()
                        else:
                            if st.button("🗑️ Delete this meeting", key=f"del_{meeting['id']}", use_container_width=True):
                                st.session_state[confirm_key] = True
                                st.rerun()
    else:
        st.info("No archived meetings yet.")

with tab1:
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # MEETING FORM
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Meeting Details")
    
    col1, col2, col3 = st.columns(3)
    
    # Defaults
    if selected_record:
        default_date = datetime.date.fromisoformat(selected_record['meeting_date'])
        default_term = selected_record.get('term', 'T2')
        default_week = selected_record.get('week_number', 1)
    else:
        default_date = datetime.date.today()
        default_term = 'T2'
        default_week = 1

    _term_opts = ["T1", "T2", "T3", "T4"]
    _term_idx  = _term_opts.index(normalise_term_short(default_term)) if normalise_term_short(default_term) in _term_opts else 1

    # Namespaced per meeting id — otherwise, like every other widget in this
    # file, these only pick up a NEW meeting's date/term/week/taker the very
    # first time they're ever rendered; every meeting opened afterwards (e.g.
    # via "Edit / Add to This Meeting" from the Archive tab) would silently
    # keep showing whichever meeting's values were last typed here, and
    # clicking Save Meeting would then overwrite the correct record's real
    # date/term/week with those stale leftover values — this is almost
    # certainly how meetings ended up looking duplicated/wrong before.
    _details_mkey = st.session_state.current_staff_meeting_id or "new"

    with col1:
        meeting_date = st.date_input("Meeting Date", value=default_date, key=f"staff_date_{_details_mkey}")

    with col2:
        term = st.selectbox("Term", options=_term_opts, index=_term_idx, key=f"staff_term_{_details_mkey}")

    with col3:
        week_number = st.number_input("Week Number", min_value=1, max_value=11, value=default_week, key=f"staff_week_{_details_mkey}")

    default_minute_taker = selected_record.get('minute_taker', '') if selected_record else ''
    minute_taker = st.text_input("Minute Taker", value=default_minute_taker, key=f"minute_taker_{_details_mkey}")
    
    st.markdown("---")
    # ══════════════════════════════════════════════════════════════════════════════
    # 1. STAFF BULLETIN FOR THE WEEK
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📋 Staff Bulletin (This Week)")
    
    # Auto-load bulletin from Staff Bulletin tool based on term and week
    try:
        # Normalise term to "Term N" format (Staff Bulletin always stores it that way)
        term_long = normalise_term_long(term)
        # Find bulletin edition linked to this meeting's term/week
        bulletin_result = supabase_ops.table('weekly_editions').select('*').eq('meeting_linked', True).eq('meeting_term', term_long).eq('meeting_week', int(week_number)).execute()

        # ── Bulletin link status ──────────────────────────────────────────────
        with st.expander("🗓️ Bulletin link status", expanded=False):
            st.write(f"**Querying:** meeting_linked=True, meeting_term=`{term_long}`, meeting_week=`{int(week_number)}`")
            all_linked = supabase_ops.table('weekly_editions').select('id,week_label,week_start,meeting_linked,meeting_term,meeting_week').eq('meeting_linked', True).execute()
            st.write("**All linked editions in Supabase:**")
            if all_linked.data:
                import re as _re
                from datetime import date as _date, timedelta as _td
                _TERM_STARTS = {"Term 1": _date(2026,1,27), "Term 2": _date(2026,4,27),
                                "Term 3": _date(2026,7,20), "Term 4": _date(2026,10,12)}
                for row in all_linked.data:
                    st.write(f"- `{row.get('week_label')}` → term=`{repr(row.get('meeting_term'))}` week=`{repr(row.get('meeting_week'))}`")
                    # Offer repair if week looks wrong
                    ws = row.get('week_start')
                    stored_term = row.get('meeting_term', '')
                    if ws and stored_term in _TERM_STARTS:
                        d = _date.fromisoformat(str(ws))
                        correct_week = (d - _TERM_STARTS[stored_term]).days // 7 + 1
                        correct_week = max(1, correct_week)
                        if correct_week != row.get('meeting_week'):
                            st.warning(f"  ⚠️ Week should be **{correct_week}** (stored as {row.get('meeting_week')})")
                            if st.button(f"🔧 Fix to Week {correct_week}", key=f"repair_{row['id']}"):
                                supabase_ops.table('weekly_editions').update(
                                    {"meeting_week": correct_week}
                                ).eq('id', row['id']).execute()
                                st.success(f"Fixed! Now week {correct_week}")
                                st.rerun()
            else:
                st.write("None found — nothing is linked at all in Supabase")
            st.write(f"**Query result:** {bulletin_result.data}")
        # ─────────────────────────────────────────────────────────────────────
        
        if bulletin_result.data and len(bulletin_result.data) > 0:
            edition = bulletin_result.data[0]
            
            # Get all notices for this edition
            notices_result = supabase_ops.table('notices').select('*').eq('edition_id', edition['id']).order('created_at').execute()

            is_draft = edition.get('status', 'draft') == 'draft'

            # Status badge
            if is_draft:
                st.markdown(
                    '<div style="background:#fef9c3;border:1px solid #fde047;border-radius:6px;'
                    'padding:8px 14px;font-size:13px;color:#854d0e;margin-bottom:10px;">'
                    '🟡 <strong>Bulletin is in draft</strong> — items are live here as they are added. '
                    'Staff will see the full bulletin once you click Send.</div>',
                    unsafe_allow_html=True
                )
            else:
                st.markdown(
                    '<div style="background:#dcfce7;border:1px solid #86efac;border-radius:6px;'
                    'padding:8px 14px;font-size:13px;color:#14532d;margin-bottom:10px;">'
                    '✅ <strong>Bulletin sent</strong> — all items confirmed.</div>',
                    unsafe_allow_html=True
                )

            if notices_result.data:
                for notice in notices_result.data:
                    category = notice.get('category', 'general')
                    author   = notice.get('author', 'Staff')
                    with st.expander(f"📌 {notice['title']} ({category.upper()})"):
                        st.write(f"**From:** {author}")
                        st.write(f"**Category:** {category.title()}")
                        st.markdown("---")
                        st.write(notice.get('content', ''))
            else:
                st.info("No bulletin items added yet — they will appear here as they are added in the Bulletin tool.")

            # Allow admin to remove the bulletin link
            st.write("")
            edition_id_str = str(edition['id'])
            if not st.session_state.get(f"mtg_unlink_confirm_{edition_id_str}"):
                if st.button("🗑️ Remove bulletin from this meeting", key=f"mtg_unlink_{edition_id_str}",
                             help="Detaches this bulletin so it can be re-linked or replaced"):
                    st.session_state[f"mtg_unlink_confirm_{edition_id_str}"] = True
                    st.rerun()
            else:
                st.warning(f"Remove the **{edition.get('week_label', '')}** bulletin from this meeting? "
                           "It can be re-linked from the Staff Bulletin tool at any time.")
                cu1, cu2 = st.columns(2)
                with cu1:
                    if st.button("Yes, remove it", key=f"mtg_unlink_yes_{edition_id_str}", type="primary"):
                        try:
                            supabase_ops.table('weekly_editions').update({
                                "meeting_linked": False,
                                "meeting_term":   None,
                                "meeting_week":   None,
                            }).eq('id', edition['id']).execute()
                            st.session_state.pop(f"mtg_unlink_confirm_{edition_id_str}", None)
                            st.success("Bulletin removed from this meeting.")
                            time.sleep(1)
                            st.rerun()
                        except Exception as ue:
                            st.error(f"Could not remove: {ue}")
                with cu2:
                    if st.button("Cancel", key=f"mtg_unlink_cancel_{edition_id_str}"):
                        st.session_state.pop(f"mtg_unlink_confirm_{edition_id_str}", None)
                        st.rerun()
        else:
            st.info(f"ℹ️ No bulletin linked for {term_long} Week {int(week_number)} yet")
            st.caption("The bulletin will appear here automatically once the Staff Bulletin tool opens this week's edition.")
    
    except Exception as e:
        st.warning(f"Could not load bulletin: {e}")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 2. ATTENDANCE
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("👥 Attendance")
    st.caption(f"Staff list loaded from: {STAFF_ROSTER_SOURCE} ({len(STAFF_ROSTER)} names). "
               f"To fix a name, edit `DEFAULT_STAFF_ROSTER` in the code or set STAFF_NAMES in Render.")

    _att_mkey = st.session_state.current_staff_meeting_id or "new"
    default_attendees = selected_record.get('attendees', '') if selected_record else ''
    default_apologies = selected_record.get('apologies', '') if selected_record else ''
    attendees, apologies = _render_roster_attendance(
        "Meeting", f"meeting_att_{_att_mkey}", STAFF_ROSTER, default_attendees, default_apologies
    )
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 3. ACKNOWLEDGEMENT OF COUNTRY
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("🪃 Acknowledgement of Country")
    
    # Video playback - Read from environment variable
    VIDEO_URL = os.environ.get("ACKNOWLEDGEMENT_VIDEO_URL", "") or st.secrets.get("ACKNOWLEDGEMENT_VIDEO_URL", "")
    
    if VIDEO_URL:
        with st.expander("📹 Watch Acknowledgement of Country Video", expanded=False):
            st.video(VIDEO_URL)
            st.caption("Play this video at the start of the meeting")
    else:
        st.info("📹 **Video not configured yet** - Add ACKNOWLEDGEMENT_VIDEO_URL to Render environment variables to enable video playback")
    
    # Text version option
    with st.expander("📄 Or Read Acknowledgement of Country (Text Version)", expanded=False):
        st.markdown("""
        *"Before we begin, I acknowledge the Kaurna people as the Traditional Custodians of this land, and pay my respects to their Elders past, present, and emerging.*
        
        *As a Learning and Behaviour Unit, we recognise that many of our students carry trauma — and we acknowledge the particular trauma that colonisation has caused and continues to cause for Aboriginal and Torres Strait Islander peoples.*
        
        *We are committed to trauma-informed, culturally responsive practice that honours the strengths, resilience, and cultures of all our students and their families.*
        
        *I extend my respect to any Aboriginal and Torres Strait Islander people present today."*
        """)
        st.caption("Chair can read this aloud at the start of the meeting")
    
    acknowledgement_done = st.checkbox("✅ Acknowledgement completed", value=selected_record.get('acknowledgement_done', False) if selected_record else False)
    acknowledgement_by = st.text_input("Led by", value=selected_record.get('acknowledgement_by', '') if selected_record else '', placeholder="Who led the Acknowledgement?")
    
    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 4. BSEM ACTIVITY (5 mins)
    # ══════════════════════════════════════════════════════════════════════════════

    st.subheader("🎯 BSEM Activity (5 mins)")

    # Suggested icebreaker for this week
    icebreaker = _bsem_icebreaker_for(meeting_date, term, week_number)

    _bsem_mkey = st.session_state.current_staff_meeting_id or "new"
    _bsem_raw = selected_record.get('icebreaker', '') if selected_record else ''
    _bsem_mode0, _bsem_name0, _bsem_expl0, _bsem_notes0 = _parse_bsem_field(_bsem_raw)

    _bsem_choice_key = f"bsem_choice_{_bsem_mkey}"
    if _bsem_choice_key not in st.session_state:
        st.session_state[_bsem_choice_key] = "Different activity" if _bsem_mode0 == "different" else "Suggested activity"

    bsem_choice = st.radio(
        "Activity for this meeting", ["Suggested activity", "Different activity"],
        key=_bsem_choice_key, horizontal=True
    )

    bsem_name, bsem_explanation = _bsem_name0, _bsem_expl0
    if bsem_choice == "Suggested activity":
        with st.expander(f"💡 Suggested Activity: **{icebreaker['name']}**", expanded=True):
            st.write(f"**Time:** {icebreaker['time']}")
            st.write(f"**Instructions:** {icebreaker['instructions']}")
    else:
        bsem_name = st.text_input("Activity name", value=_bsem_name0,
                                   key=f"bsem_name_{_bsem_mkey}",
                                   placeholder="e.g. Two Truths and a Lie")
        bsem_explanation = st.text_area("Quick explanation", value=_bsem_expl0,
                                        height=70, key=f"bsem_explanation_{_bsem_mkey}",
                                        placeholder="Briefly explain how it works...")

    icebreaker_notes = st.text_area("Activity Notes (optional)",
                                    value=_bsem_notes0,
                                    height=80,
                                    placeholder="Any notes about how the activity went...",
                                    key=f"icebreaker_{_bsem_mkey}")

    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 5. AGENDA ITEMS
    # ══════════════════════════════════════════════════════════════════════════════
    
    st.subheader("📑 Meeting Agenda")

    # Load agenda data
    if selected_record and selected_record.get('agenda_items'):
        try:
            agenda_data = json.loads(selected_record['agenda_items']) if isinstance(selected_record['agenda_items'], str) else selected_record['agenda_items']
        except:
            agenda_data = {}
    else:
        agenda_data = {}

    # Initialise in agenda_data
    if 'additional_agenda' not in agenda_data:
        agenda_data['additional_agenda'] = []

    # Use session state as the live list so changes survive widget rerenders.
    # Normalise each entry to a plain label string here — some older records
    # saved additional agenda items as {'item':..., 'raised_by':...} dicts
    # rather than plain strings, which crashed downstream code that only
    # ever expected strings (e.g. joining/rendering them directly).
    def _normalise_agenda_item(entry):
        if isinstance(entry, dict):
            _text = entry.get('item') or entry.get('text') or entry.get('label') or ''
            _by = entry.get('raised_by') or entry.get('submitted_by') or ''
            return f"📌 {_text}  — submitted by {_by}" if _by else f"📌 {_text}"
        return str(entry)

    ss_key = f"addl_items_{st.session_state.current_staff_meeting_id or 'new'}"
    if ss_key not in st.session_state:
        st.session_state[ss_key] = [_normalise_agenda_item(e) for e in agenda_data.get('additional_agenda', [])]

    additional_items = st.session_state[ss_key]

    # ── Minutes blocks (shared with the "📄 Meeting Minutes" section further
    # down the page) — seeded here, BEFORE the Standing Items loop below, so
    # each Standing Item's minutes/action fields can render directly inside
    # its own box right here, rather than a second, duplicate "Standing
    # Items" block appearing again later on the page.
    minutes = selected_record.get('minutes', '') if selected_record else ''
    _minutes_mkey = st.session_state.current_staff_meeting_id or "new"
    _blocks_ss_key = f"minutes_blocks_{_minutes_mkey}"
    if _blocks_ss_key not in st.session_state:
        st.session_state[_blocks_ss_key] = _seed_minutes_blocks(minutes, additional_items)
    _sync_additional_minutes_blocks(st.session_state[_blocks_ss_key], additional_items)
    blocks = st.session_state[_blocks_ss_key]
    _minutes_editor_key_prefix = f"minutes_editor_{_minutes_mkey}"
    _standing_blocks = [b for b in blocks if b["kind"] == "standing"]

    # If an AI generation step (further down the page) just updated `blocks`
    # directly, this resyncs every affected widget's session_state from that
    # fresh data BEFORE any of those widgets render below — see
    # _sync_all_minutes_widgets_from_blocks for why this has to happen here.
    _pending_minutes_sync_key = f"_pending_minutes_widget_sync_{_minutes_mkey}"
    if st.session_state.pop(_pending_minutes_sync_key, False):
        _sync_all_minutes_widgets_from_blocks(blocks, _minutes_editor_key_prefix)

    # Likewise for "Clear draft" below — it resets the blocks DATA immediately,
    # but the widgets for the keys that were showing the old text still need
    # clearing out before they render again, which can only safely happen
    # here, before any of them are instantiated this run.
    _pending_minutes_clear_key = f"_pending_minutes_clear_{_minutes_mkey}"
    if st.session_state.pop(_pending_minutes_clear_key, False):
        for _k in _all_minutes_widget_keys(blocks, _minutes_editor_key_prefix):
            st.session_state.pop(_k, None)

    # Standing agenda items
    st.write("**Standing Items:**")

    _agenda_mkey = st.session_state.current_staff_meeting_id or "new"
    for _std_idx, item in enumerate(STANDING_AGENDA_ITEMS):
        with st.expander(f"📌 {item}"):
            # Namespaced per meeting (_agenda_mkey) for the same reason as the
            # Minutes section fields below: Streamlit only honours `value=`
            # the first time a widget key is created, so an un-namespaced key
            # here would keep showing one meeting's agenda notes on every
            # other meeting for the rest of the session.
            agenda_data[item] = st.text_area(
                f"Notes for {item}",
                value=agenda_data.get(item, ''),
                height=100,
                key=f"agenda_{_agenda_mkey}_{item.replace(' ', '_')}",
                placeholder=f"Add information/updates for {item}..."
            )
            st.markdown("---")
            st.caption("📝 Minutes for this item — filled in manually, or converted from a "
                       "transcript in the Meeting Minutes section below.")
            _render_minutes_block_fields(blocks, _standing_blocks[_std_idx], _std_idx,
                                          _minutes_editor_key_prefix, show_heading=False)

    # ── ADDITIONAL AGENDA ITEMS ───────────────────────────────────────────────
    st.markdown("---")
    st.markdown("#### 📋 Additional Agenda Items")

    # ── Load Staff Submissions button ─────────────────────────────────────────
    col_load1, col_load2 = st.columns([2, 3])
    with col_load1:
        if st.button("📥 Load Staff Submissions", key="load_pending_items", type="secondary",
                     use_container_width=True):
            try:
                pending_result = supabase_ops.table('staff_agenda_items') \
                                             .select('*').eq('status', 'pending').execute()
                if pending_result.data:
                    loaded_count = 0
                    for item in pending_result.data:
                        label = f"📌 {item['item_text']}  — submitted by {item['submitted_by']}"
                        if label not in additional_items:
                            additional_items.append(label)
                            loaded_count += 1
                        supabase_ops.table('staff_agenda_items') \
                                    .update({'status': 'added'}).eq('id', item['id']).execute()

                    st.session_state[ss_key] = additional_items

                    if st.session_state.current_staff_meeting_id:
                        agenda_data['additional_agenda'] = additional_items
                        supabase.table('staff_meetings').update({
                            "agenda_items": json.dumps(agenda_data)
                        }).eq('id', st.session_state.current_staff_meeting_id).execute()

                    if loaded_count:
                        st.success(f"✅ {loaded_count} item(s) loaded!")
                    else:
                        st.info("No new pending submissions.")
                    st.rerun()
                else:
                    st.info("No pending agenda items found.")
            except Exception as e:
                st.error(f"Error: {e}")
    with col_load2:
        st.caption("Pulls items submitted by staff via the Submit Agenda Item tool")

    st.write("")

    # ── Display current items as cards ────────────────────────────────────────
    if additional_items:
        st.markdown(
            f'<div style="font-size:13px;color:#6b7280;margin-bottom:8px;">'
            f'{len(additional_items)} item(s) on agenda</div>',
            unsafe_allow_html=True
        )
        items_to_remove = []
        for i, item_text in enumerate(additional_items):
            col_item, col_del = st.columns([11, 1])
            with col_item:
                st.markdown(
                    f'<div style="background:#f0fdf4;border:1px solid #86efac;border-radius:8px;'
                    f'padding:10px 14px;font-family:Segoe UI,Arial,sans-serif;font-size:14px;'
                    f'color:#14532d;margin-bottom:4px;">{item_text}</div>',
                    unsafe_allow_html=True
                )
            with col_del:
                if st.button("✕", key=f"remove_item_{i}", help="Remove this item"):
                    items_to_remove.append(i)

        if items_to_remove:
            for idx in sorted(items_to_remove, reverse=True):
                additional_items.pop(idx)
            st.session_state[ss_key] = additional_items
            st.rerun()
    else:
        st.markdown(
            '<div style="background:#f9fafb;border:1px dashed #d1d5db;border-radius:8px;'
            'padding:16px;text-align:center;color:#9ca3af;font-size:13px;">'
            'No additional items yet — load staff submissions or add one below</div>',
            unsafe_allow_html=True
        )

    # ── Manual add ────────────────────────────────────────────────────────────
    # The text box is cleared via a "pending clear" flag checked/applied
    # HERE, before the widget below is instantiated — setting a widget's
    # session_state key directly after it's already been rendered earlier in
    # the same script run raises StreamlitWidgetAlreadyInstantiatedError
    # (which is what crashed this section); the flag itself is a plain,
    # non-widget key, so setting it from the button below is safe.
    _new_agenda_mkey = st.session_state.current_staff_meeting_id or "new"
    _new_agenda_key = f"new_agenda_item_{_new_agenda_mkey}"
    _clear_flag_key = f"_clear_new_agenda_item_{_new_agenda_mkey}"
    if st.session_state.get(_clear_flag_key):
        st.session_state[_new_agenda_key] = ""
        st.session_state[_clear_flag_key] = False

    st.write("")
    col_new, col_add = st.columns([4, 1])
    with col_new:
        new_item = st.text_input("Add an agenda item", key=_new_agenda_key,
                                 placeholder="Type item and click Add →",
                                 label_visibility="collapsed")
    with col_add:
        if st.button("➕ Add", key="add_agenda_item", use_container_width=True):
            if new_item.strip():
                additional_items.append(new_item.strip())
                st.session_state[ss_key] = additional_items
                st.session_state[_clear_flag_key] = True
                st.rerun()

    # Keep agenda_data in sync with session state list
    additional_items = st.session_state[ss_key]
    agenda_data['additional_agenda'] = additional_items

    st.markdown("---")
    
    # ══════════════════════════════════════════════════════════════════════════════
    # 6. MINUTES (Manual OR AI Transcript) — both land in the same blocks: one
    # per Standing Item (matching the Agenda section above), one per this
    # meeting's Additional Agenda Items, and a dynamic "Any Other Items" block
    # for anything raised that wasn't on the agenda.
    # ══════════════════════════════════════════════════════════════════════════════

    # `minutes`, `blocks` and `_minutes_editor_key_prefix` were already
    # seeded up in the Agenda section above (so Standing Items can render
    # their minutes/action fields directly in their own box there) — reused
    # as-is here rather than re-seeded, so there's one shared set of blocks
    # regardless of where on the page they're being edited.
    has_existing_minutes = bool(minutes and minutes.strip())

    # ── Keep this section's open/closed state and entry-method choice pinned
    # per-meeting in session_state, seeded ONCE when a meeting is opened.
    # Recomputing `expanded=` fresh from has_existing_minutes on every rerun
    # (as this used to do) forces the expander back to its default state the
    # instant something inside it — like the radio button below — triggers a
    # rerun, which is what made the section look like it "wouldn't expand" or
    # "wouldn't show" the AI transcript box after switching to it.
    _minutes_expander_key = f"_minutes_section_open_{_minutes_mkey}"
    if _minutes_expander_key not in st.session_state:
        st.session_state[_minutes_expander_key] = not has_existing_minutes

    with st.expander("📄 Meeting Minutes", expanded=st.session_state[_minutes_expander_key]):

        minutes_method = st.radio("Minutes Entry Method",
                                  options=["✍️ Manual Entry", "🤖 AI from Transcript"],
                                  horizontal=True, key=f"minutes_entry_method_{_minutes_mkey}")

        # Always defined regardless of entry method, so the PD section further
        # down can offer "reuse the main meeting transcript/synthesis for PD
        # too" even when Manual Entry is selected up here.
        transcript_text = ""
        synthesis_for_minutes = ""

        if minutes_method == "✍️ Manual Entry":
            st.caption("Enter notes directly below. Leave an item's minutes blank if it wasn't discussed.")

        else:  # AI from Transcript
            st.markdown("**Paste your transcript below, or upload a file (.txt / .docx)**")
            st.caption(
                "Two steps: Step 1 condenses the transcript into a short synthesis of what was "
                "actually discussed — the Acknowledgement of Country, icebreaker activity and any "
                "Professional Development content are dropped automatically, not just summarised. "
                "Step 2 sorts that short synthesis (not the raw transcript) into the Standing Items, "
                "this meeting's Additional Agenda Items, and anything else it picks up that wasn't "
                "on the agenda — which is what keeps each AI call well under Groq's token limit."
            )

            _mkey = st.session_state.current_staff_meeting_id or "new"
            synthesis_state_key = f"transcript_synthesis_{_mkey}"
            synthesis_widget_key = f"synthesis_editor_{_mkey}"

            # ── Paste or upload ───────────────────────────────────────────────
            transcript_text = ""

            pasted = st.text_area(
                "Paste transcript here",
                height=180,
                key=f"transcript_paste_{_mkey}",
                placeholder="Paste your meeting transcript or voice-to-text output here…"
            )
            if pasted.strip():
                transcript_text = pasted.strip()

            transcript_file = st.file_uploader(
                "Or upload a file",
                type=['txt', 'docx'],
                key=f"transcript_upload_{_mkey}",
                label_visibility="collapsed"
            )
            if transcript_file and not transcript_text:
                if transcript_file.name.endswith('.txt'):
                    transcript_text = transcript_file.read().decode('utf-8')
                else:
                    if DOCX_AVAILABLE:
                        try:
                            doc = docx.Document(transcript_file)
                            transcript_text = '\n'.join([p.text for p in doc.paragraphs])
                        except Exception as e:
                            st.error(f"Could not read .docx: {e}")
                    else:
                        st.error("python-docx not installed — please paste the transcript instead.")

            st.markdown("---")

            # ══════════════════════════════════════════════════════════════════
            # STEP 1 — Synthesise the transcript. This drops the Acknowledgement
            # of Country and icebreaker activity entirely and condenses the rest,
            # so the text that later gets classified into sections is small — the
            # raw transcript never goes near the classifier prompt.
            # ══════════════════════════════════════════════════════════════════
            st.markdown("##### Step 1 · Synthesise transcript")

            if transcript_text and GROQ_KEY:
                if st.button("🧹 Synthesise Transcript", key="synthesise_transcript_btn"):
                    with st.spinner("Condensing transcript…"):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            transcript_for_synthesis, was_truncated = _fit_to_groq_budget(
                                transcript_text, max_tokens=1200, prompt_overhead_tokens=350
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ This transcript is longer than the AI can read in one go "
                                    "(Groq's 8,000 tokens/minute limit on the current plan). Only "
                                    "the first part was synthesised. Paste the rest of the transcript "
                                    "above and click **Synthesise Transcript** again — the new part "
                                    "will be added to the synthesis below rather than replacing it."
                                )

                            synthesis_prompt = f"""Read the transcript of a school staff meeting below
and condense it into a short, information-dense synthesis of what was
actually discussed, ready to be sorted into meeting minutes afterwards.

Rules:
1. COMPLETELY leave out the Acknowledgement of Country (the formal
   acknowledgement/welcome-to-country reading) — do not mention that it
   happened, just omit it entirely.
2. COMPLETELY leave out the icebreaker / BSEM activity (warm-up games,
   check-ins, "two truths and a lie", wellbeing rounds, etc.) — omit it
   entirely, do not summarise it.
3. COMPLETELY leave out any Professional Development (PD) session content —
   that's documented separately. If this transcript also contains a PD
   session mixed in with the regular meeting business, leave the PD part
   out of this synthesis entirely.
4. Keep every substantive point: updates given, decisions made, concerns
   raised, and action items (what needs to be done, who's responsible, and
   any due date mentioned).
5. Keep staff names, dates and figures that are mentioned.
6. Write in tight prose or bullet points — no filler, no small talk, no
   repeated pleasantries.
7. Do not invent anything that isn't in the transcript.

Return ONLY the condensed synthesis text — no preamble, no commentary.

TRANSCRIPT:
{transcript_for_synthesis}"""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": synthesis_prompt}],
                                temperature=0.2,
                                max_tokens=1200
                            )
                            new_synthesis = response.choices[0].message.content.strip()

                            existing_synthesis = (st.session_state.get(synthesis_state_key) or "").strip()
                            if existing_synthesis:
                                combined = existing_synthesis + "\n\n— continued —\n\n" + new_synthesis
                                st.success("✅ Transcript synthesised and added to the synthesis below.")
                            else:
                                combined = new_synthesis
                                st.success("✅ Transcript synthesised — review it below before generating minutes.")

                            st.session_state[synthesis_state_key] = combined
                            # Widget key already exists once rendered, so setting it here
                            # (not just the value= below) is what actually updates the box.
                            st.session_state[synthesis_widget_key] = combined

                        except Exception as e:
                            st.error(f"Synthesis failed: {e}")

            elif transcript_text and not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured.")
            else:
                st.caption("Paste or upload a transcript above, then click **Synthesise Transcript**.")

            current_synthesis = st.session_state.get(synthesis_state_key, "")

            synthesis_for_minutes = ""
            if current_synthesis:
                col_syn, col_syn_clear = st.columns([5, 1])
                with col_syn:
                    st.caption(
                        "Review/edit the synthesis below — this is what Step 2 sorts into "
                        "sections, not the raw transcript."
                    )
                with col_syn_clear:
                    if st.button("🗑️ Clear", key="clear_synthesis_btn", help="Clear the synthesis and start over"):
                        st.session_state[synthesis_state_key] = ""
                        st.session_state.pop(synthesis_widget_key, None)
                        st.rerun()
                synthesis_for_minutes = st.text_area(
                    "Transcript synthesis",
                    value=current_synthesis,
                    height=180,
                    key=synthesis_widget_key,
                    label_visibility="collapsed"
                )

            st.markdown("---")

            # ══════════════════════════════════════════════════════════════════
            # STEP 2 — Sort the (short) synthesis into the Standing Items, this
            # meeting's Additional Agenda Items, and anything else raised
            # ══════════════════════════════════════════════════════════════════
            st.markdown("##### Step 2 · Generate structured minutes")

            if synthesis_for_minutes.strip() and GROQ_KEY:
                if st.button("🤖 Generate Structured Minutes", type="primary", key="generate_minutes_btn"):

                    with st.spinner("Generating structured minutes…"):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            synthesis_for_ai, was_truncated = _fit_to_groq_budget(
                                synthesis_for_minutes.strip(), max_tokens=2600, prompt_overhead_tokens=400
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ Even the synthesis is longer than the AI can process in one "
                                    "go. Trim the synthesis above (or split the transcript into "
                                    "smaller parts at Step 1) and try again."
                                )

                            additional_labels = [_clean_agenda_label(x) for x in additional_items]
                            standing_list = "\n".join(f"- {label}" for label in STANDING_AGENDA_ITEMS)
                            additional_list = ("\n".join(f"- {label}" for label in additional_labels)
                                               if additional_labels else "(none for this meeting)")
                            heading_lines = [f"## STANDING: {label}" for label in STANDING_AGENDA_ITEMS]
                            heading_lines += [f"## ADDITIONAL: {label}" for label in additional_labels]
                            heading_list = "\n".join(heading_lines)

                            prompt = f"""Read the synthesis of a school staff meeting below.

This meeting has these STANDING agenda items (discussed every meeting):
{standing_list}

And these ADDITIONAL agenda items specific to THIS meeting:
{additional_list}

For EACH standing item and EACH additional item above, write a CONCISE
summary (a few sentences at most) of what was discussed and any decisions
made. If an item was not discussed at all, write exactly: "{_NIL_TEXT}"
Immediately after each item's summary, on its own line, write:
ACTION: <who is responsible and what they need to do, including a due date
if one was mentioned>
or, if there is no action for that item, write exactly:
ACTION: None

Then, separately, look for anything ELSE that was raised in the synthesis
that does NOT belong to any of the items listed above — a topic that came
up but wasn't on the agenda. For each one you find, write its own section
using the "## OTHER: <topic> | RAISED BY: <name>" heading format shown
below, naming the topic and, if you can tell, who raised it (write
"Unknown" if you can't tell). Follow it with a short summary and an ACTION
line the same way as above. If nothing else was raised, don't write any
OTHER section at all.

Do not invent information that isn't in the synthesis.

Reply in PLAIN TEXT using EXACTLY this structure — one block per item, each
starting on its own line with the heading shown, nothing else before,
between or after (no JSON, no extra commentary, no numbering). Use this
exact order for the standing/additional items, then add any OTHER blocks
after them:
{heading_list}

MEETING SYNTHESIS:
{synthesis_for_ai}"""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.2,
                                max_tokens=2600
                            )
                            raw = response.choices[0].message.content.strip()

                            # Parsed with the SAME "## Heading" parser used everywhere else in
                            # this file (Manual Entry, saved-minutes display), rather than
                            # asking the AI for JSON — a JSON response that gets cut off (long
                            # synthesis, verbose item) fails to parse AT ALL and loses
                            # everything; this plain-text format degrades gracefully instead,
                            # since each block is captured independently up to the next "## "
                            # heading — a cut-off reply only loses whichever block(s) never
                            # arrived, not everything already generated.
                            parsed_blocks = _parse_minutes_blocks(raw)

                            if not parsed_blocks:
                                with st.expander("Show raw AI response"):
                                    st.code(raw or "(empty response)")
                                raise ValueError(
                                    "The AI's reply didn't match the expected format — see the raw "
                                    "response above. Try trimming the synthesis and generating again."
                                )

                            by_standing = {b['label'].strip().lower(): b
                                           for b in parsed_blocks if b['kind'] == 'standing'}
                            by_additional = {b['label'].strip().lower(): b
                                             for b in parsed_blocks if b['kind'] == 'additional'}
                            new_others = [b for b in parsed_blocks if b['kind'] == 'other']
                            for b in new_others:
                                b['origin'] = 'ai'

                            # Update the shared blocks list in place. The Standing Items
                            # widgets live up in the Agenda section — earlier in the script
                            # than this button — so they've already rendered this run and
                            # can't have their session_state set directly here without
                            # Streamlit raising StreamlitWidgetAlreadyInstantiatedError.
                            # Instead, a pending-sync flag is set below and applied at the
                            # very top of the Agenda section on the rerun that follows,
                            # before any of these widgets are instantiated again.
                            for b in blocks:
                                if b['kind'] == 'standing':
                                    src = by_standing.get(b['label'].strip().lower())
                                elif b['kind'] == 'additional':
                                    src = by_additional.get(b['label'].strip().lower())
                                else:
                                    src = None
                                if src:
                                    b['minutes'], b['action'] = src['minutes'], src['action']

                            # Replace previously AI-generated "Any Other Items" with this
                            # fresh batch; keep anything the user added manually.
                            manual_others = [b for b in blocks if b['kind'] == 'other' and b.get('origin') != 'ai']
                            blocks[:] = [b for b in blocks if b['kind'] != 'other'] + manual_others + new_others

                            st.success("✅ Minutes generated — review below before saving.")
                            st.session_state[_pending_minutes_sync_key] = True
                            st.rerun()

                        except Exception as e:
                            st.error(f"AI extraction failed: {e}")

            elif synthesis_for_minutes.strip() and not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured.")
            else:
                st.caption("Complete Step 1 above to produce a synthesis, then generate structured minutes from it.")

        st.markdown("---")
        col_edit_hdr, col_clear = st.columns([5, 1])
        with col_edit_hdr:
            st.markdown("#### ✏️ Minutes")
        with col_clear:
            if st.button("🗑️ Clear draft", key=f"clear_minutes_draft_{_minutes_mkey}",
                         help="Clear all minutes and actions (including the Standing Item "
                              "boxes above) and start over"):
                # Reset the data now; the matching widgets (some of which — the
                # Standing Items — live up in the Agenda section, earlier in the
                # script than this button) can only safely be cleared at the top
                # of that section on the rerun this triggers, before they render.
                st.session_state[_blocks_ss_key] = _seed_minutes_blocks("", additional_items)
                st.session_state[_pending_minutes_clear_key] = True
                st.rerun()

        _render_minutes_blocks_editor(blocks, key_prefix=_minutes_editor_key_prefix)
        minutes = _build_minutes_text(blocks)

        if minutes and minutes.strip():
            with st.expander("👁️ Preview combined minutes"):
                st.markdown(_minutes_display_markdown(minutes))

    st.subheader("✅ Actions")

    # Actions are kept in session_state (namespaced per meeting), the same
    # pattern used for attachments — otherwise anything extracted, added,
    # edited or deleted here is silently lost on the very next rerun (which is
    # why this section previously looked broken). Nothing is written to the
    # database until "Save Meeting" is clicked further down the page.
    _act_mkey = st.session_state.current_staff_meeting_id or "new"
    _actions_ss_key = f"meeting_actions_{_act_mkey}"
    if _actions_ss_key not in st.session_state:
        if selected_record and selected_record.get('actions'):
            try:
                _seed_actions = json.loads(selected_record['actions']) if isinstance(selected_record['actions'], str) else selected_record['actions']
            except Exception:
                _seed_actions = []
        else:
            _seed_actions = []
        # Give every action a stable id so edits/deletes track the right row
        # even after another row is added, edited or removed.
        for _a in _seed_actions:
            if not _a.get('uid'):
                _a['uid'] = uuid.uuid4().hex
        st.session_state[_actions_ss_key] = _seed_actions

    actions = st.session_state[_actions_ss_key]

    # Every Standing/Additional/Other Item above with an "Action" line typed
    # or AI-extracted into it also gets pushed into this trackable Actions
    # list automatically (tagged with a 'source' so re-running this never
    # duplicates — editing the inline action text updates the same entry,
    # and clearing it removes the entry again). Owner/due date/done the
    # user has since edited directly below are left alone.
    _sync_minutes_actions_to_global(blocks, actions)

    # AI Action Extraction option (if minutes exist)
    _pending_key = f"_extracted_actions_pending_{_act_mkey}"
    if minutes and minutes.strip() and GROQ_KEY:
        with st.expander("🤖 Extract Actions from Minutes with AI", expanded=bool(st.session_state.get(_pending_key))):
            st.caption("AI will scan the minutes and pull out action items for you to review, amend if needed, and add below")

            if st.button("🤖 Extract Actions", type="secondary", key=f"extract_actions_ai_{_act_mkey}"):
                with st.spinner("Extracting actions from minutes..."):
                    try:
                        from groq import Groq
                        client = Groq(api_key=GROQ_KEY)

                        minutes_for_ai, was_truncated = _fit_to_groq_budget(
                            minutes, max_tokens=2000, prompt_overhead_tokens=250
                        )
                        if was_truncated:
                            st.warning(
                                "⚠️ These minutes are longer than the AI can process in one go "
                                "(Groq's 8,000 tokens/minute limit on the current plan). "
                                "Only the first part was sent — check for any actions later in "
                                "the minutes and add them manually if missed."
                            )

                        action_prompt = f"""From these meeting minutes, extract all action items.

    For each action, identify:
    1. What needs to be done (the action)
    2. Who is responsible (name if mentioned, otherwise "Unassigned")
    3. Deadline (if mentioned, otherwise leave blank)

    Return ONLY a JSON array in this exact format:
    [
      {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}},
      {{"action": "action description", "owner": "person name", "due_date": "YYYY-MM-DD or blank"}}
    ]

    If no actions found, return: []

    Meeting Minutes:
    {minutes_for_ai}

    JSON array of actions:"""

                        response = client.chat.completions.create(
                            model="openai/gpt-oss-120b",
                            messages=[{"role": "user", "content": action_prompt}],
                            temperature=0.2,
                            max_tokens=2000
                        )

                        extracted_text = response.choices[0].message.content.strip()

                        # Extract JSON array from response
                        json_match = re.search(r'\[.*\]', extracted_text, re.DOTALL)
                        if json_match:
                            extracted_actions = json.loads(json_match.group())
                            st.session_state[_pending_key] = extracted_actions
                            if not extracted_actions:
                                st.info("No action items found in minutes")
                        else:
                            st.session_state[_pending_key] = []
                            st.warning("Could not parse AI response. Add actions manually below.")
                    except Exception as e:
                        st.error(f"Action extraction failed: {e}")
                st.rerun()

            _pending = st.session_state.get(_pending_key) or []
            if _pending:
                st.success(f"✅ Found {len(_pending)} action item(s) — review below, then add them to Actions")
                for _p in _pending:
                    st.write(f"• {_p.get('action', '')} — **{_p.get('owner', 'Unassigned')}** — {_p.get('due_date') or 'No deadline'}")
                col_add_all, col_discard = st.columns(2)
                with col_add_all:
                    if st.button("➕ Add All to Actions", key=f"add_extracted_actions_{_act_mkey}", type="primary", use_container_width=True):
                        for _p in _pending:
                            actions.append({
                                "uid": uuid.uuid4().hex,
                                "action": _p.get('action', ''),
                                "owner": _p.get('owner', 'Unassigned'),
                                "due_date": _p.get('due_date', ''),
                                "done": False
                            })
                        st.session_state[_actions_ss_key] = actions
                        st.session_state[_pending_key] = []
                        st.rerun()
                with col_discard:
                    if st.button("✖️ Discard", key=f"discard_extracted_actions_{_act_mkey}", use_container_width=True):
                        st.session_state[_pending_key] = []
                        st.rerun()

    # Display existing actions — editable in place; amend anything the AI got
    # wrong (or add manually below), then click Save Meeting to keep changes.
    if actions:
        st.write("**Current Actions** — edit or amend as needed, then **Save Meeting** below to keep changes:")
        _action_uid_to_delete = None
        for action in actions:
            _uid = action.get('uid') or uuid.uuid4().hex
            action['uid'] = _uid
            with st.container(border=True):
                col_a, col_b, col_c, col_d = st.columns([3, 2, 2, 1])
                with col_a:
                    action['action'] = st.text_input("Action", value=action.get('action', ''),
                                                      key=f"action_text_{_act_mkey}_{_uid}")
                with col_b:
                    action['owner'] = st.text_input("Owner", value=action.get('owner', 'Unassigned'),
                                                     key=f"action_owner_{_act_mkey}_{_uid}")
                with col_c:
                    _due_seed = None
                    if action.get('due_date'):
                        try:
                            _due_seed = datetime.date.fromisoformat(str(action['due_date']))
                        except Exception:
                            _due_seed = None
                    _new_due = st.date_input("Due date", value=_due_seed,
                                              key=f"action_due_{_act_mkey}_{_uid}")
                    action['due_date'] = str(_new_due) if _new_due else ""
                with col_d:
                    action['done'] = st.checkbox("Done", value=action.get('done', False),
                                                  key=f"action_done_{_act_mkey}_{_uid}")
                    if st.button("🗑️", key=f"delete_action_{_act_mkey}_{_uid}"):
                        _action_uid_to_delete = _uid
        if _action_uid_to_delete:
            st.session_state[_actions_ss_key] = [a for a in actions if a.get('uid') != _action_uid_to_delete]
            st.rerun()
        else:
            st.session_state[_actions_ss_key] = actions

    st.write("**Add New Action:**")
    col_a1, col_a2, col_a3, col_a4 = st.columns([3, 2, 2, 1])

    with col_a1:
        new_action = st.text_input("Action Description", key=f"new_action_{_act_mkey}", placeholder="What needs to be done?")

    with col_a2:
        new_owner = st.text_input("Assigned To", key=f"new_owner_{_act_mkey}", placeholder="Who will do it?")

    with col_a3:
        new_due = st.date_input("Due Date", key=f"new_due_{_act_mkey}", value=None)

    with col_a4:
        st.write("")  # Spacing
        st.write("")  # Spacing
        if st.button("➕ Add", key=f"add_action_btn_{_act_mkey}", use_container_width=True):
            if new_action.strip():
                actions.append({
                    "uid": uuid.uuid4().hex,
                    "action": new_action.strip(),
                    "owner": new_owner.strip() or "Unassigned",
                    "due_date": str(new_due) if new_due else "",
                    "done": False
                })
                st.session_state[_actions_ss_key] = actions
                st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    # MEETING ATTACHMENTS (General)
    # ══════════════════════════════════════════════════════════════════════════════

    st.subheader("📎 Meeting Attachments")

    with st.expander("📁 Attach Files to Meeting", expanded=False):

        # Kept in session_state, not just re-read from the saved record, so files
        # added here survive the rerun this section triggers — previously they
        # were silently lost on rerun before "Save Meeting" ever saw them.
        _mtg_key = st.session_state.current_staff_meeting_id or "new"
        _meeting_att_ss_key = f"meeting_attachments_{_mtg_key}"
        if _meeting_att_ss_key not in st.session_state:
            if selected_record and selected_record.get('meeting_attachments'):
                try:
                    _seed = json.loads(selected_record['meeting_attachments']) if isinstance(selected_record['meeting_attachments'], str) else selected_record['meeting_attachments']
                except Exception:
                    _seed = []
            else:
                _seed = []
            st.session_state[_meeting_att_ss_key] = _seed
        meeting_attachments = st.session_state[_meeting_att_ss_key]

        # Display existing attachments
        if meeting_attachments:
            st.write("**Attached Files:**")
            for idx, attachment in enumerate(meeting_attachments):
                col_m1, col_m2 = st.columns([4, 1])
                with col_m1:
                    _render_attachment_link(attachment, MEETING_ATTACHMENTS_BUCKET)
                with col_m2:
                    if st.button("🗑️", key=f"delete_meeting_attachment_{idx}"):
                        _delete_attachment(MEETING_ATTACHMENTS_BUCKET, attachment.get('path'))
                        meeting_attachments.pop(idx)
                        st.session_state[_meeting_att_ss_key] = meeting_attachments
                        st.rerun()

        # Add multiple attachments at once
        st.write("**Add Files:**")
        meeting_uploaded_files = st.file_uploader("Upload files (select multiple)",
                                                 type=['pdf', 'docx', 'pptx', 'txt', 'jpg', 'png', 'xlsx', 'csv', 'mp4', 'mov'],
                                                 accept_multiple_files=True,
                                                 key="meeting_file_upload")

        if meeting_uploaded_files:
            st.write(f"**{len(meeting_uploaded_files)} file(s) selected**")

            # Show selected files
            for f in meeting_uploaded_files:
                st.caption(f"📄 {f.name}")

            # Description for all files
            meeting_batch_desc = st.text_input("Description for all files (optional)",
                                              key="meeting_batch_desc",
                                              placeholder="E.g., Budget documents, Policy drafts")

            if st.button("➕ Add All Files", key="add_all_meeting_attachments", type="secondary"):
                added, failed = 0, []
                with st.spinner("Uploading file(s)…"):
                    for file in meeting_uploaded_files:
                        result = _upload_attachment(MEETING_ATTACHMENTS_BUCKET, f"meeting_{_mtg_key}", file)
                        if "path" in result:
                            meeting_attachments.append({
                                "name": file.name,
                                "description": meeting_batch_desc if meeting_batch_desc else "",
                                "filename": file.name,
                                "path": result["path"],
                                "size": file.size,
                                "type": file.type,
                                "uploaded_date": str(datetime.date.today())
                            })
                            added += 1
                        else:
                            failed.append((file.name, result.get("error", "unknown error")))
                st.session_state[_meeting_att_ss_key] = meeting_attachments
                for name, err in failed:
                    st.error(f"⚠️ Could not upload {name}: {err}")
                if added:
                    st.success(f"✅ Uploaded and added {added} file(s) to meeting!")
                    st.info("💡 Click 'Save Meeting' at the bottom to save these to the meeting record.")
                    st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    # 7. PROFESSIONAL DEVELOPMENT
    # ══════════════════════════════════════════════════════════════════════════════

    st.subheader("🎓 Professional Development Component")

    with st.expander("📚 PD Session Details", expanded=True):

        # PD Title
        default_pd_title = selected_record.get('pd_title', '') if selected_record else ''
        pd_title = st.text_input("PD Session Title", value=default_pd_title, key=f"pd_title_{_att_mkey}",
                                 placeholder="e.g. Sounds-Write Introduction, Berry Street Module 3, WHS Refresher…")

        st.write("**PD Attendance** (defaults to the meeting attendance above — click to change for this PD session)")

        # Pre-fill with meeting attendees/apologies but allow editing per-person
        default_pd_attendees = selected_record.get('pd_attendees', attendees) if selected_record else attendees
        default_pd_absent = selected_record.get('pd_absent', apologies) if selected_record else apologies
        pd_attendees, pd_absent = _render_roster_attendance(
            "PD", f"pd_att_{_att_mkey}", STAFF_ROSTER, default_pd_attendees, default_pd_absent
        )
    
        st.markdown("---")

        # PD Content Entry Method
        st.write("**PD Content Entry:**")

        # Kept in session_state (namespaced per meeting) so the recap text
        # survives switching between Manual Entry and AI from Transcript, and
        # so a freshly-generated AI recap actually shows up — once a widget
        # key exists, Streamlit ignores `value=` on rerun.
        _pd_notes_ss_key = f"pd_notes_state_{_att_mkey}"
        if _pd_notes_ss_key not in st.session_state:
            st.session_state[_pd_notes_ss_key] = selected_record.get('pd_notes', '') if selected_record else ''

        pd_method = st.radio("Choose entry method", options=["✍️ Manual Entry", "🤖 AI from Transcript"],
                           horizontal=True, key=f"pd_method_{_att_mkey}")

        _pd_notes_widget_key = f"pd_notes_manual_{_att_mkey}"

        if pd_method == "✍️ Manual Entry":
            pd_notes = st.text_area("PD Main Points / Notes", value=st.session_state[_pd_notes_ss_key],
                                   height=260, key=_pd_notes_widget_key,
                                   placeholder="Document key points from the PD session...")
            st.session_state[_pd_notes_ss_key] = pd_notes

        else:  # AI from Transcript
            st.caption(
                "If the PD part of this meeting is in a totally separate recording, paste or "
                "upload it below. If the main meeting transcript/synthesis above already covers "
                "the PD discussion too, tick the box instead — the AI will pick out just the PD "
                "part from it."
            )

            _reuse_main_transcript = st.checkbox(
                "Use the main meeting transcript/synthesis above for this PD section too",
                key=f"pd_reuse_main_transcript_{_att_mkey}"
            )

            pd_transcript_text = ""
            if _reuse_main_transcript:
                pd_transcript_text = (synthesis_for_minutes or transcript_text or "").strip()
                if not pd_transcript_text:
                    st.info("No main meeting transcript or synthesis has been entered above yet.")
            else:
                pd_pasted = st.text_area("Paste PD transcript or summary here", height=150,
                                         key=f"pd_transcript_paste_{_att_mkey}",
                                         placeholder="Paste the PD session transcript or summary…")
                if pd_pasted.strip():
                    pd_transcript_text = pd_pasted.strip()

                pd_transcript_file = st.file_uploader("Or upload a file (.txt or .docx)",
                                                     type=['txt', 'docx'],
                                                     key=f"pd_transcript_upload_{_att_mkey}")
                if pd_transcript_file and not pd_transcript_text:
                    if pd_transcript_file.name.endswith('.txt'):
                        pd_transcript_text = pd_transcript_file.read().decode('utf-8')
                    else:  # .docx
                        if DOCX_AVAILABLE:
                            try:
                                pd_doc = docx.Document(pd_transcript_file)
                                pd_transcript_text = '\n'.join([para.text for para in pd_doc.paragraphs])
                            except Exception as e:
                                st.error(f"Could not read .docx file: {e}")
                        else:
                            st.error("python-docx not installed — please paste the transcript instead.")

            if pd_transcript_text and GROQ_KEY:
                if st.button("🤖 Extract PD Recap with AI", type="secondary", key=f"extract_pd_ai_{_att_mkey}"):
                    with st.spinner("Processing PD content…"):
                        try:
                            from groq import Groq
                            client = Groq(api_key=GROQ_KEY)

                            pd_transcript_for_ai, was_truncated = _fit_to_groq_budget(
                                pd_transcript_text, max_tokens=600, prompt_overhead_tokens=300
                            )
                            if was_truncated:
                                st.warning(
                                    "⚠️ This is longer than the AI can process in one go (Groq's "
                                    "8,000 tokens/minute limit on the current plan). Only the "
                                    "first part was sent — review the recap and add anything "
                                    "missed by hand."
                                )

                            prompt = f"""The text below is from a school staff meeting and may contain
BOTH general staff meeting business AND a separate Professional
Development (PD) session. Find the part that is about the PD session and
IGNORE anything that's general staff meeting business (standing items,
additional agenda items, etc. — that's documented separately).

Write a BRIEF recap of the PD session only: 3-5 sentences of plain,
flowing prose covering what the session focused on and the main
takeaway(s) — no headings, no bullet points, just a short recap someone
could read in 15 seconds.

Do not invent anything that isn't in the text. If you can't find any PD
content at all, reply with exactly: NO_PD_CONTENT_FOUND

TEXT:
{pd_transcript_for_ai}"""

                            response = client.chat.completions.create(
                                model="openai/gpt-oss-120b",
                                messages=[{"role": "user", "content": prompt}],
                                temperature=0.3,
                                max_tokens=600
                            )
                            extracted_pd = response.choices[0].message.content.strip()

                            if extracted_pd == "NO_PD_CONTENT_FOUND":
                                st.warning(
                                    "Couldn't find any PD-specific content in that text — try "
                                    "pasting just the PD part, or write the recap manually below."
                                )
                            else:
                                st.session_state[_pd_notes_ss_key] = extracted_pd
                                # Widget key may already exist once rendered, so setting it here
                                # too is what actually updates the box below.
                                st.session_state[_pd_notes_widget_key] = extracted_pd
                                st.success("✅ PD recap generated — review/edit it below before saving.")

                        except Exception as e:
                            st.error(f"AI extraction failed: {e}")

            elif pd_transcript_text and not GROQ_KEY:
                st.warning("⚠️ GROQ_API_KEY not configured.")

            pd_notes = st.text_area("PD Notes / Recap", value=st.session_state[_pd_notes_ss_key],
                                    height=180, key=_pd_notes_widget_key,
                                    placeholder="A brief recap of the PD session will appear here "
                                                "after extraction — or type it directly.")
            st.session_state[_pd_notes_ss_key] = pd_notes

        st.markdown("---")
    
        # PD Attachments
        st.write("**PD Attachments / Resources:**")

        # Kept in session_state, not just re-read from the saved record, so files
        # added here survive the rerun this section triggers — previously they
        # were silently lost on rerun before "Save Meeting" ever saw them.
        _pd_att_ss_key = f"pd_attachments_{_mtg_key}"
        if _pd_att_ss_key not in st.session_state:
            if selected_record and selected_record.get('pd_attachments'):
                try:
                    _pd_seed = json.loads(selected_record['pd_attachments']) if isinstance(selected_record['pd_attachments'], str) else selected_record['pd_attachments']
                except Exception:
                    _pd_seed = []
            else:
                _pd_seed = []
            st.session_state[_pd_att_ss_key] = _pd_seed
        pd_attachments = st.session_state[_pd_att_ss_key]

        # Display existing attachments
        if pd_attachments:
            st.write("**Uploaded Attachments:**")
            for idx, attachment in enumerate(pd_attachments):
                col_att1, col_att2 = st.columns([4, 1])
                with col_att1:
                    _render_attachment_link(attachment, PD_ATTACHMENTS_BUCKET)
                with col_att2:
                    if st.button("🗑️", key=f"delete_pd_attachment_{idx}"):
                        _delete_attachment(PD_ATTACHMENTS_BUCKET, attachment.get('path'))
                        pd_attachments.pop(idx)
                        st.session_state[_pd_att_ss_key] = pd_attachments
                        st.rerun()

        # Add multiple attachments at once
        st.write("**Add New Attachments:**")
        uploaded_files = st.file_uploader("Upload files (select multiple) — any file type accepted",
                                         accept_multiple_files=True,
                                         key="pd_file_upload")

        if uploaded_files:
            st.write(f"**{len(uploaded_files)} file(s) selected**")

            # Show selected files
            for f in uploaded_files:
                st.caption(f"📄 {f.name}")

            # Description for all files (optional)
            batch_description = st.text_input("Description for all files (optional)",
                                             key="pd_batch_desc",
                                             placeholder="E.g., Restorative Practices Resources")

            if st.button("➕ Add All Files", key="add_all_pd_attachments", type="secondary"):
                added, failed = 0, []
                with st.spinner("Uploading file(s)…"):
                    for file in uploaded_files:
                        result = _upload_attachment(PD_ATTACHMENTS_BUCKET, f"pd_{_mtg_key}", file)
                        if "path" in result:
                            pd_attachments.append({
                                "name": file.name,
                                "description": batch_description if batch_description else "",
                                "filename": file.name,
                                "path": result["path"],
                                "size": file.size,
                                "type": file.type,
                                "uploaded_date": str(datetime.date.today())
                            })
                            added += 1
                        else:
                            failed.append((file.name, result.get("error", "unknown error")))
                st.session_state[_pd_att_ss_key] = pd_attachments
                for name, err in failed:
                    st.error(f"⚠️ Could not upload {name}: {err}")
                if added:
                    st.success(f"✅ Uploaded and added {added} file(s) to PD!")
                    st.info("💡 Click 'Save Meeting' at the bottom to save these to the meeting record.")
                    st.rerun()

    st.markdown("---")

    # ══════════════════════════════════════════════════════════════════════════════
    # DOWNLOAD + SAVE
    # ══════════════════════════════════════════════════════════════════════════════

    meeting_data = {
        "meeting_date": str(meeting_date),
        "term": term.strip(),
        "week_number": int(week_number),
        "minute_taker": minute_taker.strip(),
        "attendees": attendees.strip(),
        "apologies": apologies.strip(),
        "acknowledgement_done": acknowledgement_done,
        "acknowledgement_by": acknowledgement_by.strip(),
        "icebreaker": _build_bsem_field(
            "different" if bsem_choice == "Different activity" else "suggested",
            bsem_name.strip(), bsem_explanation.strip(), icebreaker_notes.strip()
        ),
        "agenda_items": json.dumps(agenda_data),
        "minutes": minutes.strip() if minutes else '',
        "actions": json.dumps(actions) if actions else '[]',
        "meeting_attachments": json.dumps(meeting_attachments) if meeting_attachments else '[]',
        "pd_attendees": pd_attendees.strip(),
        "pd_absent": pd_absent.strip(),
        "pd_notes": pd_notes.strip() if pd_notes else '',
        "pd_title": pd_title.strip() if pd_title else '',
        "pd_attachments": json.dumps(pd_attachments) if pd_attachments else '[]'
    }

    col_dl, col_save = st.columns([1, 2])
    with col_dl:
        if DOCX_AVAILABLE and meeting_data["minutes"].strip():
            st.download_button(
                "📥 Download Minutes (.docx)",
                data=_build_minutes_docx_bytes(meeting_data),
                file_name=f"Staff_Meeting_Minutes_{meeting_data['meeting_date']}.docx",
                mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                use_container_width=True,
                key="download_current_minutes"
            )
        else:
            st.button("📥 Download Minutes (.docx)", disabled=True, use_container_width=True,
                      help="Add some minutes content first" if DOCX_AVAILABLE else "python-docx not installed")

    with col_save:
        if st.button("💾 Save Meeting", type="primary", use_container_width=True, key="save_meeting"):
            try:
                if st.session_state.current_staff_meeting_id:
                    # Update existing
                    result = supabase.table('staff_meetings').update(meeting_data).eq('id', st.session_state.current_staff_meeting_id).execute()
                    st.success("✅ **Meeting Saved Successfully!**")
                    st.info("📄 Minutes, agenda, and actions have been saved. The Minutes section will collapse on next page load.")
                    time.sleep(2)
                    st.rerun()
                else:
                    # Create new
                    result = supabase.table('staff_meetings').insert(meeting_data).execute()
                    if result.data:
                        st.session_state.current_staff_meeting_id = result.data[0]['id']
                        st.success("✅ **New Meeting Created & Saved!**")
                        st.info("📄 All meeting details saved successfully.")
                        time.sleep(2)
                        st.rerun()

            except Exception as e:
                st.error(f"⚠️ Could not save meeting: {e}")

with tab3:
    st.subheader("⚙️ Manage Staff List")
    st.caption(
        f"Attendance dropdowns are currently loaded from: **{STAFF_ROSTER_SOURCE}** "
        f"({len(STAFF_ROSTER)} names). Add or remove staff below — changes apply "
        "immediately, no redeploy needed."
    )

    if not _staff_roster_table_exists:
        st.warning(
            "The staff list database table hasn't been set up yet, so names can't be "
            "added or removed here — attendance is falling back to the STAFF_NAMES "
            "secret or the built-in default list instead. Run this once in the "
            "**MEETINGS** Supabase project's SQL editor, then reload this page:"
        )
        st.code(STAFF_ROSTER_TABLE_SQL, language="sql")
    else:
        if _staff_roster_rows:
            st.write("**Current staff:**")
            for _row in _staff_roster_rows:
                col_staff_name, col_staff_del = st.columns([4, 1])
                with col_staff_name:
                    st.write(_row['name'])
                with col_staff_del:
                    if st.button("🗑️ Remove", key=f"del_staff_{_row['id']}", use_container_width=True):
                        _ok, _err = _delete_staff_member(_row['id'])
                        if _ok:
                            st.rerun()
                        else:
                            st.error(f"Could not remove: {_err}")
        else:
            st.info(
                "No staff added yet. Add names one at a time below, or seed the list "
                "from the built-in defaults to get started quickly."
            )
            if st.button("➕ Seed with built-in default staff list"):
                _seeded = 0
                for _name in DEFAULT_STAFF_ROSTER:
                    _ok, _ = _add_staff_member(_name)
                    if _ok:
                        _seeded += 1
                st.success(f"Added {_seeded} staff member(s).")
                st.rerun()

        st.markdown("---")
        st.write("**Add a staff member:**")
        col_new_staff, col_add_staff = st.columns([3, 1])
        with col_new_staff:
            _new_staff_name = st.text_input(
                "Name", key="new_staff_name", label_visibility="collapsed",
                placeholder="Full name as it should appear in attendance"
            )
        with col_add_staff:
            if st.button("➕ Add", key="add_staff_btn", use_container_width=True):
                _ok, _err = _add_staff_member(_new_staff_name)
                if _ok:
                    st.success(f"Added {_new_staff_name.strip()}.")
                    st.rerun()
                else:
                    st.error(f"Could not add: {_err}")

st.markdown("---")
st.caption("🏫 Cowandilla Learning Centre · LBU · STAFF Meetings")
