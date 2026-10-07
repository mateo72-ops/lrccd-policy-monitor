import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

POLICY_PAGE = (
    "https://losrios.edu/about-los-rios/"
    "board-of-trustees/policies-and-regulations"
)

STATE_FILE = Path("policy_state.json")
CHANGES_FILE = Path("changes.json")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept": (
        "text/html,application/xhtml+xml,application/xml;q=0.9,"
        "application/pdf;q=0.8,*/*;q=0.7"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": POLICY_PAGE,
}


def get_page(url):
    response = requests.get(
        url,
        headers=HEADERS,
        timeout=30,
        allow_redirects=True
    )

    print(
        f"  HTTP {response.status_code} | "
        f"{response.headers.get('Content-Type', 'unknown')} | "
        f"{response.url}"
    )

    response.raise_for_status()
    return response


def discover_documents():
    response = get_page(POLICY_PAGE)
    soup = BeautifulSoup(response.text, "html.parser")

    documents = {}

    for link in soup.find_all("a", href=True):
        text = " ".join(link.stripped_strings)

        if not text:
            continue

        match = re.search(
            r"\b(Policy|Regulation)\s+([1-9]\d{3})\b",
            text,
            re.IGNORECASE
        )

        if not match:
            continue

        document_type = match.group(1).title()
        document_number = match.group(2)

        title = re.sub(
            r"^(Policy|Regulation)\s+[1-9]\d{3}\s*[-–:]?\s*",
            "",
            text,
            flags=re.IGNORECASE
        ).strip()

url = urljoin("https://losrios.edu/", link["href"].lstrip("/"))

        key = f"{document_type}-{document_number}"

        documents[key] = {
            "document_number": document_number,
            "document_type": document_type,
            "title": title,
            "url": url,
        }

    return documents


def fingerprint_url(url):
    response = get_page(url)

    return {
        "sha256": hashlib.sha256(response.content).hexdigest(),
        "size_bytes": len(response.content),
        "content_type": response.headers.get(
            "Content-Type", ""
        ),
    }


def load_previous_state():
    if not STATE_FILE.exists():
        return {}

    return json.loads(
        STATE_FILE.read_text(encoding="utf-8")
    )


def main():
    print("LRCCD Policy & Regulation Monitor")
    print("---------------------------------")

    checked_at = datetime.now(timezone.utc).isoformat()

    documents = discover_documents()

    print(f"Discovered {len(documents)} documents.")

    previous_state = load_previous_state()

    new_state = {}
    changes = []

    for count, (key, document) in enumerate(
        sorted(documents.items()),
        start=1
    ):
        print(
            f"[{count}/{len(documents)}] "
            f"{key} - {document['title']}"
        )

        try:
            fingerprint = fingerprint_url(document["url"])

        except Exception as error:
            print(f"  ERROR: {error}")

            document["status"] = "error"
            document["error"] = str(error)
            document["last_checked"] = checked_at

            new_state[key] = document
            continue

        current = {
            **document,
            **fingerprint,
            "last_checked": checked_at,
        }

        previous = previous_state.get(key)

        if previous is None:
            current["status"] = "baseline"

        elif previous.get("sha256") != current["sha256"]:
            current["status"] = "changed"

            changes.append(
                {
                    "key": key,
                    "document_number":
                        current["document_number"],
                    "document_type":
                        current["document_type"],
                    "title": current["title"],
                    "url": current["url"],
                    "detected_at": checked_at,
                    "old_sha256":
                        previous.get("sha256"),
                    "new_sha256":
                        current["sha256"],
                    "old_size_bytes":
                        previous.get("size_bytes"),
                    "new_size_bytes":
                        current["size_bytes"],
                }
            )

            print("  *** CHANGE DETECTED ***")

        else:
            current["status"] = "unchanged"

        new_state[key] = current

    STATE_FILE.write_text(
        json.dumps(new_state, indent=2),
        encoding="utf-8"
    )

    CHANGES_FILE.write_text(
        json.dumps(changes, indent=2),
        encoding="utf-8"
    )

    print()
    print("---------------------------------")
    print(f"Documents checked: {len(new_state)}")
    print(f"Changes detected: {len(changes)}")

    if not previous_state:
        print(
            "Initial baseline created. "
            "Future runs will detect changes."
        )


if __name__ == "__main__":
    main()
