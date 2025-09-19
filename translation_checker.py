import csv
import re
from dataclasses import dataclass
from typing import List, Dict, Tuple, Optional

@dataclass
class QAIssue:
    uid: str
    issue_type: str
    details: str
    source: str
    target: str

    def to_dict(self):
        return {
            "ID": self.uid,
            "Issue Type": self.issue_type,
            "Details": self.details,
            "Source": self.source,
            "Target": self.target,
        }


def load_pairs(file_path: str) -> List[Dict[str, str]]:
    """
    Load bilingual text pairs from CSV/TSV/TXT/XLIFF/XLSX.
    For now: support CSV/TSV/TXT/XLSX (simple format).
    """
    pairs = []

    if file_path.endswith(".csv") or file_path.endswith(".tsv") or file_path.endswith(".txt"):
        sep = "\t" if file_path.endswith(".tsv") else ","
        with open(file_path, encoding="utf-8-sig") as f:
            reader = csv.DictReader(f, delimiter=sep)
            for row in reader:
                pairs.append({"id": row.get("id") or row.get("ID") or str(len(pairs) + 1),
                              "source": row.get("source") or row.get("Source") or "",
                              "target": row.get("target") or row.get("Target") or ""})

    elif file_path.endswith(".xlsx"):
        import pandas as pd
        df = pd.read_excel(file_path)
        for i, row in df.iterrows():
            pairs.append({"id": str(row.get("id", i+1)),
                          "source": str(row.get("source", "")),
                          "target": str(row.get("target", ""))})

    else:
        raise ValueError("Unsupported file format for now.")

    return pairs


def load_glossary(file_path: str) -> Dict[str, str]:
    """
    Load glossary as dict {source_term: target_term}
    """
    glossary = {}
    with open(file_path, encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            src = row.get("source") or row.get("Source")
            tgt = row.get("target") or row.get("Target")
            if src and tgt:
                glossary[src.strip()] = tgt.strip()
    return glossary


def check_placeholders(uid: str, src: str, tgt: str) -> Optional[QAIssue]:
    pattern = r"%\w+|\{[^}]+\}|\$\w+"
    src_tokens = re.findall(pattern, src)
    tgt_tokens = re.findall(pattern, tgt)
    if sorted(src_tokens) != sorted(tgt_tokens):
        return QAIssue(uid, "PLACEHOLDER_MISMATCH",
                       f"Source={src_tokens}, Target={tgt_tokens}",
                       src, tgt)
    return None


def check_numbers(uid: str, src: str, tgt: str) -> Optional[QAIssue]:
    nums_src = re.findall(r"\d+", src)
    nums_tgt = re.findall(r"\d+", tgt)
    if sorted(nums_src) != sorted(nums_tgt):
        return QAIssue(uid, "NUM_MISMATCH",
                       f"Source={nums_src}, Target={nums_tgt}",
                       src, tgt)
    return None


def check_tags(uid: str, src: str, tgt: str) -> Optional[QAIssue]:
    tags_src = re.findall(r"<[^>]+>", src)
    tags_tgt = re.findall(r"<[^>]+>", tgt)
    if sorted(tags_src) != sorted(tags_tgt):
        return QAIssue(uid, "TAG_MISMATCH",
                       f"Source={tags_src}, Target={tags_tgt}",
                       src, tgt)
    return None


def check_empty(uid: str, src: str, tgt: str) -> Optional[QAIssue]:
    if src.strip() and not tgt.strip():
        return QAIssue(uid, "EMPTY_TARGET", "Target is empty", src, tgt)
    return None


def check_glossary(uid: str, src: str, tgt: str, glossary: Dict[str, str]) -> Optional[QAIssue]:
    for s_term, t_term in glossary.items():
        if s_term in src and t_term not in tgt:
            return QAIssue(uid, "GLOSSARY_MISMATCH",
                           f"Expected '{s_term}' -> '{t_term}'",
                           src, tgt)
    return None


def run_checks(pairs: List[Dict[str, str]],
               glossary: Optional[Dict[str, str]] = None,
               config: Optional[Dict] = None,
               length_ratio_limits: Tuple[float, float] = (0.5, 3.0)) -> Tuple[List[QAIssue], Dict]:
    """
    Run all QA checks on bilingual pairs
    """
    issues: List[QAIssue] = []
    stats = {"total": len(pairs), "issues": 0}

    for p in pairs:
        uid, src, tgt = p.get("id"), p.get("source", ""), p.get("target", "")

        # Length ratio
        if src and tgt:
            ratio = len(tgt) / max(1, len(src))
            if not (length_ratio_limits[0] <= ratio <= length_ratio_limits[1]):
                issues.append(QAIssue(uid, "LENGTH_RATIO",
                                      f"Ratio={ratio:.2f}", src, tgt))

        for check in [check_placeholders, check_numbers, check_tags, check_empty]:
            issue = check(uid, src, tgt)
            if issue:
                issues.append(issue)

        if glossary:
            issue = check_glossary(uid, src, tgt, glossary)
            if issue:
                issues.append(issue)

    stats["issues"] = len(issues)
    return issues, stats
