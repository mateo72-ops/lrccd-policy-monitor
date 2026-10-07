import difflib
from pathlib import Path

BASELINE = Path("document_text/Policy-1111.txt")

original_text = BASELINE.read_text(encoding="utf-8")

# Create a simulated revised version in memory only.
# This does NOT alter Policy-1111.txt.
revised_text = original_text.replace(
    "The District has a responsibility to inform the public of important events",
    "The District shall promptly inform the public of important events"
)

original_lines = original_text.splitlines()
revised_lines = revised_text.splitlines()

diff = list(
    difflib.unified_diff(
        original_lines,
        revised_lines,
        fromfile="Current Policy-1111",
        tofile="Simulated Revised Policy-1111",
        lineterm=""
    )
)

print("=" * 70)
print("LRCCD POLICY CHANGE REPORT - TEST ONLY")
print("=" * 70)
print()
print("Document: Policy 1111 - News Media Communication")
print("Test type: Simulated policy revision")
print("Production baseline modified: NO")
print()
print("CHANGE DETECTED")
print()
print("Section affected: 1.2 Responsibility")
print()
print("Current language:")
print(
    "The District has a responsibility to inform the public "
    "of important events"
)
print()
print("Simulated revised language:")
print(
    "The District shall promptly inform the public "
    "of important events"
)
print()
print("Plain-language summary:")
print(
    "The simulated revision changes the District's general "
    "responsibility to inform the public into more directive "
    "language and adds an expectation that communication occur promptly."
)
print()
print("Detailed text comparison:")
print("-" * 70)

for line in diff:
    print(line)

print()
print("=" * 70)
print("TEST COMPLETE - NO PRODUCTION BASELINES WERE CHANGED")
print("=" * 70)
