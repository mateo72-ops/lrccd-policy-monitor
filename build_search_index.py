import csv
import json
from pathlib import Path

STATE_FILE = Path("policy_state.json")
TEXT_DIR = Path("document_text")
OUTPUT_FILE = Path("policy_search_index.csv")

CHUNK_SIZE = 4000


def split_text(text, chunk_size=CHUNK_SIZE):
    """Split document text into searchable chunks."""
    text = " ".join(text.split())

    for start in range(0, len(text), chunk_size):
        yield text[start:start + chunk_size]


def main():
    state = json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )

    indexed = 0
    chunks_created = 0
    missing = 0

    with OUTPUT_FILE.open(
        "w", newline="", encoding="utf-8-sig"
    ) as file:
        writer = csv.writer(file)

        writer.writerow([
            "DocumentKey",
            "DocumentNumber",
            "DocumentType",
            "Title",
            "RevisionDate",
            "SourceURL",
            "ChunkNumber",
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

            for chunk_number, chunk in enumerate(
                split_text(text), start=1
            ):
                writer.writerow([
                    key,
                    document.get("document_number", ""),
                    document.get("document_type", ""),
                    document.get("title", ""),
                    document.get("revision_date", ""),
                    document.get("url", ""),
                    chunk_number,
                    chunk,
                ])

                chunks_created += 1

            indexed += 1

    print(f"Documents indexed: {indexed}")
    print(f"Documents missing text: {missing}")
    print(f"Searchable sections created: {chunks_created}")
    print(f"Search index created: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
