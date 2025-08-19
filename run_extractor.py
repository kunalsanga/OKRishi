import re
import csv
from pathlib import Path
from typing import Dict, Tuple, Optional, List, Any


def load_webpages(webpages_dir: Path) -> Dict[str, str]:
    webpages: Dict[str, str] = {}
    for html_file in webpages_dir.glob("*.html"):
        try:
            webpages[html_file.name] = html_file.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            # Fallback read without encoding errors breaking the run
            webpages[html_file.name] = html_file.read_text(errors="ignore")
    return webpages


def extract_answer(entity: str, claim_type: str, webpages: Dict[str, str]) -> Tuple[Any, int, str]:
    """Find the value for (entity, claim_type) by parsing the webpages.

    Returns: (found_value, confidence_score, evidence_snippet)
    """

    def normalize_text(text: str) -> str:
        return re.sub(r"\s+", " ", text).strip()

    def cast_if_numeric(value_text: str, claim_label: str):
        cleaned = value_text.strip()
        cleaned_digits = cleaned.replace(",", "")
        numeric_claims = {
            "number of offices",
            "annual revenue (usd millions)",
            "subscription price (usd)",
            "customer satisfaction (score)",
            "employee count (approx)",
            "public listing year",
            "founded year",
            "product launch year",
            "last funding round year",
        }
        if claim_label in numeric_claims:
            # Prefer 4-digit year if present for year-like claims
            if claim_label in {"public listing year", "founded year", "product launch year", "last funding round year"}:
                m_year = re.search(r"\b(\d{4})\b", cleaned_digits)
                if m_year:
                    try:
                        return int(m_year.group(1))
                    except ValueError:
                        pass
            m = re.search(r"(-?\d+)", cleaned_digits)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
        return cleaned

    def is_valid_by_type(value: str, claim_label: str) -> bool:
        text = str(value).strip()
        lower = text.lower()
        # Email validation
        if claim_label == "support email":
            return bool(re.fullmatch(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", text))

        # Year-like claims
        if claim_label in {"public listing year", "founded year", "product launch year", "last funding round year"}:
            if re.fullmatch(r"\d{4}", text):
                year = int(text)
                return 1900 <= year <= 2025
            return False

        # Numeric scalar claims
        if claim_label in {"number of offices", "employee count (approx)"}:
            if re.fullmatch(r"-?\d+", text):
                n = int(text)
                return 0 <= n <= 1000000
            return False

        if claim_label == "customer satisfaction (score)":
            if re.fullmatch(r"-?\d+", text):
                n = int(text)
                return 0 <= n <= 100
            return False

        if claim_label in {"subscription price (usd)", "annual revenue (usd millions)"}:
            # Accept integers for now
            if re.fullmatch(r"-?\d+", text):
                n = int(text)
                return -1 <= n <= 1000000
            return False

        # Textual fields should not be obvious emails or pure numbers
        if "@" in text:
            return False
        if re.fullmatch(r"\d+", text):
            return False
        # Minimal sanity: has at least one letter
        return bool(re.search(r"[A-Za-z]", text))

    canonical_field_aliases: Dict[str, List[str]] = {
        "number of offices": ["number of offices"],
        "main competitor": ["main competitor"],
        "annual revenue (usd millions)": ["annual revenue (usd millions)"],
        "research lab location": ["research lab location"],
        "ceo": ["ceo"],
        "subscription price (usd)": ["subscription price (usd)"],
        "support email": ["support email"],
        "recent award": ["recent award"],
        "regional hq": ["regional hq", "headquarters"],
        "headquarters neighborhood": ["headquarters neighborhood"],
        "manufacturing site": ["manufacturing site"],
        "public listing year": ["public listing year"],
        "core technology": ["core technology"],
        "major client": ["major client"],
        "founded year": ["founded year"],
        "partner organization": ["partner organization"],
        "product launch year": ["product launch year", "launch year"],
        "customer satisfaction (score)": ["customer satisfaction (score)"],
        "employee count (approx)": ["employee count (approx)"],
        "primary market": ["primary market"],
        "flagship product": ["flagship product"],
        "last funding round year": ["last funding round year"],
        "founder": ["founder"],
        "slogan": ["slogan"],
    }

    entity_escaped = re.escape(entity)
    claim_norm = claim_type.strip().lower()
    field_aliases: List[str] = canonical_field_aliases.get(claim_norm, [claim_norm])

    def build_patterns(field_phrase: str) -> List[Tuple[re.Pattern, int]]:
        # Allow emails, words, spaces, dots, dashes, apostrophes, slashes, and numbers
        val = r"(?P<val>[A-Za-z0-9@._%+\- '&/]+)"
        patterns: List[Tuple[str, int]] = [
            # base patterns with relative strengths
            (rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\bis\s+{val}", 4),
            (rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\bequal to\s+{val}", 5),
            (rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\blisted as\s+{val}", 6),
            (rf"{entity_escaped}[^.?!]*?'s\s+{re.escape(field_phrase)}\s+as\s+{val}", 6),
            # "reports that its FIELD is VALUE"
            (rf"{entity_escaped}[^.?!]*?reports that (its|their)\s+{re.escape(field_phrase)}\s+is\s+{val}", 5),
            # filings / archived materials / observers
            (rf"company filings list\s+{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?as\s+{val}", 7),
            (rf"according to archived materials,\s*{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?listed as\s+{val}", 6),
            (rf"industry observers note\s+{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?equal to\s+{val}", 6),
            # simple separators
            (rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?[:=]\s*{val}", 4),
        ]
        if field_phrase in {"headquarters", "regional hq"}:
            patterns.extend([
                (rf"{entity_escaped}[^.?!]*?is\s+headquartered\s+in\s+{val}", 7),
                (rf"{entity_escaped}[^.?!]*?\bheadquarters\b[^.?!]*?\bas\s+{val}", 5),
            ])
        if field_phrase in {"founded year"}:
            patterns.append((rf"{entity_escaped}[^.?!]*?\bfounded\s+in\s+(?P<val>\d{{4}})", 7))
        return [(re.compile(p, flags=re.IGNORECASE | re.DOTALL), strength) for p, strength in patterns]

    # Collect candidates across pages
    candidates: List[Dict[str, Any]] = []
    for filename, content in webpages.items():
        if entity.lower() not in content.lower():
            continue
        for alias in field_aliases:
            for pattern, strength in build_patterns(alias):
                for m in pattern.finditer(content):
                    raw_value = m.group("val")
                    value_clean = normalize_text(re.sub(r"[\s\.,;:]+$", "", raw_value))
                    start, end = m.span()
                    snippet_start = max(0, start - 80)
                    snippet_end = min(len(content), end + 80)
                    snippet = normalize_text(content[snippet_start:snippet_end])
                    value_final = cast_if_numeric(value_clean, claim_norm)
                    if is_valid_by_type(str(value_final), claim_norm):
                        candidates.append({
                            "value": value_final,
                            "snippet": snippet,
                            "strength": strength,
                            "file": filename,
                        })

    # Specialized fallback for support email
    if not candidates and claim_norm == "support email":
        email_pat = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
        for filename, content in webpages.items():
            if entity.lower() not in content.lower():
                continue
            # Look at sentences with entity mention
            for sent in re.split(r"(?<=[.?!])\s+", content):
                if entity in sent:
                    m = email_pat.search(sent)
                    if m:
                        email = m.group(0)
                        snippet = normalize_text(sent)
                        if is_valid_by_type(email, claim_norm):
                            candidates.append({
                                "value": email,
                                "snippet": snippet,
                                "strength": 4,
                                "file": filename,
                            })

    if not candidates and claim_norm in {"regional hq"}:
        hq_pat = re.compile(
            rf"{entity_escaped}[^.?!]*?headquartered\s+in\s+(?P<val>[A-Za-z0-9 .\-'/&]+)",
            re.IGNORECASE | re.DOTALL,
        )
        for filename, content in webpages.items():
            if entity.lower() not in content.lower():
                continue
            m = hq_pat.search(content)
            if m:
                raw_value = m.group("val")
                value_clean = normalize_text(re.sub(r"[\s\.,;:]+$", "", raw_value))
                start, end = m.span()
                snippet_start = max(0, start - 80)
                snippet_end = min(len(content), end + 80)
                snippet = normalize_text(content[snippet_start:snippet_end])
                if is_valid_by_type(value_clean, claim_norm):
                    candidates.append({
                        "value": value_clean,
                        "snippet": snippet,
                        "strength": 6,
                        "file": filename,
                    })

    if not candidates:
        return "UNKNOWN", 0, "No evidence found"

    # Aggregate by value: majority vote
    counts: Dict[str, int] = {}
    best_strength: Dict[str, int] = {}
    best_snippet: Dict[str, str] = {}
    files_seen: Dict[str, set] = {}
    for c in candidates:
        v = str(c["value"])  # use string key for grouping
        counts[v] = counts.get(v, 0) + 1
        best_strength[v] = max(best_strength.get(v, 0), c["strength"])
        if v not in best_snippet:
            best_snippet[v] = c["snippet"]
        files_seen.setdefault(v, set()).add(c["file"])

    # Choose value with highest count, break ties by strength then by file diversity
    sorted_vals = sorted(counts.keys(), key=lambda v: (counts[v], best_strength[v], len(files_seen[v])), reverse=True)
    chosen_key = sorted_vals[0]

    # Confidence calibration
    num_distinct = len(counts)
    occurrences = counts[chosen_key]
    strength = best_strength[chosen_key]
    diversity = len(files_seen[chosen_key])
    confidence = 70 + (strength * 3) + min(15, (occurrences - 1) * 4) + min(10, (diversity - 1) * 3)
    if num_distinct > 1:
        confidence -= 10
    confidence = max(50, min(98, confidence))

    # Cast back to numeric if possible for final value
    final_value = candidates[0]["value"]
    # Use the chosen key to find original typed value
    for c in candidates:
        if str(c["value"]) == chosen_key:
            final_value = c["value"]
            chosen_snippet = c["snippet"]
            break

    return final_value, int(confidence), chosen_snippet


def main() -> None:
    project_root = Path(__file__).parent
    claims_path = project_root / "claims.csv"
    webpages_dir = project_root / "webpages"

    if not claims_path.exists():
        raise FileNotFoundError(f"Missing claims.csv at: {claims_path}")
    if not webpages_dir.exists():
        raise FileNotFoundError(f"Missing webpages directory at: {webpages_dir}")

    webpages = load_webpages(webpages_dir)

    results: List[Dict[str, Any]] = []
    with claims_path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            claim_id = row.get("id", "").strip()
            entity = row.get("entity", "").strip()
            claim_type = row.get("claim_type", "").strip()

            found_value, confidence_score, evidence_snippet = extract_answer(entity, claim_type, webpages)

            results.append(
                {
                    "id": claim_id,
                    "found_value": found_value,
                    "confidence_score": confidence_score,
                    "evidence_snippet": evidence_snippet,
                }
            )

    # Write outputs
    fieldnames = ["id", "found_value", "confidence_score", "evidence_snippet"]
    results_path = project_root / "results.csv"
    with results_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    submit_path = project_root / "Kunal_results.csv"
    with submit_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in results:
            writer.writerow(r)

    print(f"Wrote {len(results)} rows to {results_path.name} and {submit_path.name}")


if __name__ == "__main__":
    main()


