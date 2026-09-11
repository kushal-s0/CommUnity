"""
Generative-AI drafting of post-event reports.

Claude is the primary provider. Hugging Face Inference Providers remains as an
alternative, and an offline template guarantees a usable draft when no provider
is configured or the API can't be reached. The organiser always reviews and can
edit the draft before it becomes the official report.
"""

import logging

import requests
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger(__name__)

# Models that support server-side refusal fallbacks ("fallbacks": "default").
FALLBACK_CAPABLE_MODELS = {'claude-opus-5', 'claude-fable-5-1'}

SYSTEM_PROMPT = """You write formal post-event reports for student clubs and committees at {college}. \
The reports are submitted to faculty and kept in the institution's records, so they must be accurate: \
use only the facts provided and never invent names, numbers, quotes or outcomes. When a detail is \
missing, leave it out instead of guessing.

Write the report in Markdown with these sections, in this order:
# <Event title> - Event Report
## Overview
## Objectives
## Proceedings
## Speakers and Contributions   (omit this section when no speakers are given)
## Participation
## Outcomes and Impact
## Conclusion

Use the third person and past tense in a formal, academic register. Prefer short paragraphs; use \
bullet points only for lists of speakers, activities or outcomes. Aim for 400-700 words. Output only \
the report."""


class ReportGenerationError(Exception):
    pass


def event_facts(event, data):
    start = timezone.localtime(event.date_time)
    end = timezone.localtime(event.end_time)
    registered = event.registrations.count()
    attended = event.registrations.filter(attended=True).count()
    facts = [
        ("Event title", event.title),
        ("Organised by", data.get('organizer') or event.association.name),
        ("Club / committee", f"{event.association.name} ({event.association.get_type_display()})"),
        ("Faculty in-charge", event.association.faculty_incharge.id.display_name),
        ("Event type", data.get('event_type')),
        ("Date", f"{start:%A, %d %B %Y}"),
        ("Time", f"{start:%I:%M %p} to {end:%I:%M %p}"),
        ("Venue", str(event.location)),
        ("Description", event.description),
        ("Number of attendees", data.get('attendees')),
        ("Online registrations", registered or None),
        ("Attendance marked on CommUnity", attended or None),
        ("Speakers / guests", data.get('speakers')),
        ("Agenda and proceedings", data.get('agenda')),
        ("Highlights", data.get('highlights')),
        ("Outcomes", data.get('outcomes')),
        ("Participant feedback", data.get('feedback')),
        ("Photo / video links", data.get('media_links')),
    ]
    return [(label, value) for label, value in facts if value not in (None, '')]


def build_prompt(event, data):
    lines = [f"{label}: {value}" for label, value in event_facts(event, data)]
    return "Write the post-event report for this event.\n\n" + "\n".join(lines)


def _system_prompt():
    return SYSTEM_PROMPT.format(college=settings.COLLEGE_NAME)


