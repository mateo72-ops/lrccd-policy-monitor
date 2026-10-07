import difflib
import re
from pathlib import Path

BASELINE = Path("document_text/Policy-1111.txt")

original_text = BASELINE.read_text(encoding="utf-8")

# Create a simulated revision in memory only.
# The production baseline file is never modified.
revised_text = original_text.replace(
    "The District has a responsibility to inform the public of important events",
    "The District shall promptly inform the public of important events"
)


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


original_lines = original_text.splitlines()
revised_lines = revised_text.splitlines()

matcher = difflib.SequenceMatcher(
    None,
    original_lines,
    revised_lines
)

changes = []

for tag, i1, i2, j1, j2 in matcher.get_opcodes():
    if tag == "equal":
        continue

    old_lines = original_lines[i1:i2]
    new_lines = revised_lines[j1:j2]

    section = find_section(
        original_lines,
        max(i1 - 1, 0)
    )

    changes.append(
        {
            "type": tag,
            "section": section,
            "old": old_lines,
            "new": new_lines,
        }
    )

print("=" * 70)
print("LRCCD POLICY CHANGE REPORT - AUTOMATIC SECTION TEST")
print("=" * 70)
print()
print("Document: Policy 1111 - News Media Communication")
print("Test type: Simulated policy revision")
print("Production baseline modified: NO")
print()
print(f"Changes found: {len(changes)}")
print()

for number, change in enumerate(changes, start=1):
    print("-" * 70)
    print(f"CHANGE {number}")
    print("-" * 70)
    print()
    print(f"Section affected: {change['section']}")
    print()

    print("Previous language:")
    if change["old"]:
        for line in change["old"]:
            print(f"- {line}")
    else:
        print("- No previous text")

    print()
    print("Revised language:")
    if change["new"]:
        for line in change["new"]:
            print(f"+ {line}")
    else:
        print("+ Text removed")

    print()

print("=" * 70)
print("TEST COMPLETE - NO PRODUCTION BASELINES WERE CHANGED")
print("=" * 70)
