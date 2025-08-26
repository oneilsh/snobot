import streamlit as st
from typing import Any, List
import pandas as pd
import re
from ui.utils import OMOP_DOMAINS, DOMAIN_COLORS
from models import FullCodedConcept

def render_annotated_component_from_concepts(
    text: str,
    coded_concepts: List[FullCodedConcept],
    scroll: bool = True,
    max_height_px: int = 520,
    tooltip_room_px: int = 50,  # extra space after the text so bottom tooltips aren't cut off
):
    """Single-pane annotated text with CSS-only hover tooltips for FullCodedConcept objects.
    Searches for mention_str in the text and highlights them with concept information.
    """
    if not coded_concepts:
        # If no concepts, just render plain text
        st.html(f'<div style="white-space: pre-wrap; padding: 16px; border: 1px solid #e7e7e7; border-radius: 10px; background: #fafafa;">{_esc(text)}</div>')
        return
    
    # Find all mentions in the text and create spans
    spans = []
    for concept in coded_concepts:
        mention = concept.mention_str
        # Find all occurrences of this mention (case-insensitive)
        for match in re.finditer(re.escape(mention), text, re.IGNORECASE):
            spans.append({
                "start": match.start(),
                "end": match.end(),
                "concept": concept
            })
    
    # Sort spans by start position
    spans.sort(key=lambda x: x["start"])
    
    # Create segments with potential overlaps
    cuts = sorted({0, len(text), *[s["start"] for s in spans], *[s["end"] for s in spans]})
    segs = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if a == b:
            continue
        # Find all concepts that cover this segment
        cover = [s["concept"] for s in spans if s["start"] < b and s["end"] > a]
        segs.append({"a": a, "b": b, "cover": cover})

    # Build HTML for the text with highlighted segments
    parts = []
    for seg in segs:
        a, b, cover = seg["a"], seg["b"], seg["cover"]
        seg_txt = _esc(text[a:b])

        if not cover:
            parts.append(seg_txt)
            continue

        # Background as stacked gradients for overlaps
        layers = []
        for concept in cover:
            domain = concept.domain_id if hasattr(concept, 'domain_id') else "Other"
            hexcol = DOMAIN_COLORS.get(domain, "#EEEEEE").lstrip("#")
            rr, gg, bb = int(hexcol[0:2], 16), int(hexcol[2:4], 16), int(hexcol[4:6], 16)
            layers.append(f"linear-gradient(rgba({rr},{gg},{bb},0.45), rgba({rr},{gg},{bb},0.45))")
        bg = ", ".join(layers) if layers else "none"

        # Tooltip contents - plain text since CSS content doesn't support HTML
        tip = " | ".join(
            f"{concept.concept_name} ({concept.concept_id}/{concept.domain_id})"
            for concept in cover
        )

        parts.append(
            f'<span class="seg" data-tip="{_esc(tip)}" style="background-image:{bg}">{seg_txt}</span>'
        )

    textbox_html = "".join(parts)
    _render_html_with_styles(textbox_html, scroll, max_height_px, tooltip_room_px)

def _esc(s: Any) -> str:
    """HTML escape helper function."""
    s = "" if s is None else str(s)
    return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

