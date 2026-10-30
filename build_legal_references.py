
import csv
import json
import re
from pathlib import Path

STATE_FILE = Path("policy_state.json")
TEXT_DIR = Path("document_text")
OUTPUT_FILE = Path("legal_references.csv")

PATTERNS = [
    (
        "Education Code",
        re.compile(
            r"\b(?:California\s+)?(?:Education|Ed\.?)\s+"
            r"Code\s*(?:§|§§|sections?|secs?\.?)?\s*"
            r"(\d{3,6}(?:\.\d+)?)",
            re.IGNORECASE,
        ),
    ),
    (
        "Title 5",
        re.compile(
            r"\b(?:Title\s*5(?:\s*,?\s*CCR)?|"
            r"5\s*CCR)\s*(?:§|§§|sections?|secs?\.?)?\s*"
            r"(\d{3,6}(?:\.\d+)?)",
            re.IGNORECASE,
        ),
    ),
]


def main():
    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    rows = []

    for key, document in sorted(state.items()):
        path = TEXT_DIR / f"{key}.txt"

        if not path.exists():
            continue

        text = " ".join(
            path.read_text(
                encoding="utf-8",
                errors="replace"
            ).split()
        )

        for reference_type, pattern in PATTERNS:
            for match in pattern.finditer(text):
                section = match.group(1)

                excerpt = text[
                    max(0, match.start() - 100):
                    min(len(text), match.end() + 150)
                ]

                if reference_type == "Education Code":
                    legal_url = (
                        "https://leginfo.legislature.ca.gov/"
                        "faces/codes_displaySection.xhtml?"
                        f"sectionNum={section}&lawCode=EDC"
                    )

                else:
                    legal_url = (
                        "https://www.law.cornell.edu/"
                        "regulations/california/"
                        f"5-CCR-{section}"
                    )

                rows.append([
                    key,
                    document.get("document_number", ""),
                    document.get("document_type", ""),
                    document.get("title", ""),
                    reference_type,
                    section,
                    match.group(0),
                    excerpt,
                    legal_url,
                    document.get("url", ""),
                ])

    with OUTPUT_FILE.open(
        "w",
        newline="",
        encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "DocumentKey",
            "DocumentNumber",
            "DocumentType",
            "Title",
            "ReferenceType",
            "Section",
            "CitationText",
            "Excerpt",
            "LegalURL",
            "DocumentURL",
        ])

        writer.writerows(rows)

    print(f"Legal citations found: {len(rows)}")
    print(f"Output created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
