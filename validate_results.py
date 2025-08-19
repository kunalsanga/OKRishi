import csv
from pathlib import Path


def main() -> None:
    root = Path(__file__).parent
    claims_path = root / "claims.csv"
    results_path = root / "results.csv"

    with claims_path.open(encoding="utf-8", newline="") as f:
        claims_rows = list(csv.DictReader(f))

    with results_path.open(encoding="utf-8", newline="") as f:
        results_reader = csv.DictReader(f)
        results_rows = list(results_reader)
        headers = results_reader.fieldnames or []

    expected_headers = ["id", "found_value", "confidence_score", "evidence_snippet"]
    header_ok = headers == expected_headers

    # Build id -> (entity, claim_type)
    meta = {row["id"].strip(): (row["entity"].strip(), row["claim_type"].strip()) for row in claims_rows}

    n_claims = len(claims_rows)
    n_results = len(results_rows)

    conf_ok = 0
    conf_bad = 0
    n_unknown = 0
    snippet_present = 0
    snippet_contains_value = 0
    snippet_contains_entity = 0

    for r in results_rows:
        val = (r.get("found_value") or "").strip()
        try:
            conf = int(str(r.get("confidence_score", "")).strip())
        except Exception:
            conf = -1
        snip = (r.get("evidence_snippet") or "").strip()
        if 0 <= conf <= 100:
            conf_ok += 1
        else:
            conf_bad += 1
        if val.upper() == "UNKNOWN":
            n_unknown += 1
        if snip:
            snippet_present += 1
        # check snippet contains value (string match)
        if val and val.upper() != "UNKNOWN" and val in snip:
            snippet_contains_value += 1
        # check snippet contains entity
        ent = meta.get(r.get("id", ""), ("", ""))[0]
        if ent and ent in snip:
            snippet_contains_entity += 1

    print("headers_ok:", header_ok)
    print("claims_count:", n_claims)
    print("results_count:", n_results)
    print("confidence_in_range:", conf_ok, "/", n_results)
    print("unknown_count:", n_unknown)
    print("snippet_present:", snippet_present, "/", n_results)
    print("snippet_contains_value:", snippet_contains_value)
    print("snippet_contains_entity:", snippet_contains_entity)


if __name__ == "__main__":
    main()


