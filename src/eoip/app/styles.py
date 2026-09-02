"""Shared CSS styling for the EOIP Streamlit application."""

from __future__ import annotations

import streamlit as st

from eoip.app.theme import css_theme_variables

EOIP_CSS = f"<style>{css_theme_variables()}</style>" + """
<style>
html,
body,
[class*="css"] {
    font-family: var(--eoip-font-family);
    font-size: var(--eoip-font-size-body);
    line-height: var(--eoip-line-height-normal);
}

.stApp {
    background:
        linear-gradient(
            180deg,
            var(--eoip-surface) 0%,
            var(--eoip-bg) 100%
        );
    color: var(--eoip-text);
}

/* Keep the toolbar shell because it owns the collapsed-sidebar expand control. */
[data-testid="stHeader"],
[data-testid="stToolbar"] {
    background: transparent;
}

[data-testid="stAppDeployButton"],
[data-testid="stMainMenu"],
[data-testid="stStatusWidget"],
[data-testid="stToolbarActions"],
[data-testid="stDecoration"] {
    display: none;
}

[data-testid="stSidebarCollapseButton"],
[data-testid="stExpandSidebarButton"] {
    visibility: visible;
    pointer-events: auto;
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            var(--eoip-surface-soft) 0%,
            var(--eoip-border-subtle) 100%
        );
    border-right:
        1px solid var(--eoip-border);
}

[data-testid="stSidebar"] > div:first-child {
    padding-top: 1.4rem;
}

[data-testid="stSidebar"] h2 {
    color: var(--eoip-text);
    letter-spacing: -0.02em;
}

[data-testid="stSidebar"] [data-testid="stCaptionContainer"] {
    color: var(--eoip-muted);
}

.block-container {
    max-width: 1500px;
    width: 100%;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}

h1 {
    color: var(--eoip-text);
    font-weight: var(--eoip-font-weight-bold);
    letter-spacing: -0.03em;
}

h2,
h3 {
    color: var(--eoip-text);
    font-weight: var(--eoip-font-weight-semibold);
    letter-spacing: -0.02em;
}

[data-testid="stCaptionContainer"] {
    color: var(--eoip-muted);
    font-size: var(--eoip-font-size-caption);
    font-weight: var(--eoip-font-weight-regular);
    line-height: var(--eoip-line-height-normal);
}

[data-testid="stMarkdownContainer"] p {
    font-size: var(--eoip-font-size-body);
    font-weight: var(--eoip-font-weight-regular);
    line-height: var(--eoip-line-height-relaxed);
}

[data-testid="stWidgetLabel"] p,
[data-testid="stDateInput"] label p,
[data-testid="stSelectbox"] label p {
    color: var(--eoip-text-secondary);
    font-size: var(--eoip-font-size-label);
    font-weight: var(--eoip-font-weight-medium);
    line-height: var(--eoip-line-height-normal);
}

.eoip-kpi-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(min(100%, 13rem), 1fr));
    gap: 0.65rem;
    width: 100%;
}

.eoip-kpi-card {
    display: flex;
    flex-direction: column;
    min-width: 0;
    min-height: 142px;
    padding: 1.1rem 1.2rem;
    background: var(--eoip-surface);
    border: 1px solid var(--eoip-border-subtle);
    border-radius: 11px;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}

.eoip-kpi-card-compact {
    min-height: 116px;
    padding: 0.9rem 1rem;
}

.eoip-kpi-header {
    display: flex;
    align-items: center;
    min-width: 0;
    gap: 0.42rem;
}

.eoip-kpi-icon,
.eoip-kpi-help,
.eoip-kpi-delta-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex: 0 0 auto;
}

.eoip-kpi-icon {
    color: var(--eoip-primary);
}

.eoip-kpi-label {
    min-width: 0;
    color: var(--eoip-text-secondary);
    font-size: var(--eoip-font-size-label);
    font-weight: var(--eoip-font-weight-semibold);
    line-height: var(--eoip-line-height-normal);
}

.eoip-kpi-help {
    margin-left: auto;
    color: var(--eoip-muted);
    cursor: help;
}

.eoip-kpi-value {
    margin-top: 0.72rem;
    color: var(--eoip-text);
    font-size: clamp(1.55rem, 2.1vw, var(--eoip-font-size-kpi-value));
    font-weight: var(--eoip-font-weight-bold);
    font-variant-numeric: tabular-nums;
    letter-spacing: -0.025em;
    line-height: var(--eoip-line-height-tight);
    overflow-wrap: anywhere;
}

.eoip-kpi-delta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: 0.24rem;
    margin-top: 0.55rem;
    color: var(--eoip-muted);
    font-size: var(--eoip-font-size-caption);
    font-weight: var(--eoip-font-weight-semibold);
    line-height: var(--eoip-line-height-normal);
}

.eoip-kpi-delta-positive {
    color: var(--eoip-success);
}

.eoip-kpi-delta-negative {
    color: var(--eoip-danger);
}

.eoip-kpi-delta-warning {
    color: var(--eoip-warning);
}

.eoip-kpi-delta-neutral {
    color: var(--eoip-muted);
}

.eoip-kpi-context,
.eoip-kpi-subtitle {
    color: var(--eoip-muted);
    font-weight: var(--eoip-font-weight-medium);
}

.eoip-kpi-context {
    margin-left: 0.16rem;
}

.eoip-kpi-subtitle,
.eoip-kpi-status {
    margin-top: auto;
    padding-top: 0.55rem;
    font-size: var(--eoip-font-size-caption);
    line-height: var(--eoip-line-height-normal);
}

.eoip-kpi-status {
    display: flex;
    align-items: center;
    gap: 0.3rem;
    color: var(--eoip-text-secondary);
}

[data-testid="stAlert"] {
    border-radius: 12px;
    border-width: 1px;
}

[data-testid="stDataFrame"] {
    background: var(--eoip-surface);
    border: 1px solid var(--eoip-border);
    border-radius: 12px;
    overflow: auto;
    max-width: 100%;
    font-size: var(--eoip-font-size-label);
    font-variant-numeric: tabular-nums;
    overscroll-behavior-inline: contain;
}

[data-testid="stPlotlyChart"] {
    background: var(--eoip-surface);
    border: 1px solid var(--eoip-border);
    border-radius: 14px;
    padding: 0.6rem;
    box-shadow:
        0 2px 8px rgba(15, 23, 42, 0.04);
    width: 100%;
    min-width: 0;
}

div[data-baseweb="select"] > div {
    border-radius: 10px;
}

.stButton > button {
    border-radius: 10px;
    border: 1px solid var(--eoip-border);
    font-size: var(--eoip-font-size-label);
    font-weight: var(--eoip-font-weight-semibold);
    transition:
        transform 0.15s ease,
        box-shadow 0.15s ease;
}

.stButton > button:hover {
    transform: translateY(-1px);
    box-shadow:
        0 5px 14px rgba(15, 23, 42, 0.10);
}

.stDownloadButton > button {
    border-radius: 10px;
    font-size: var(--eoip-font-size-label);
    font-weight: var(--eoip-font-weight-semibold);
}

hr {
    border-color: var(--eoip-border);
}

.eoip-card {
    background: var(--eoip-surface);
    border: 1px solid var(--eoip-border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow:
        0 2px 8px rgba(15, 23, 42, 0.04);
}

.eoip-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    line-height: 1;
}

.eoip-icon svg {
    display: block;
}

.eoip-icon-accent,
.eoip-page-icon {
    color: var(--eoip-primary-dark);
}

.eoip-icon-muted {
    color: var(--eoip-muted);
}

.eoip-icon-success {
    color: var(--eoip-success);
}

.eoip-icon-warning {
    color: var(--eoip-warning);
}

.eoip-icon-danger {
    color: var(--eoip-danger);
}

.eoip-brand,
.eoip-title-row,
.eoip-section-title,
.eoip-status {
    display: flex;
    align-items: center;
}

.eoip-brand {
    gap: 0.5rem;
    margin-bottom: var(--eoip-space-1);
    color: var(--eoip-text);
    font-size: 1.5rem;
    font-weight: var(--eoip-font-weight-bold);
    letter-spacing: -0.02em;
}

.eoip-title-row {
    gap: 0.5rem;
}

.eoip-title-row h1 {
    margin: 0;
    padding: 0;
    color: var(--eoip-text);
    font-size: var(--eoip-font-size-page-title);
    font-weight: var(--eoip-font-weight-bold);
    line-height: var(--eoip-line-height-tight);
    letter-spacing: -0.025em;
}

.eoip-page-header {
    margin-bottom: var(--eoip-space-2);
}

.eoip-page-subtitle {
    max-width: 72ch;
    margin: var(--eoip-space-1) 0 0;
    color: var(--eoip-text-secondary);
    font-size: var(--eoip-font-size-body);
    font-weight: var(--eoip-font-weight-regular);
    line-height: var(--eoip-line-height-normal);
}

.eoip-section-header {
    margin: var(--eoip-space-6) 0 var(--eoip-space-3);
}

.eoip-section-heading {
    margin: 0;
    color: var(--eoip-text);
    font-size: var(--eoip-font-size-section-title);
    font-weight: var(--eoip-font-weight-semibold);
    line-height: 1.25;
    letter-spacing: -0.012em;
}

.eoip-section-description {
    max-width: 76ch;
    margin: var(--eoip-space-1) 0 0;
    color: var(--eoip-text-secondary);
    font-size: var(--eoip-font-size-body);
    font-weight: var(--eoip-font-weight-regular);
    line-height: var(--eoip-line-height-normal);
}

.eoip-card-title,
.eoip-filter-heading {
    color: var(--eoip-text);
    font-size: var(--eoip-font-size-card-title);
    font-weight: var(--eoip-font-weight-semibold);
    line-height: var(--eoip-line-height-normal);
}

.eoip-card-title {
    margin-bottom: var(--eoip-space-2);
}

.eoip-filter-heading {
    margin-bottom: var(--eoip-space-2);
}

.eoip-page-context {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--eoip-space-2) var(--eoip-space-4);
    margin: 0 0 var(--eoip-space-3);
    color: var(--eoip-text-secondary);
    font-size: var(--eoip-font-size-caption);
    line-height: var(--eoip-line-height-normal);
}

.eoip-context-item {
    display: flex;
    align-items: baseline;
    gap: var(--eoip-space-1);
    min-width: 0;
    overflow: hidden;
}

[data-testid="stPlotlyChart"] .modebar {
    max-width: 100%;
}

.eoip-context-item:not(:last-child)::after {
    margin-left: var(--eoip-space-2);
    color: var(--eoip-border);
    content: "|";
}

.eoip-context-item dt {
    color: var(--eoip-muted);
    font-weight: var(--eoip-font-weight-medium);
}

.eoip-context-item dd {
    margin: 0;
    color: var(--eoip-text-secondary);
    font-weight: var(--eoip-font-weight-semibold);
}

.eoip-section-title {
    gap: 0.45rem;
}

.eoip-status {
    gap: 0.35rem;
}

.st-key-eoip_navigation [data-testid="stVerticalBlock"] {
    gap: 3px;
}

.eoip-nav-group-label {
    margin: var(--eoip-space-3) var(--eoip-space-3) var(--eoip-space-1);
    color: var(--eoip-muted);
    font-size: 0.6875rem;
    font-weight: var(--eoip-font-weight-semibold);
    line-height: var(--eoip-line-height-tight);
    letter-spacing: 0.08em;
    text-transform: uppercase;
    white-space: nowrap;
}

.st-key-eoip_navigation .element-container:first-child .eoip-nav-group-label {
    margin-top: var(--eoip-space-1);
}

div[class*="st-key-eoip_nav_"] .stButton {
    margin: 0;
}

div[class*="st-key-eoip_nav_"] button {
    justify-content: flex-start;
    min-height: 40px;
    padding: 0.5rem 0.7rem;
    gap: 0.55rem;
    border: 0;
    border-left: 3px solid transparent;
    border-radius: 8px;
    background: transparent;
    color: var(--eoip-muted);
    font-size: var(--eoip-font-size-body);
    font-weight: var(--eoip-font-weight-medium);
    line-height: var(--eoip-line-height-tight);
    box-shadow: none;
    transition:
        background-color 120ms ease,
        color 120ms ease,
        border-color 120ms ease;
}

div[class*="st-key-eoip_nav_"] button::before {
    width: 19px;
    height: 19px;
    flex: 0 0 19px;
    content: "";
    background-color: currentColor;
    -webkit-mask-position: center;
    mask-position: center;
    -webkit-mask-repeat: no-repeat;
    mask-repeat: no-repeat;
    -webkit-mask-size: contain;
    mask-size: contain;
}

div[class*="st-key-eoip_nav_"] button:hover {
    transform: none;
    background: var(--eoip-primary-soft);
    color: var(--eoip-primary-dark);
    box-shadow: none;
}

div[class*="st-key-eoip_nav_"] button:focus-visible {
    outline: 2px solid var(--eoip-primary-dark);
    outline-offset: 1px;
    box-shadow: none;
}

div[class*="st-key-eoip_nav_"] button p {
    margin: 0;
    color: inherit;
    font-size: inherit;
    font-weight: inherit;
    line-height: inherit;
    white-space: nowrap;
}

.eoip-eyebrow {
    color: var(--eoip-primary-dark);
    font-size: var(--eoip-font-size-caption);
    font-weight: var(--eoip-font-weight-semibold);
    letter-spacing: 0.08em;
    text-transform: uppercase;
}

.eoip-muted {
    color: var(--eoip-muted);
}

.eoip-section {
    margin-top: 0.7rem;
    margin-bottom: 0.9rem;
}

@media (max-width: 1200px) {
    .block-container {
        padding-top: 1.75rem;
        padding-right: 1.5rem;
        padding-left: 1.5rem;
    }

    .eoip-kpi-grid {
        grid-template-columns: repeat(auto-fit, minmax(min(100%, 11.5rem), 1fr));
    }

    .eoip-kpi-card {
        padding: 1rem;
    }
}

@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    h1 {
        font-size: clamp(1.625rem, 6vw, var(--eoip-font-size-page-title));
        line-height: var(--eoip-line-height-tight);
    }

    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="column"] {
        min-width: min(100%, 18rem);
        flex: 1 1 18rem;
    }

    [data-testid="stPlotlyChart"] {
        padding: 0.4rem;
    }

    .eoip-section-header {
        margin-top: var(--eoip-space-4);
    }

    .eoip-kpi-grid {
        grid-template-columns: repeat(2, minmax(0, 1fr));
    }

}

@media (max-width: 600px) {
    .block-container {
        padding-top: 1.25rem;
        padding-left: 0.75rem;
        padding-right: 0.75rem;
    }

    [data-testid="stSidebar"] > div:first-child {
        padding-top: 0.8rem;
    }

    .eoip-kpi-grid {
        grid-template-columns: 1fr;
    }

    .eoip-title-row {
        align-items: flex-start;
    }

    .eoip-title-row h1 {
        overflow-wrap: anywhere;
    }

    .eoip-kpi-card,
    .eoip-card,
    [data-testid="stDataFrame"],
    [data-testid="stPlotlyChart"] {
        border-radius: 9px;
    }

    [data-testid="stHorizontalBlock"] .stButton,
    [data-testid="stHorizontalBlock"] .stDownloadButton {
        flex: 1 1 12rem;
        min-width: 0;
    }

    [data-testid="stHorizontalBlock"] .stButton > button,
    [data-testid="stHorizontalBlock"] .stDownloadButton > button {
        width: 100%;
        min-height: 40px;
    }

    .eoip-page-context {
        gap: var(--eoip-space-1) var(--eoip-space-2);
    }

    .eoip-context-item:not(:last-child)::after {
        display: none;
    }
}

@media (prefers-reduced-motion: reduce) {
    .stButton > button,
    div[class*="st-key-eoip_nav_"] button {
        transition: none;
    }
}
</style>
"""


def apply_global_styles() -> None:
    """Inject EOIP global CSS into the Streamlit application."""
    st.markdown(
        EOIP_CSS,
        unsafe_allow_html=True,
    )
