import re
import streamlit as st
import docx2txt
from pathlib import Path

DOC_PATH = Path("An Introduction to Heat Pumps.docx")

# -----------------------
# Helpers
# -----------------------
def load_doc_text() -> str:
    if not DOC_PATH.exists():
        raise FileNotFoundError(f"Missing file: {DOC_PATH}. Put it in the same folder as app.py")
    text = docx2txt.process(str(DOC_PATH))
    # normalize whitespace
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()

def split_sections(text: str):
    # Simple section splitter based on headings in your doc
    headings = [
        "Heat Pumps: The Basics",
        "How They Work",
        "Benefits",
        "Understanding Heat Pump Costs",
        "Myths and Misperceptions",
        "FAQs",
        "Video Resources",
    ]

    # Find heading positions
    positions = []
    for h in headings:
        m = re.search(rf"\b{re.escape(h)}\b", text)
        if m:
            positions.append((m.start(), h))
    positions.sort()

    # Build sections
    sections = {}
    for i, (start, h) in enumerate(positions):
        end = positions[i + 1][0] if i + 1 < len(positions) else len(text)
        sections[h] = text[start:end].strip()

    # If headings not found, fallback to whole doc
    if not sections:
        sections["Document"] = text
    return sections

def top_snippets(sections: dict, query_terms: list[str], k: int = 5):
    scored = []
    for title, body in sections.items():
        score = 0
        for t in query_terms:
            score += len(re.findall(rf"\b{re.escape(t)}\b", body, flags=re.IGNORECASE))
        scored.append((score, title, body))
    scored.sort(reverse=True, key=lambda x: x[0])
    # keep only sections with some hits; fallback to top anyway
    picked = [x for x in scored if x[0] > 0][:k] or scored[:k]
    return picked

def bullets_from_text(text: str, max_bullets: int = 4):
    # Pull out existing bullet-style lines if present; otherwise make short sentences
    lines = [ln.strip(" •\t") for ln in text.splitlines() if ln.strip()]
    bulletish = [ln for ln in lines if ln.startswith(("·", "-", "•")) or len(ln) < 120]
    bulletish = [re.sub(r"^[·•\-]\s*", "", b).strip() for b in bulletish]
    bulletish = [b for b in bulletish if len(b) > 0]
    return bulletish[:max_bullets] if bulletish else lines[:max_bullets]

# -----------------------
# UI
# -----------------------
st.title("Heat Pump Readiness Assistant (No-API MVP)")
st.write("Free, offline prototype: guided intake → grounded briefing from the sponsor Heat Pump 101 doc.")

state = st.text_input("State (optional)", placeholder="e.g., Illinois")
home_size = st.selectbox("Home size", ["1500–2500 sq ft", "2500–5500 sq ft", "5500+ sq ft"])
heating = st.selectbox("Current heating type", ["Gas", "Electric resistance", "Oil", "Other / Not sure"])
concern = st.selectbox("Primary concern", ["Cost", "Cold climate performance", "Carbon impact", "Reliability / myths"])

st.divider()

@st.cache_data
def get_sections():
    text = load_doc_text()
    return split_sections(text)

sections = get_sections()

# Build concern → keywords mapping (simple but effective)
concern_terms = {
    "Cost": ["cost", "install", "upfront", "rebate", "range", "median", "audit", "weatherization"],
    "Cold climate performance": ["cold", "subzero", "-10", "winter", "efficient", "backup", "temperature"],
    "Carbon impact": ["carbon", "pollut", "electricity", "renewable", "coal", "emissions"],
    "Reliability / myths": ["myth", "misperception", "noisy", "old buildings", "apartments", "untested", "last long"],
}

query_terms = concern_terms[concern] + [heating.lower()]
if state:
    query_terms.append(state)

if st.button("Generate readiness briefing"):
    picked = top_snippets(sections, query_terms, k=4)

    st.subheader("Decision Briefing")

    # 1) Summary
    st.markdown("### 1) Summary")
    st.write(f"- Location: **{state or 'Not provided'}**")
    st.write(f"- Home size: **{home_size}** | Current heating: **{heating}** | Concern: **{concern}**")
    st.write("- This briefing is grounded only in the sponsor Heat Pump 101 document (offline).")

    # 2) What matters most
    st.markdown("### 2) What matters most for you")
    focus_map = {
        "Cost": ["Upfront purchase/installation costs", "Potential rebates/incentives", "Pre-work (audit/insulation) that affects outcomes"],
        "Cold climate performance": ["Operating range in cold temps", "Efficiency drop in extreme cold", "When backup heat might matter"],
        "Carbon impact": ["Electricity source matters for emissions", "Replacing combustion reduces local pollutants", "Pairing with renewables improves impact"],
        "Reliability / myths": ["Modern heat pumps address older limitations", "Noise/old home/apartment myths are common", "Sizing + installer quality drives outcomes"],
    }
    for b in focus_map[concern]:
        st.write(f"- {b}")

    # 3) Cost & planning notes
    st.markdown("### 3) Cost & planning notes")
    cost_text = sections.get("Understanding Heat Pump Costs", "")
    for b in bullets_from_text(cost_text, max_bullets=5):
        st.write(f"- {b}")

    # 4) Cold-climate / performance notes
    st.markdown("### 4) Cold-climate / performance notes")
    perf_text = (sections.get("How They Work", "") + "\n\n" + sections.get("FAQs", "")).strip()
    for b in bullets_from_text(perf_text, max_bullets=5):
        st.write(f"- {b}")

    # 5) Myths
    st.markdown("### 5) Common myths to watch for")
    myths_text = sections.get("Myths and Misperceptions", "")
    for b in bullets_from_text(myths_text, max_bullets=6):
        st.write(f"- {b}")

    # 6) Next steps
    st.markdown("### 6) Next steps checklist")
    steps = [
        "Confirm whether your home is ducted or ductless (affects indoor unit approach).",
        "Schedule an energy audit to understand insulation/air sealing needs.",
        "Identify any pre-weatherization work (insulation/sealing) to improve performance.",
        "Check your state/utility for rebates or incentive programs.",
        "Talk to an installer about sizing for both heating + cooling needs (especially for cold climates).",
    ]
    for s in steps:
        st.write(f"- [ ] {s}")

    # Sources used
    st.subheader("Source excerpts used")
    for i, (score, title, body) in enumerate(picked, start=1):
        st.markdown(f"**Source {i}: {title}** (match score: {score})")
        st.write(body[:900] + "...")