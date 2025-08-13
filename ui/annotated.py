import streamlit as st
from typing import Any
import pandas as pd
from ui.utils import OMOP_DOMAINS, DOMAIN_COLORS

def render_annotated_component_from_df_css(
    text: str,
    df_rows: pd.DataFrame,
    scroll: bool = True,
    max_height_px: int = 520,
    tooltip_room_px: int = 50,  # extra space after the text so bottom tooltips aren't cut off
):
    """Single-pane annotated text with CSS-only hover tooltips.
    Adds a bottom spacer so tooltips near the end remain visible inside the scroll box.
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

    def esc(s: Any) -> str:
        s = "" if s is None else str(s)
        return s.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    # Build HTML for the text with highlighted segments
    parts = []
    for seg in segs:
        a, b, cover = seg["a"], seg["b"], seg["cover"]
        seg_txt = esc(text[a:b])

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
        tip = esc(" | ".join(
            f"{r.get('domain','Other')} • {r.get('canonical_label','')} • {r.get('id','')}"
            for r in cover
        ))

        parts.append(
            f'<span class="seg" data-tip="{tip}" style="background-image:{bg}">{seg_txt}</span>'
        )

    textbox_html = "".join(parts)

    pane_h = f"{max_height_px}px" if scroll else "auto"
    pane_overflow = "auto" if scroll else "visible"

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

  .annotated {{
    border: 1px solid #e7e7e7; border-radius: 10px;
    padding: 16px; background: #fafafa;
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
  .seg:hover {{ outline: 1px dashed #999; }}

  /* Tooltip BELOW the span */
  .seg::after {{
    content: attr(data-tip);
    position: absolute;
    left: 0; top: calc(100% + 6px);
    background: #111; color: #fff;
    padding: 6px 8px; border-radius: 6px; font-size: 12px;
    white-space: normal; overflow-wrap: anywhere;
    line-height: 1.3; min-width: 120px; max-width: 420px;
    opacity: 0; pointer-events: none; transform: translateY(-4px);
    box-shadow: 0 6px 18px rgba(0,0,0,0.18);
    transition: opacity .12s ease, transform .12s ease;
    z-index: 10;
  }}
  .seg:hover::after {{ opacity: 0.98; transform: translateY(0); }}

  .seg::before {{
    content: ""; position: absolute; left: 8px; top: 100%;
    border: 6px solid transparent; border-top-color: #111;
    opacity: 0; transform: translateY(-4px);
    transition: opacity .12s ease, transform .12s ease;
    z-index: 9;
  }}
  .seg:hover::before {{ opacity: 0.98; transform: translateY(0); }}
</style>
"""
    st.html(html)
