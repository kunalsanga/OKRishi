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
            m = re.search(r"(-?\d+)", cleaned_digits)
            if m:
                try:
                    return int(m.group(1))
                except ValueError:
                    pass
        return cleaned

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

    def build_patterns(field_phrase: str) -> List[re.Pattern]:
        # Allow emails, words, spaces, dots, dashes, apostrophes, slashes, and numbers
        val = r"(?P<val>[A-Za-z0-9@._%+\- '&/]+)"
        patterns = [
            rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\bis\s+{val}",
            rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\bequal to\s+{val}",
            rf"{entity_escaped}[^.?!]*?\b{re.escape(field_phrase)}\b[^.?!]*?\blisted as\s+{val}",
            rf"{entity_escaped}[^.?!]*?'s\s+{re.escape(field_phrase)}\s+as\s+{val}",
        ]
        if field_phrase in {"headquarters", "regional hq"}:
            patterns.extend([
                rf"{entity_escaped}[^.?!]*?is\s+headquartered\s+in\s+{val}",
                rf"{entity_escaped}[^.?!]*?\bheadquarters\b[^.?!]*?\bas\s+{val}",
            ])
        if field_phrase in {"founded year"}:
            patterns.append(rf"{entity_escaped}[^.?!]*?\bfounded\s+in\s+(?P<val>\d{{4}})")
        return [re.compile(p, flags=re.IGNORECASE | re.DOTALL) for p in patterns]

    for filename, content in webpages.items():
        if entity.lower() not in content.lower():
            continue
        for alias in field_aliases:
            for pattern in build_patterns(alias):
                m = pattern.search(content)
                if not m:
                    continue
                raw_value = m.group("val")
                value_clean = normalize_text(re.sub(r"[\s\.,;:]+$", "", raw_value))
                start, end = m.span()
                snippet_start = max(0, start - 80)
                snippet_end = min(len(content), end + 80)
                snippet = normalize_text(content[snippet_start:snippet_end])
                confidence = 95
                value_final = cast_if_numeric(value_clean, claim_norm)
                return value_final, confidence, snippet

    if claim_norm in {"regional hq"}:
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
                return value_clean, 88, snippet

    return "UNKNOWN", 0, "No evidence found"


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


