"""Render the saved research record without network access."""

from io import BytesIO
from pathlib import Path
import re
import unicodedata
from xml.sax.saxutils import escape

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Paragraph, SimpleDocTemplate

from app.models import Note, utc_now
from app.config import PROJECT_ROOT
from app.services.presentation import research_sections


# ReportLab ships these fonts; embed them for accented research text on any host.
_fonts = Path(reportlab.__file__).parent / "fonts"
pdfmetrics.registerFont(TTFont("Research", str(_fonts / "Vera.ttf")))
pdfmetrics.registerFont(TTFont("ResearchBold", str(_fonts / "VeraBd.ttf")))


class EmojiFont(TTFont):
    def addObjects(self, doc):
        super().addObjects(doc)
        # ReportLab 4 writes astral code points as invalid 5-digit CMap targets.
        # PDF requires UTF-16 surrogate pairs for searchable/copyable emoji.
        for name, stream in doc.idToObject.items():
            if name.startswith("toUnicodeCMap:") and self.face.name.decode() in name:
                stream.content = re.sub(
                    r"(<[0-9A-F]{2}> )<([0-9A-F]{5,6})>",
                    lambda match: match[1] + "<" + chr(int(match[2], 16)).encode(
                        "utf-16-be"
                    ).hex().upper() + ">",
                    stream.content,
                )


pdfmetrics.registerFont(EmojiFont(
    "ResearchSymbols", str(PROJECT_ROOT / "app/static/fonts/NotoEmoji.ttf")
))


def pdf_filename(title: str) -> str:
    ascii_title = unicodedata.normalize("NFKD", title).encode("ascii", "ignore").decode()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-")[:100].rstrip("-")
    return f"{slug or 'afterthought-research'}.pdf"


def export_research(note: Note, sources: list[dict]) -> bytes:
    styles = getSampleStyleSheet()
    for style in styles.byName.values():
        style.fontName = "Research"
        style.splitLongWords = True
    for name in ("Title", "Heading1", "Heading2", "Heading3"):
        styles[name].fontName = "ResearchBold"
        styles[name].keepWithNext = True
    styles["BodyText"].fontSize = 10
    styles["BodyText"].leading = 15
    styles["BodyText"].spaceAfter = 7
    story = []

    def add(text: str, style: str = "BodyText", bullet: bool = False):
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        font = pdfmetrics.getFont(styles[style].fontName).face.charToGlyph
        symbols = pdfmetrics.getFont("ResearchSymbols").face.charToGlyph
        # Source titles can include emoji absent from the body font.
        markup = "".join(
            f'<font name="ResearchSymbols">{escape(char)}</font>'
            if ord(char) not in font and ord(char) in symbols else escape(char)
            for char in text
        ).replace("\n", "<br/>")
        story.append(Paragraph(markup, styles[style],
                               bulletText="-" if bullet else None))

    def timestamp(label, value):
        if value:
            add(f"{label}: {value.strftime('%Y-%m-%d %H:%M:%S')} UTC")

    add("AFTERTHOUGHT", "Heading2")
    add(note.title, "Title")
    timestamp("Created", note.created_at)
    add("Original thought", "Heading2")
    add(note.body)
    if note.context:
        add("Context", "Heading2")
        add(note.context)
    add("Research", "Heading1")
    for section in research_sections(note.research_summary or ""):
        add(section["title"], "Heading2")
        for block in section["blocks"]:
            for item in block["items"]:
                add(item, bullet=block["kind"] == "list")
        if not section["blocks"]:
            add("Not provided in this brief.")
    if note.followups:
        add("Follow-up discussion", "Heading1")
        for index, followup in enumerate(note.followups, 1):
            add(f"Follow-up {index}", "Heading2")
            add("Question", "Heading3")
            add(followup.question)
            add("Answer", "Heading3")
            add(followup.answer)
    add("Sources", "Heading1")
    for source in sources:
        add(source["title"], "Heading3")
        add(source["url"])
    if not sources:
        add("No sources found.")
    timestamp("Researched", note.researched_at)
    timestamp("Exported", utc_now())
    output = BytesIO()
    document = SimpleDocTemplate(
        output, pagesize=A4, rightMargin=54, leftMargin=54,
        topMargin=48, bottomMargin=48, title=note.title, author="Afterthought",
    )

    def page_number(canvas, document):
        canvas.setFont("Research", 8)
        canvas.drawRightString(A4[0] - 54, 28, str(document.page))

    document.build(story, onFirstPage=page_number, onLaterPages=page_number)
    return output.getvalue()
