# EOIP UI design system

EOIP uses one compact, offline-safe system font stack and a centralized hierarchy
defined in `src/eoip/app/theme.py` and exposed as CSS variables by
`src/eoip/app/styles.py`.

## Typography hierarchy

| Level | Use | Canonical implementation |
|---|---|---|
| Page title | One dashboard identity per page | `render_page_intro()` |
| Page subtitle | Concise page purpose | `render_page_intro(description=...)` |
| Section title | A meaningful content group | `render_section_header()` |
| Section description | Short context for that group | `render_section_header(description=...)` |
| Card title | Empty states and compact card content | `.eoip-card-title` |
| Body | Operational explanatory copy | Normal Streamlit text |
| KPI label/value | Metric name and primary data | `MetricCard` / `render_metric_row()` |
| Caption/metadata | Filters, timestamps, and supporting context | `st.caption()` |
| Navigation label | Primary application routes | `render_navigation()` |
| Badge/status text | Genuine semantic state only | Shared status components |

Page titles use 30px/700, section titles 19px/600, card titles 15px/600,
body text 14px/400, labels 13px/500–600, captions 12px/400, and KPI values
30px/700. The shared line-height scale is 1.2, 1.45, and 1.55. Vertical rhythm
uses 4, 8, 12, 16, 24, and 32px tokens.

Do not create page or section hierarchy with Markdown heading strings, blank
`st.write()` calls, or dashboard-local CSS. Use the canonical components above.
