"""Shared CSS styling for the EOIP Streamlit application."""

from __future__ import annotations

import streamlit as st

EOIP_CSS = """
<style>
:root {
    --eoip-bg: #f6f8fb;
    --eoip-surface: #ffffff;
    --eoip-surface-soft: #f0f4f8;
    --eoip-text: #1f2937;
    --eoip-muted: #6b7280;
    --eoip-border: #e5e7eb;
    --eoip-primary: #f5b400;
    --eoip-primary-dark: #d99b00;
    --eoip-success: #16803c;
    --eoip-warning: #b26a00;
    --eoip-danger: #c0392b;
}

html,
body,
[class*="css"] {
    font-family:
        Inter,
        "Segoe UI",
        Arial,
        sans-serif;
}

.stApp {
    background:
        linear-gradient(
            180deg,
            #ffffff 0%,
            var(--eoip-bg) 100%
        );
    color: var(--eoip-text);
}

[data-testid="stSidebar"] {
    background:
        linear-gradient(
            180deg,
            #f1f4f8 0%,
            #e9eef4 100%
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

[data-testid="stSidebar"] p {
    color: var(--eoip-muted);
}

.block-container {
    max-width: 1500px;
    padding-top: 2.2rem;
    padding-bottom: 3rem;
}

h1 {
    color: var(--eoip-text);
    font-weight: 750;
    letter-spacing: -0.03em;
}

h2,
h3 {
    color: var(--eoip-text);
    font-weight: 700;
    letter-spacing: -0.02em;
}

[data-testid="stCaptionContainer"] {
    color: var(--eoip-muted);
}

[data-testid="stMetric"] {
    background: var(--eoip-surface);
    border: 1px solid var(--eoip-border);
    border-radius: 14px;
    padding: 1rem 1.1rem;
    box-shadow:
        0 2px 8px rgba(15, 23, 42, 0.04);
    min-width: min(100%, 12rem);
    flex: 1 1 12rem;
}

[data-testid="stMetricLabel"] {
    color: var(--eoip-muted);
    font-weight: 600;
}

[data-testid="stMetricValue"] {
    color: var(--eoip-text);
    font-weight: 750;
    font-size: clamp(1.35rem, 2.2vw, 2rem);
    line-height: 1.2;
    overflow: visible;
    text-overflow: clip;
    white-space: normal;
    overflow-wrap: anywhere;
}

[data-testid="stMetricDelta"] {
    font-weight: 600;
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
    font-weight: 650;
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
    font-weight: 650;
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

.eoip-eyebrow {
    color: var(--eoip-primary-dark);
    font-size: 0.78rem;
    font-weight: 700;
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

@media (max-width: 900px) {
    .block-container {
        padding-left: 1rem;
        padding-right: 1rem;
    }

    h1 {
        font-size: clamp(1.65rem, 6vw, 2rem);
        line-height: 1.15;
    }

    [data-testid="stHorizontalBlock"] {
        flex-wrap: wrap;
    }

    [data-testid="column"] {
        min-width: min(100%, 18rem);
        flex: 1 1 18rem;
    }

    [data-testid="stMetric"] {
        min-width: min(100%, 10rem);
        padding: 0.85rem 0.9rem;
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
}
</style>
"""


def apply_global_styles() -> None:
    """Inject EOIP global CSS into the Streamlit application."""
    st.markdown(
        EOIP_CSS,
        unsafe_allow_html=True,
    )
