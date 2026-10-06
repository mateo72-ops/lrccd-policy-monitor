import json
import re
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

POLICY_PAGE = (
    "https://losrios.edu/about-los-rios/"
    "board-of-trustees/policies-and-regulations"
)

OUTPUT_FILE = Path("policy_index.json")


def get_policy_page():
    headers = {
        "User-Agent": (
            "Mozilla/5.0 LRCCD-Policy-Monitor/1.0 "
            "(public policy monitoring)"
        )
    }

    response = requests.get(
        POLICY_PAGE,
        headers=headers,
        timeout=30
    )
    response.raise_for_status()
    return response.text


def discover_documents(html):
    soup = BeautifulSoup(html, "html.parser")
    documents = []

    for link in soup.find_all("a", href=True):
        href = link["href"]
        text = " ".join(link.stripped_strings)

        if not text:
            continue

        # Look for four-digit Los Rios policy/regulation numbers
        match = re.search(r"\b([1-9]\d{3})\b", text)

        if not match:
            continue

        document_number = match.group(1)
        full_url = urljoin(POLICY_PAGE, href)

        documents.append(
            {
                "document_number": document_number,
                "title": text,
                "url": full_url,
            }
        )

    # Remove duplicates
    unique = {}

    for document in documents:
        key = (
            document["document_number"],
            document["url"],
        )
        unique[key] = document

    return list(unique.values())


def main():
    print("Checking Los Rios Policies and Regulations...")
    print(POLICY_PAGE)

    html = get_policy_page()
    documents = discover_documents(html)

    documents.sort(
        key=lambda item: (
            item["document_number"],
            item["title"]
        )
    )

    OUTPUT_FILE.write_text(
        json.dumps(documents, indent=2),
        encoding="utf-8"
    )

    print()
    print(f"Found {len(documents)} policy/regulation links.")
    print(f"Saved inventory to {OUTPUT_FILE}")

    print("\nFirst 10 discovered documents:")

    for document in documents[:10]:
        print(
            document["document_number"],
            "-",
            document["title"]
        )


if __name__ == "__main__":
    main()
