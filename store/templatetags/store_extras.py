import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.filter
def highlight(text, query):
    """Wrap the first case-insensitive match of `query` in <mark> tags.
    Escapes everything else to stay safe against injection."""
    text = str(text)
    if not query:
        return escape(text)

    pattern = re.compile(re.escape(query), re.IGNORECASE)
    match = pattern.search(text)
    if not match:
        return escape(text)

    start, end = match.span()
    return mark_safe(
        escape(text[:start])
        + "<mark>" + escape(text[start:end]) + "</mark>"
        + escape(text[end:])
    )