def _render_html_with_styles(textbox_html: str, scroll: bool, max_height_px: int, tooltip_room_px: int):
    """Render the HTML with CSS styles."""
    pane_h = f"{max_height_px}px" if scroll else "auto"
    pane_overflow = "auto" if scroll else "visible"
    
    # Get current theme from Streamlit context
    try:
        theme_type = st.context.theme.get('type', 'light')
        is_dark = theme_type == 'dark'
    except:
        # Fallback if context not available
        is_dark = False
    
    # Set theme-specific colors
    if is_dark:
        bg_color = "#0e1117"
        border_color = "#2b2b2b"
        hover_color = "#ccc"
        tooltip_bg = "#fafafa"
        tooltip_text = "#111"
    else:
        bg_color = "#fafafa"
        border_color = "#e7e7e7"
        hover_color = "#999"
        tooltip_bg = "#111"
        tooltip_text = "#fff"

    html = f"""
<div class="annotated">
  <div class="textbox">{textbox_html}</div>
</div>

<style>
  :root {{
    --pane-h: {pane_h};
    --pane-overflow: {pane_overflow};
    --tooltip-room: {tooltip_room_px}px; /* space after text to allow bottom tooltips */
  }}
  
  /* Theme-specific colors injected from Python */
  .annotated {{
    --background-color: {bg_color};
    --border-color: {border_color};
    --hover-color: {hover_color};
    --tooltip-bg: {tooltip_bg};
    --tooltip-text: {tooltip_text};
  }}

  .annotated {{
    border: 1px solid var(--border-color, #e7e7e7); border-radius: 10px;
    padding: 16px; background: var(--background-color, #fafafa);
    max-height: var(--pane-h);
    overflow: var(--pane-overflow);
  }}
  .textbox {{
    white-space: pre-wrap; line-height: 1.7; font-size: 1rem;
    /* Add bottom spacer so you can scroll past the last line */
    position: relative;
  }}
  .textbox::after {{
    content: ""; display: block; height: var(--tooltip-room);
  }}

  .seg {{
    position: relative; /* tooltip anchor */
    padding: 0 2px; border-radius: 4px;
    box-shadow: inset 0 -1px 0 rgba(0,0,0,.06);
    cursor: default; text-decoration: none; color: inherit;
  }}
  .seg:hover {{ outline: 1px dashed var(--hover-color, #999); }}

  /* Tooltip BELOW the span */
  .seg::after {{
    content: attr(data-tip);
    position: absolute;
    left: 0; top: calc(100% + 6px);
    background: var(--tooltip-bg, #111); color: var(--tooltip-text, #fff);
    padding: 8px 12px; border-radius: 8px; font-size: 13px;
    white-space: normal; overflow-wrap: anywhere;
    line-height: 1.4; min-width: 200px; max-width: 500px;
    opacity: 0; pointer-events: none; transform: translateY(-4px);
    box-shadow: 0 8px 24px rgba(0,0,0,0.2), 0 2px 8px rgba(0,0,0,0.1);
    transition: opacity .15s ease, transform .15s ease;
    z-index: 10;
    font-weight: 500;
    letter-spacing: 0.3px;
  }}
  .seg:hover::after {{ opacity: 0.98; transform: translateY(0); }}

  .seg::before {{
    content: ""; position: absolute; left: 8px; top: 100%;
    border: 6px solid transparent; border-top-color: var(--tooltip-bg, #111);
    opacity: 0; transform: translateY(-4px);
    transition: opacity .12s ease, transform .12s ease;
    z-index: 9;
  }}
  .seg:hover::before {{ opacity: 0.98; transform: translateY(0); }}
</style>
"""
    st.html(html)

def render_annotated_component_from_df_css(
    text: str,
    df_rows: pd.DataFrame,
    scroll: bool = True,
    max_height_px: int = 520,
    tooltip_room_px: int = 50,  # extra space after the text so bottom tooltips aren't cut off
):
    """Single-pane annotated text with CSS-only hover tooltips.
    Adds a bottom spacer so tooltips near the end remain visible inside the scroll box.
    df_rows is a pandas dataframe with columns:
    """
    rows = [] if df_rows is None or df_rows.empty else df_rows.to_dict(orient="records")

    # Segment the text so overlapping spans render correctly
    cuts = sorted({0, len(text), *[r.get("start", 0) for r in rows], *[r.get("end", 0) for r in rows]})
    segs = []
    for a, b in zip(cuts[:-1], cuts[1:]):
        if a == b:
            continue
        cover = [r for r in rows if r.get("start", 0) < b and r.get("end", 0) > a]
        segs.append({"a": a, "b": b, "cover": cover})



    # Build HTML for the text with highlighted segments
    parts = []
    for seg in segs:
        a, b, cover = seg["a"], seg["b"], seg["cover"]
        seg_txt = _esc(text[a:b])

        if not cover:
            parts.append(seg_txt)
            continue

        # Background as stacked gradients for overlaps
        layers = []
        for r in cover:
            dom = r.get("domain", "Other")
            hexcol = DOMAIN_COLORS.get(dom, "#EEEEEE").lstrip("#")
            rr, gg, bb = int(hexcol[0:2], 16), int(hexcol[2:4], 16), int(hexcol[4:6], 16)
            layers.append(f"linear-gradient(rgba({rr},{gg},{bb},0.45), rgba({rr},{gg},{bb},0.45))")
        bg = ", ".join(layers) if layers else "none"

        # Tooltip contents
        tip = _esc(" | ".join(
            f"{r.get('domain','Other')} • {r.get('canonical_label','')} • {r.get('id','')}"
            for r in cover
        ))

        parts.append(
            f'<span class="seg" data-tip="{tip}" style="background-image:{bg}">{seg_txt}</span>'
        )

    textbox_html = "".join(parts)
    _render_html_with_styles(textbox_html, scroll, max_height_px, tooltip_room_px)
