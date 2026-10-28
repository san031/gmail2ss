from collections import Counter
from pathlib import Path

import streamlit as st

import sheet
from summary import upcoming_interviews

LOG_FILE = Path(__file__).resolve().parents[2] / "logs" / "tracker.log"
SHOWN_COLUMNS = [c for c in sheet.COLUMNS if c != "Email IDs"]

st.set_page_config(page_title="Job Tracker", layout="wide")
st.title("Job Application Tracker")

rows = sheet.list_applications()

# 1. Status counts
counts = Counter(r["Status"] for r in rows)
for col, status in zip(st.columns(4),
                       ["Applied", "Interview Scheduled", "Offer", "Rejected"]):
    col.metric(status, counts.get(status, 0))

# 2. Upcoming interviews
st.subheader("Interviews in the next 7 days")
upcoming, unparsed = upcoming_interviews(7)
if upcoming:
    st.table([{"When": f"{when:%a %d %b %H:%M}", "Company": r["Company"],
               "Role": r["Role"], "Round": r["Round"]} for when, r in upcoming])
else:
    st.info("No interviews in the next 7 days.")
if unparsed:
    st.warning("Interview dates the dashboard couldn't read: "
               + ", ".join(f"{r['Company']} ({r['Interview Date']!r})" for r in unparsed))

# 3. All applications, with filters
st.subheader("All applications")
left, right = st.columns([1, 2])
status = left.selectbox("Status", ["All", *sheet.STATUSES])
search = right.text_input("Search company or role").casefold()

shown = [r for r in rows
         if (status == "All" or r["Status"] == status)
         and search in f"{r['Company'] or ''} {r['Role'] or ''}".casefold()]
st.dataframe(shown, hide_index=True, column_order=SHOWN_COLUMNS)
st.caption(f"{len(shown)} of {len(rows)} applications")

# 6. Recent agent activity
with st.expander("Recent agent activity (last 30 log lines)"):
    if LOG_FILE.exists():
        lines = LOG_FILE.read_text(encoding="utf-8").splitlines()[-30:]
        st.code("\n".join(lines), language=None)
    else:
        st.caption("No log file yet. Run the agent once.")

if st.button("Refresh"):
    st.rerun()
