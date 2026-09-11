import html

from django import template
from django.utils.html import linebreaks
from django.utils.safestring import mark_safe

try:
    import markdown as _markdown
except ImportError:  # pragma: no cover - Markdown is in requirements.txt
    _markdown = None

register = template.Library()


@register.filter(name='markdown')
def render_markdown(text):
    """Render Markdown with any embedded HTML escaped first."""
    if not text:
        return ''
    escaped = html.escape(text, quote=False)
    if _markdown is None:
        return mark_safe(linebreaks(escaped))
    return mark_safe(_markdown.markdown(escaped, extensions=['extra', 'sane_lists']))


@register.filter
def get_item(mapping, key):
    return mapping.get(key) if mapping else None


@register.filter
def compact_number(value):
    """1,284 / 12.9K / 4.2M — for stat tiles."""
    try:
        value = float(value)
    except (TypeError, ValueError):
        return value
    for threshold, suffix in ((1_000_000, 'M'), (10_000, 'K')):
        if abs(value) >= threshold:
            return f"{value / threshold:.1f}".rstrip('0').rstrip('.') + suffix
    return f"{int(value):,}" if value == int(value) else f"{value:,.1f}"
