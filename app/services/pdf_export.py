"""Render the saved research record without network access."""

from io import BytesIO
from pathlib import Path
import re
import unicodedata
from xml.sax.saxutils import escape
from urllib.parse import urlsplit

import reportlab
from reportlab.lib.pagesizes import A4
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import CondPageBreak, Paragraph, SimpleDocTemplate

from app.models import Note
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
    styles["Title"].alignment = 0
    styles["Title"].fontSize = 20
    styles["Title"].leading = 25
    styles["Heading1"].fontSize = 15
    styles["Heading1"].leading = 19
    styles["Heading1"].spaceBefore = 18
    styles["Heading1"].spaceAfter = 9
    styles["Heading1"].textColor = HexColor("#315c4d")
    styles["Heading2"].fontSize = 11
    styles["Heading2"].leading = 15
    styles["Heading2"].spaceBefore = 11
    styles["Heading2"].spaceAfter = 6
    styles.add(ParagraphStyle(
        "Meta", parent=styles["BodyText"], fontSize=8, leading=11,
        textColor=HexColor("#646e67"), spaceAfter=8,
    ))
    styles.add(ParagraphStyle(
        "FollowupLabel", parent=styles["Heading2"], fontSize=9, leading=12,
        textColor=HexColor("#646e67"), spaceBefore=16,
    ))
    styles.add(ParagraphStyle(
        "QALabel", parent=styles["Heading3"], fontSize=8, leading=11,
        textColor=HexColor("#315c4d"), spaceBefore=7, spaceAfter=5,
        keepWithNext=False,
    ))
    styles.add(ParagraphStyle(
        "Question", parent=styles["BodyText"], backColor=HexColor("#eef2eb"),
        borderPadding=7, leftIndent=7, rightIndent=7, spaceBefore=7, spaceAfter=14,
    ))
    styles.add(ParagraphStyle(
        "SourceTitle", parent=styles["BodyText"], fontName="ResearchBold",
        fontSize=9, leading=12, spaceBefore=7, spaceAfter=2, keepWithNext=True,
    ))
    styles.add(ParagraphStyle(
        "SourceDetails", parent=styles["Meta"], fontSize=7.5, leading=10, spaceAfter=6,
    ))
    story = []

    def text_markup(text: str, style: str) -> str:
        text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", text)
        font = pdfmetrics.getFont(styles[style].fontName).face.charToGlyph
        symbols = pdfmetrics.getFont("ResearchSymbols").face.charToGlyph
        # Source titles can include emoji absent from the body font.
        return "".join(
            f'<font name="ResearchSymbols">{escape(char)}</font>'
            if ord(char) not in font and ord(char) in symbols else escape(char)
            for char in text
        ).replace("\n", "<br/>")

    def add(text: str, style: str = "BodyText", bullet: bool = False, href: str | None = None):
        markup = text_markup(text, style)
        if href:
            safe_href = escape(href, {'"': "&quot;"})
            markup = f'<link href="{safe_href}">{markup}</link>'
        story.append(Paragraph(markup, styles[style],
                               bulletText="-" if bullet else None))

    def date_line(label, value):
        if value:
            add(f"{label}: {value:%B} {value.day}, {value.year}", "Meta")

    add("AFTERTHOUGHT", "Heading2")
    add(note.title, "Title")
    date_line("Created", note.created_at)
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
        story.append(CondPageBreak(180))
        add("Follow-up discussion", "Heading1")
        for index, followup in enumerate(note.followups, 1):
            if index > 1:
                story.append(CondPageBreak(120))
            add(f"Follow-up {index}", "FollowupLabel")
            add("Question", "QALabel")
            add(followup.question, "Question")
            # Keep a label with the first two answer lines, not the whole answer.
            story.append(CondPageBreak(65))
            add("Answer", "QALabel")
            add(followup.answer)
    add("Sources", "Heading1")
    for index, source in enumerate(sources, 1):
        url = source["url"]
        try:
            parsed = urlsplit(url)
            domain = parsed.hostname
            href = url if parsed.scheme in ("https", "http") and domain else None
        except ValueError:
            domain, href = None, None
        add(f"{index}. {source['title']}", "SourceTitle", href=href)
        # Keep the full address small for print readers; the title and domain link
        # directly to the saved URL in digital copies.
        details = domain or url
        if domain and (parsed.path.strip("/") or parsed.query or parsed.fragment):
            details += "\n" + url
        add(details, "SourceDetails", href=href)
    if not sources:
        add("No sources found.")
    date_line("Research completed", note.researched_at)
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
