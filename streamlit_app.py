import streamlit as st
import pandas as pd
import tempfile
import os
from translation_checker import load_pairs, load_glossary, run_checks

st.set_page_config(page_title="Translation QA Checker", layout="wide")

st.title("📝 Translation QA Checker")

st.write(
    "Upload **Source** and **Target** files for comparison. "
    "Supported formats:\n\n"
    "- **Source**: Word (.docx), Excel (.xlsx), PowerPoint (.pptx), PDF (.pdf)\n"
    "- **Target**: Word (.docx), Excel (.xlsx), PowerPoint (.pptx)"
)

# --- File uploaders ---
src_file = st.file_uploader("Upload Source File", type=["docx", "xlsx", "pptx", "pdf"])
tgt_file = st.file_uploader("Upload Target File", type=["docx", "xlsx", "pptx"])

glossary_file = st.file_uploader("Upload Glossary (optional, CSV with columns: source,target)", type=["csv"])

if src_file and tgt_file:
    with tempfile.TemporaryDirectory() as tmpdir:
        # Save files temporarily
        src_path = os.path.join(tmpdir, src_file.name)
        tgt_path = os.path.join(tmpdir, tgt_file.name)

        with open(src_path, "wb") as f:
            f.write(src_file.read())
        with open(tgt_path, "wb") as f:
            f.write(tgt_file.read())

        glossary = None
        if glossary_file:
            gloss_path = os.path.join(tmpdir, glossary_file.name)
            with open(gloss_path, "wb") as f:
                f.write(glossary_file.read())
            glossary = load_glossary(gloss_path)

        # --- Align Source & Target ---
        try:
            combined = load_pairs(src_path, tgt_path)
        except Exception as e:
            st.error(f"Error reading files: {e}")
            st.stop()

        st.success(f"Loaded {len(combined)} aligned segments ✅")

        # --- Run QA Checks ---
        if st.button("Run QA Checks"):
            issues, stats = run_checks(combined, glossary=glossary)

            st.subheader("QA Summary")
            st.write(f"Total Segments: {stats['total']}")
            st.write(f"Issues Found: {stats['issues']}")

            if issues:
                st.subheader("Detailed Issues")
                df = pd.DataFrame([i.to_dict() for i in issues])
                st.dataframe(df, use_container_width=True)

                # Download CSV
                csv = df.to_csv(index=False).encode("utf-8-sig")
                st.download_button(
                    label="Download Issues as CSV",
                    data=csv,
                    file_name="qa_issues.csv",
                    mime="text/csv"
                )
            else:
                st.success("No issues found 🎉")
