import difflib
import hashlib
import io
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from pypdf import PdfReader

POLICY_PAGE = "https://losrios.edu/about-los-rios/board-of-trustees/policies-and-regulations"
STATE_FILE = Path("policy_state.json")
CHANGES_FILE = Path("changes.json")
TEXT_DIR = Path("document_text")
REPORT_DIR = Path("change_reports")

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/154.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,application/pdf;q=0.8,*/*;q=0.7",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": POLICY_PAGE,
}

def get_page(url):
    response = requests.get(url, headers=HEADERS, timeout=30, allow_redirects=True)
    print(f"  HTTP {response.status_code} | {response.headers.get('Content-Type', 'unknown')} | {response.url}")
    response.raise_for_status()
    return response

def discover_documents():
    soup = BeautifulSoup(get_page(POLICY_PAGE).text, "html.parser")
    documents = {}
    for link in soup.find_all("a", href=True):
        text = " ".join(link.stripped_strings)
        if not text:
            continue
        match = re.search(r"\b(Policy|Regulation)\s+([1-9]\d{3})\b", text, re.IGNORECASE)
        if not match:
            continue
        document_type = match.group(1).title()
        document_number = match.group(2)
        title = re.sub(r"^(Policy|Regulation)\s+[1-9]\d{3}\s*[-–:]?\s*", "", text, flags=re.IGNORECASE).strip()
        url = urljoin("https://losrios.edu/", link["href"].lstrip("/"))
        key = f"{document_type}-{document_number}"
        documents[key] = {"document_number": document_number, "document_type": document_type, "title": title, "url": url}
    return documents

def extract_pdf_text(pdf_bytes):
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n\n".join((page.extract_text() or "") for page in reader.pages).strip()
def find_section(lines, changed_line_index):
    """
    Look backward from a changed line and find the nearest
    numbered section heading.
    """
    section_pattern = re.compile(
        r"^\s*(\d+(?:\.\d+)*)\s+(.+)$"
    )

    for index in range(changed_line_index, -1, -1):
        line = lines[index].strip()
        match = section_pattern.match(line)

        if match:
            section_number = match.group(1)
            section_title = match.group(2)

            # Ignore numbered paragraphs that are really body text.
            if len(section_title.split()) <= 8:
                return f"{section_number} {section_title}"

    return "Section could not be determined automatically"
def download_document(url):
    response = get_page(url)
    data = response.content
    return data, {
        "sha256": hashlib.sha256(data).hexdigest(),
        "size_bytes": len(data),
        "content_type": response.headers.get("Content-Type", ""),
    }

def load_previous_state():
    return json.loads(STATE_FILE.read_text(encoding="utf-8")) if STATE_FILE.exists() else {}

def text_path_for(key):
    return TEXT_DIR / f"{key}.txt"

def save_text(key, text):
    TEXT_DIR.mkdir(exist_ok=True)
    path = text_path_for(key)
    path.write_text(text, encoding="utf-8")
    return str(path)

def make_change_report(key, document, old_text, new_text, detected_at):
    diff_lines = list(difflib.unified_diff(
        old_text.splitlines(),
        new_text.splitlines(),
        fromfile=f"{key} OLD",
        tofile=f"{key} NEW",
        lineterm="",
        n=3,
    ))

    old_lines = old_text.splitlines()
    new_lines = new_text.splitlines()

    matcher = difflib.SequenceMatcher(
        None,
        old_lines,
        new_lines,
    )

    affected_sections = []

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue

        section = find_section(
            old_lines,
            max(i1 - 1, 0)
        )

        if section not in affected_sections:
            affected_sections.append(section)
    safe_time = detected_at.replace(":", "-").replace("+", "_")
    report_path = REPORT_DIR / f"{key}_{safe_time}.md"

    section_lines = ["## Affected section(s)", ""]

    if affected_sections:
        for section in affected_sections:
            section_lines.append(f"- {section}")
    else:
        section_lines.append("- Section could not be determined automatically")

    section_lines.append("")
    header = [
        f"# Change Report: {key}", "",
        f"**Title:** {document['title']}",
        f"**Type:** {document['document_type']}",
        f"**Number:** {document['document_number']}",
        f"**Detected:** {detected_at}",
        f"**Source:** {document['url']}", "",
        "## Text changes", "",
        "Lines beginning with `-` were removed from the prior version.",
        "Lines beginning with `+` were added in the new version.", "",
        "```diff",
    ]
    report_path.write_text("\n".join(header + section_lines + diff_lines + ["```", ""]), encoding="utf-8")
    added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
    removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))
    return str(report_path), added, removed

def main():
    print("LRCCD Policy & Regulation Monitor")
    print("---------------------------------")
    checked_at = datetime.now(timezone.utc).isoformat()
    documents = discover_documents()
    print(f"Discovered {len(documents)} documents.")
    previous_state = load_previous_state()
    new_state, changes = {}, []

    for count, (key, document) in enumerate(sorted(documents.items()), start=1):
        print(f"[{count}/{len(documents)}] {key} - {document['title']}")
        try:
            pdf_bytes, fingerprint = download_document(document["url"])
        except Exception as error:
            print(f"  ERROR: {error}")
            new_state[key] = {**document, "status": "error", "error": str(error), "last_checked": checked_at}
            continue

        current = {**document, **fingerprint, "last_checked": checked_at}
        previous = previous_state.get(key)
        baseline_path = text_path_for(key)

        if previous is None or previous.get("sha256") is None:
            current["status"] = "baseline"
            try:
                new_text = extract_pdf_text(pdf_bytes)
                current["text_file"] = save_text(key, new_text)
                current["text_extracted"] = True
            except Exception as error:
                print(f"  TEXT EXTRACTION ERROR: {error}")
                current["text_extracted"] = False
                current["text_error"] = str(error)

        elif previous.get("sha256") != current["sha256"]:
            current["status"] = "changed"
            print("  *** CHANGE DETECTED ***")
            report_file = None
            added = removed = None
            try:
                new_text = extract_pdf_text(pdf_bytes)
                if baseline_path.exists():
                    old_text = baseline_path.read_text(encoding="utf-8")
                    report_file, added, removed = make_change_report(key, document, old_text, new_text, checked_at)
                    print(f"  Change report created: {added} added lines, {removed} removed lines.")
                else:
                    print("  No prior text baseline was available.")
                current["text_file"] = save_text(key, new_text)
                current["text_extracted"] = True
            except Exception as error:
                print(f"  TEXT EXTRACTION/DIFF ERROR: {error}")
                current["text_extracted"] = False
                current["text_error"] = str(error)

            changes.append({
                "key": key, "document_number": current["document_number"],
                "document_type": current["document_type"], "title": current["title"],
                "url": current["url"], "detected_at": checked_at,
                "old_sha256": previous.get("sha256"), "new_sha256": current["sha256"],
                "old_size_bytes": previous.get("size_bytes"), "new_size_bytes": current["size_bytes"],
                "report_file": report_file, "added_lines": added, "removed_lines": removed,
            })

        else:
            current["status"] = "unchanged"
            if not baseline_path.exists():
                try:
                    new_text = extract_pdf_text(pdf_bytes)
                    current["text_file"] = save_text(key, new_text)
                    current["text_extracted"] = True
                    print("  Text baseline created.")
                except Exception as error:
                    print(f"  TEXT EXTRACTION ERROR: {error}")
                    current["text_extracted"] = False
                    current["text_error"] = str(error)
            else:
                current["text_file"] = str(baseline_path)
                current["text_extracted"] = True
        new_state[key] = current

    STATE_FILE.write_text(json.dumps(new_state, indent=2), encoding="utf-8")
    CHANGES_FILE.write_text(json.dumps(changes, indent=2), encoding="utf-8")
    print()
    print("---------------------------------")
    print(f"Documents checked: {len(new_state)}")
    print(f"Changes detected: {len(changes)}")
    print(f"Text baselines available: {sum(1 for item in new_state.values() if item.get('text_extracted'))}")
    print(f"Change reports created: {sum(1 for change in changes if change.get('report_file'))}")

if __name__ == "__main__":
    main()
