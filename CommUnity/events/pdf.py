"""Render a post-event report as a formatted A4 PDF."""

import re
from io import BytesIO
from xml.sax.saxutils import escape

from django.conf import settings
from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import ListFlowable, ListItem, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

INK = colors.HexColor('#0f2233')
BRAND = colors.HexColor('#003459')
ACCENT = colors.HexColor('#007EA7')
MUTED = colors.HexColor('#5b6b7b')
RULE = colors.HexColor('#d9e2ec')
TINT = colors.HexColor('#f1f6fa')


def _styles():
    base = getSampleStyleSheet()
    return {
        'eyebrow': ParagraphStyle('eyebrow', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=8.5,
                                  textColor=ACCENT, spaceAfter=4, leading=11),
        'title': ParagraphStyle('title', parent=base['Title'], fontName='Helvetica-Bold', fontSize=21,
                                textColor=BRAND, alignment=0, spaceAfter=2, leading=25),
        'subtitle': ParagraphStyle('subtitle', parent=base['Normal'], fontSize=11, textColor=MUTED, spaceAfter=12),
        'h2': ParagraphStyle('h2', parent=base['Heading2'], fontName='Helvetica-Bold', fontSize=12.5,
                             textColor=BRAND, spaceBefore=12, spaceAfter=5),
        'h3': ParagraphStyle('h3', parent=base['Heading3'], fontName='Helvetica-Bold', fontSize=11,
                             textColor=INK, spaceBefore=8, spaceAfter=4),
        'body': ParagraphStyle('body', parent=base['BodyText'], fontSize=10.5, leading=15.5, textColor=INK,
                               spaceAfter=6),
        'label': ParagraphStyle('label', parent=base['Normal'], fontName='Helvetica-Bold', fontSize=9,
                                textColor=MUTED, leading=12),
        'value': ParagraphStyle('value', parent=base['Normal'], fontSize=10, textColor=INK, leading=13),
    }


def _inline(text):
    text = escape(text)
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'(?<![\*\w])\*(?!\s)(.+?)(?<!\s)\*(?![\*\w])', r'<i>\1</i>', text)
    return text.replace('`', '')


def _markdown_flowables(markdown_text, styles):
    flowables, bullets = [], []

    def flush_bullets():
        if bullets:
            flowables.append(ListFlowable(
                [ListItem(Paragraph(item, styles['body']), leftIndent=14) for item in bullets],
                bulletType='bullet', start='•', leftIndent=14, bulletColor=ACCENT,
            ))
            bullets.clear()

    for raw in markdown_text.splitlines():
        line = raw.strip()
        if not line:
            flush_bullets()
            continue
        if line.startswith('# '):
            flush_bullets()  # the document header already shows the title
            continue
        if line.startswith('### '):
            flush_bullets()
            flowables.append(Paragraph(_inline(line[4:]), styles['h3']))
            continue
        if line.startswith('## '):
            flush_bullets()
            flowables.append(Paragraph(_inline(line[3:]), styles['h2']))
            continue
        bullet = re.match(r'^(?:[-*•]|\d+[.)])\s+(.*)', line)
        if bullet:
            bullets.append(_inline(bullet.group(1)))
            continue
        flush_bullets()
        flowables.append(Paragraph(_inline(line), styles['body']))
    flush_bullets()
    return flowables


def _meta_table(event, data, styles):
    start = timezone.localtime(event.date_time)
    end = timezone.localtime(event.end_time)
    rows = [
        ('Organised by', data.get('organizer') or event.association.name),
        ('Faculty in-charge', event.association.faculty_incharge.id.display_name),
        ('Date', f"{start:%A, %d %B %Y}"),
        ('Time', f"{start:%I:%M %p} – {end:%I:%M %p}"),
        ('Venue', str(event.location)),
        ('Event type', data.get('event_type') or '—'),
        ('Attendance', str(data.get('attendees') or event.registrations.count() or '—')),
        ('Approved by', event.approved_by.id.display_name if event.approved_by else '—'),
    ]
    cells = [[Paragraph(escape(label), styles['label']), Paragraph(escape(str(value)), styles['value'])]
             for label, value in rows]
    # Two label/value pairs per row keep the block compact.
    paired = [cells[i] + (cells[i + 1] if i + 1 < len(cells) else ['', '']) for i in range(0, len(cells), 2)]
    table = Table(paired, colWidths=[28 * mm, 57 * mm, 28 * mm, 57 * mm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), TINT),
        ('BOX', (0, 0), (-1, -1), 0.6, RULE),
        ('LINEBELOW', (0, 0), (-1, -2), 0.4, RULE),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 7),
    ]))
    return table


def build_report_pdf(event, report_text, data=None):
    data = data or {}
    styles = _styles()
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        leftMargin=20 * mm, rightMargin=20 * mm, topMargin=18 * mm, bottomMargin=20 * mm,
        title=f"{event.title} - Event Report", author=event.association.name,
    )
    generated_on = timezone.localtime(timezone.now())

    def draw_footer(canvas, document):
        canvas.saveState()
        canvas.setStrokeColor(RULE)
        canvas.line(20 * mm, 14 * mm, A4[0] - 20 * mm, 14 * mm)
        canvas.setFont('Helvetica', 8)
        canvas.setFillColor(MUTED)
        canvas.drawString(20 * mm, 9.5 * mm, f"{settings.COLLEGE_NAME} · CommUnity · Generated {generated_on:%d %b %Y}")
        canvas.drawRightString(A4[0] - 20 * mm, 9.5 * mm, f"Page {document.page}")
        canvas.restoreState()

    story = [
        Paragraph(escape(f"{settings.COLLEGE_NAME} · {event.association.name}").upper(), styles['eyebrow']),
        Paragraph(escape(event.title), styles['title']),
        Paragraph("Post-Event Report", styles['subtitle']),
        _meta_table(event, data, styles),
        Spacer(1, 8),
        *_markdown_flowables(report_text, styles),
    ]
    doc.build(story, onFirstPage=draw_footer, onLaterPages=draw_footer)
    return buffer.getvalue()
