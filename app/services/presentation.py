"""Turn the brief's small plain-text convention into autoescaped template data."""

import re


SECTION_TITLES = ("Overview", "Important findings", "Next steps", "Uncertainties")
HEADING_ALIASES = {
    "findings": "Important findings",
    "sample findings": "Important findings",
    "use cases": "Important findings",
}


def plain_text(text: str) -> str:
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return re.sub(
        r"(\*\*|__|`|\*(?=\S)|(?<=\S)\*|(?<!\w)_(?=\S)|(?<=\S)_(?!\w))",
        "", text,
    ).strip()


def research_sections(summary: str) -> list[dict]:
    sections = {title: [] for title in SECTION_TITLES}
    current = "Overview"
    for raw_line in summary.splitlines():
        line = re.sub(r"^#{1,6}\s*", "", raw_line.strip())
        if not line or line.startswith("```") or line in ("---", "***", "___"):
            continue
        heading = plain_text(line).rstrip(":").strip()
        title = next((title for title in SECTION_TITLES if title.lower() == heading.lower()), None)
        title = title or HEADING_ALIASES.get(heading.lower())
        if title:
            current = title
            continue
        bullet = re.match(r"^(?:[-*+•]|\d+[.)])\s+(.+)$", line)
        text = plain_text(bullet.group(1) if bullet else line)
        if text:
            kind = "list" if bullet else "paragraph"
            blocks = sections[current]
            if kind == "list" and blocks and blocks[-1]["kind"] == "list":
                blocks[-1]["items"].append(text)
            else:
                blocks.append({"kind": kind, "items": [text]})
    return [{"title": title, "blocks": sections[title]} for title in SECTION_TITLES]
