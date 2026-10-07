from datetime import datetime, timezone
from pathlib import Path

from monitor import make_change_report


BASELINE = Path("document_text/Policy-1111.txt")

original_text = BASELINE.read_text(encoding="utf-8")

# Create a simulated revision in memory only.
# The production baseline file is never modified.
revised_text = original_text.replace(
    "The District has a responsibility to inform the public of important events",
    "The District shall promptly inform the public of important events"
)

if revised_text == original_text:
    raise RuntimeError(
        "Test text was not found in Policy-1111 baseline. "
        "No simulated change was created."
    )

document = {
    "title": "News Media Communication",
    "document_type": "Policy",
    "document_number": "1111",
    "url": "SIMULATED TEST - NO LIVE DOCUMENT CHANGED",
}

detected_at = datetime.now(timezone.utc).isoformat()

report_file, added, removed = make_change_report(
    "Policy-1111-TEST",
    document,
    original_text,
    revised_text,
    detected_at,
)

print("=" * 70)
print("PRODUCTION CHANGE REPORT TEST")
print("=" * 70)
print()
print("Production baseline modified: NO")
print(f"Report created: {report_file}")
print(f"Lines added: {added}")
print(f"Lines removed: {removed}")
print()
print("Generated production report:")
print("-" * 70)
print()

report_text = Path(report_file).read_text(encoding="utf-8")
print(report_text)

print()
print("=" * 70)
print("TEST COMPLETE - NO PRODUCTION BASELINES WERE CHANGED")
print("=" * 70)
