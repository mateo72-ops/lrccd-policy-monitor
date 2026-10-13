
import csv
import json
from pathlib import Path

STATE_FILE = Path("policy_state.json")
TEXT_DIR = Path("document_text")
OUTPUT_FILE = Path("policy_search_index.csv")


def main():
    state = json.loads(STATE_FILE.read_text(encoding="utf-8"))

    indexed = 0
    missing = 0

    with OUTPUT_FILE.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.writer(file)
        writer.writerow([
            "DocumentKey",
            "DocumentNumber",
            "DocumentType",
            "Title",
            "RevisionDate",
            "SourceURL",
            "SearchText",
        ])

        for key, document in sorted(state.items()):
            text_path = TEXT_DIR / f"{key}.txt"

            if not text_path.exists():
                missing += 1
                continue

            text = text_path.read_text(
                encoding="utf-8", errors="replace"
            )

            # Normalize whitespace for searching.
            search_text = " ".join(text.split())

            writer.writerow([
                key,
                document.get("document_number", ""),
                document.get("document_type", ""),
                document.get("title", ""),
                document.get("revision_date", ""),
                document.get("url", ""),
                search_text,
            ])

            indexed += 1

    print(f"Documents indexed: {indexed}")
    print(f"Documents missing text: {missing}")
    print(f"Search index created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
