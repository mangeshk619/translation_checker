import streamlit as st
import pandas as pd
import tempfile
import json
import re
from translation_checker import load_pairs, run_checks, load_glossary

# --- Highlighting utility ---
def highlight(text, terms, color):
    for t in terms:
        if not t:
            continue
        pattern = re.escape(t)
        repl = f"<span style='background-color:{color}; padding:2px;'>{t}</span>"
        text = re.sub(pattern, repl, text)
    return text

def render_issue(issue):
    src = issue.source
    tgt = issue.target

    if issue.issue_type == "PLACEHOLDER_MISMATCH":
        src = highlight(src, re.findall(r"%\\w+|\\{[^}]+\\}|\\$\\w+", src), "#cce5ff")
        tgt = highlight(tgt, re.findall(r"%\\w+|\\{[^}]+\\}|\\$\\w+", tgt), "#cce5ff")

    elif issue.issue_type == "NUM_MISMATCH":
        nums_src = re.findall(r"\\d+", src)
        nums_tgt = re.findall(r"\\d+", tgt)
        src = highlight(src, nums_src, "#fff3cd")
        tgt = highlight(tgt, nums_tgt, "#fff3cd")

    elif issue.issue_type == "TAG_MISMATCH":
        tags_src = re.findall(r"<[^>]+>", src)
        tags_tgt = re.findall(r"<[^>]+>", tgt)
        src = highlight(src, tags_src, "#d4edda")
        tgt = highlight(tgt, tags_tgt, "#d4edda")

    elif issue.issue_type == "EMPTY_TARGET":
        tgt = f"<span style='color:#999;'>[EMPTY]</span>"

    elif issue.issue_type == "GLOSSARY_MISMATCH":
        src_term = issue.details.split('"')[1] if '"' in issue.details else ""
        tgt_term = issue.details.split('"')[3] if '"' in issue.details else ""
        src = highlight(src, [src_term], "#f8d7da")
        tgt = highlight(tgt, [tgt_term], "#f8d7da")

    st.markdown(f"""
    **ID:** {issue.uid}  
    **Type:** {issue.issue_type}  
    **Details:** {issue.details}  

    **Source:**  
    <div style='border:1px solid #ddd; padding:6px; margin-bottom:4px;'>{src}</div>

    **Target:**  
    <div style='border:1px solid #ddd; padding:6px;'>{tgt}</div>
    """, unsafe_allow_html=True)


# --- Streamlit App UI ---
st.set_page_config(page_title="Translation QA Checker", layout="wide")
st.title("🔍 Translation QA Checker")

uploaded_source = st.file_uploader("Upload Source File", type=["xlf","xliff","csv","tsv","xlsx","txt"])
uploaded_target = st.file_uploader("Upload Translated File", type=["xlf","xliff","csv","tsv","xlsx","txt"])
uploaded_glossary = st.file_uploader("Upload Glossary (optional)", type=["csv"])
uploaded_config = st.file_uploader("Upload Client Rules JSON (optional)", type=["json"])

min_ratio = st.slider("Minimum Target/Source Length Ratio", 0.1, 1.0, 0.5)
max_ratio = st.slider("Maximum Target/Source Length Ratio", 1.0, 5.0, 3.0)

if st.button("Run QA") and uploaded_source and uploaded_target:
    with tempfile.NamedTemporaryFile(delete=False) as src_tmp, tempfile.NamedTemporaryFile(delete=False) as tgt_tmp:
        src_tmp.write(uploaded_source.read())
        tgt_tmp.write(uploaded_target.read())
        src_path, tgt_path = src_tmp.name, tgt_tmp.name

    glossary = None
    if uploaded_glossary:
        with tempfile.NamedTemporaryFile(delete=False) as g_tmp:
            g_tmp.write(uploaded_glossary.read())
            glossary = load_glossary(g_tmp.name)

    config = None
    if uploaded_config:
        config = json.load(uploaded_config)

    # Load source/target pairs
    src_pairs = load_pairs(src_path)
    tgt_pairs = load_pairs(tgt_path)

    src_map = {p.get('id') or str(i+1): p for i, p in enumerate(src_pairs)}
    tgt_map = {p.get('id') or str(i+1): p for i, p in enumerate(tgt_pairs)}

    combined = []
    all_ids = list(dict.fromkeys(list(src_map.keys()) + list(tgt_map.keys())))
    for uid in all_ids:
        combined.append({
            'id': uid,
            'source': src_map.get(uid, {}).get('source', ''),
            'target': tgt_map.get(uid, {}).get('target', '')
        })

    # Run QA checks
    issues, stats = run_checks(combined, glossary=glossary, config=config, length_ratio_limits=(min_ratio, max_ratio))

    st.subheader("📊 QA Summary")
    st.json(stats)

    if issues:
        st.subheader("⚠️ Issues Found")
        df = pd.DataFrame([i.to_dict() for i in issues])
        st.dataframe(df, use_container_width=True)

        with st.expander("🔎 Detailed Inline View"):
            for issue in issues:
                render_issue(issue)

        # Download CSV
        csv = df.to_csv(index=False).encode("utf-8")
        st.download_button("Download Issues CSV", csv, "issues.csv", "text/csv")
    else:
        st.success("✅ No issues found!")