def _generate_with_anthropic(prompt):
    try:
        import anthropic
    except ImportError as exc:
        raise ReportGenerationError("The 'anthropic' package isn't installed. Run: pip install anthropic") from exc

    client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY or None, timeout=180.0)
    request = {
        'model': settings.AI_MODEL,
        'max_tokens': 16000,
        'system': _system_prompt(),
        'messages': [{'role': 'user', 'content': prompt}],
    }
    try:
        if settings.AI_MODEL in FALLBACK_CAPABLE_MODELS:
            # If a safety classifier declines, the API re-runs the request on
            # Anthropic's recommended fallback model instead of refusing.
            response = client.beta.messages.create(
                betas=['server-side-fallback-2026-07-01'],
                fallbacks='default',
                **request,
            )
        else:
            response = client.messages.create(**request)
    except anthropic.AuthenticationError as exc:
        raise ReportGenerationError("Claude rejected the API key. Check ANTHROPIC_API_KEY.") from exc
    except anthropic.RateLimitError as exc:
        raise ReportGenerationError("Claude is rate-limiting requests. Try again in a minute.") from exc
    except anthropic.APIStatusError as exc:
        raise ReportGenerationError(f"Claude API error ({exc.status_code}): {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise ReportGenerationError("Couldn't reach the Claude API. Check the internet connection.") from exc
    except anthropic.AnthropicError as exc:
        raise ReportGenerationError(f"Claude request failed: {exc}") from exc

    if response.stop_reason == 'refusal':
        raise ReportGenerationError("Claude declined to write this report.")
    text = ''.join(block.text for block in response.content if block.type == 'text').strip()
    if not text:
        raise ReportGenerationError("Claude returned an empty report.")
    return text


def _generate_with_huggingface(prompt):
    try:
        response = requests.post(
            'https://router.huggingface.co/v1/chat/completions',
            headers={'Authorization': f'Bearer {settings.HUGGINGFACE_API_KEY}'},
            json={
                'model': settings.HUGGINGFACE_MODEL,
                'messages': [
                    {'role': 'system', 'content': _system_prompt()},
                    {'role': 'user', 'content': prompt},
                ],
                'max_tokens': 1800,
            },
            timeout=120,
        )
    except requests.RequestException as exc:
        raise ReportGenerationError(f"Couldn't reach Hugging Face: {exc}") from exc
    if response.status_code != 200:
        raise ReportGenerationError(f"Hugging Face API error ({response.status_code}): {response.text[:200]}")
    try:
        text = response.json()['choices'][0]['message']['content'].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise ReportGenerationError("Unexpected response format from Hugging Face.") from exc
    if not text:
        raise ReportGenerationError("Hugging Face returned an empty report.")
    return text


def _bullets(text):
    items = [line.strip(' -•*\t') for line in str(text).splitlines() if line.strip(' -•*\t')]
    return '\n'.join(f"- {item}" for item in items)


def generate_from_template(event, data):
    """Offline draft assembled from the organiser's own inputs."""
    start = timezone.localtime(event.date_time)
    end = timezone.localtime(event.end_time)
    association = event.association
    organizer = data.get('organizer') or association.name
    event_type = (data.get('event_type') or 'event').strip()
    attendees = data.get('attendees')

    parts = [
        f"# {event.title} - Event Report",
        "## Overview",
        f"{organizer} organised “{event.title}”, a {event_type.lower()}, on {start:%A, %d %B %Y} "
        f"from {start:%I:%M %p} to {end:%I:%M %p} at {event.location}. The event was conducted under "
        f"the guidance of {association.faculty_incharge.id.display_name}, faculty in-charge of {association.name}.",
        "## Objectives",
        event.description,
        "## Proceedings",
        _bullets(data['agenda']) if data.get('agenda') else "The event was conducted as planned.",
    ]
    if data.get('speakers'):
        parts += ["## Speakers and Contributions", _bullets(data['speakers'])]
    participation = f"The event was attended by {attendees} participants." if attendees else ''
    registered = event.registrations.count()
    if registered:
        participation += f" {registered} students registered through CommUnity."
    if participation:
        parts += ["## Participation", participation.strip()]
    if data.get('highlights'):
        parts += ["### Highlights", _bullets(data['highlights'])]
    if data.get('outcomes'):
        parts += ["## Outcomes and Impact", _bullets(data['outcomes'])]
    if data.get('feedback'):
        parts += ["### Participant Feedback", data['feedback']]
    parts += [
        "## Conclusion",
        f"“{event.title}” was successfully conducted by {association.name}. The organising team thanks "
        f"the faculty in-charge, speakers and participants for their support and involvement.",
    ]
    if data.get('media_links'):
        parts += ["### Media", _bullets(data['media_links'])]
    return '\n\n'.join(parts)


def active_provider():
    provider = settings.AI_PROVIDER
    if provider == 'auto':
        if settings.ANTHROPIC_API_KEY:
            return 'anthropic'
        if settings.HUGGINGFACE_API_KEY:
            return 'huggingface'
        return 'template'
    return provider


def generate_report(event, data):
    """
    Draft a report for `event` from the organiser's form `data`.

    Returns (markdown_text, provider_label, warning). `warning` explains why the
    offline template was used when an AI provider was configured but failed.
    """
    provider = active_provider()
    prompt = build_prompt(event, data)
    warning = None
    try:
        if provider == 'anthropic':
            return _generate_with_anthropic(prompt), f"Claude ({settings.AI_MODEL})", None
        if provider == 'huggingface':
            return _generate_with_huggingface(prompt), f"Hugging Face ({settings.HUGGINGFACE_MODEL})", None
    except ReportGenerationError as exc:
        logger.warning("AI report generation failed for event %s: %s", event.pk, exc)
        warning = str(exc)
    return generate_from_template(event, data), 'CommUnity template', warning
