import re
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class MeetingNote:
    response: str
    title: str
    date: str
    attendees: List[str]
    attendees_details: List[str]
    raw_notes: str
    summary: str = ""
    details: str = ""
    follow_ups: List[str] = field(default_factory=list)

@dataclass
class Connection:
    name: str
    relationship: str

@dataclass
class Meeting:
    date: str
    title: str

@dataclass
class IndividualNote:
    name: str
    summary: str = ""
    personality: str = ""
    personal: str = ""
    occupation_education: str = ""
    interests: str = ""
    connections: List[Connection] = field(default_factory=list)   
    meeting: Meeting = None

@dataclass
class OrganisationNote:
    name: str
    description: str = ""
    connections: List[Connection] = field(default_factory=list)

# ------------------------------------------------------------------
# Meetings
# ------------------------------------------------------------------

def write_meeting_note(note: MeetingNote) -> str:
    safe_title = _safe_filename(note.title, max_len=50)

    attendees_linked = (
        "\n".join(f"| [[{attendee}]] | {detail} |" for attendee, detail in zip(note.attendees, note.attendees_details))
        if note.attendees
        else "- Not specified"
    )

    attendees_table = f"| Attendee | Details |\n|---|---|\n{attendees_linked}\n" if note.attendees else ""

    follow_ups = _format_bullets(note.follow_ups)

    content = (
        f"---\n"
        f"date: {note.date}\n"
        f"---\n\n"
        f"# {note.title or 'Untitled Meeting'}\n\n"
        f"## Attendees\n"
        f"{attendees_table}\n\n"
        f"## Summary\n"
        f"{note.summary or 'Not specified'}\n\n"
        f"## Details\n"
        f"{note.details or 'Not specified'}\n\n"
        f"## Follow-ups\n"
        f"{follow_ups}\n\n"
        f"## Raw Notes / Source Details\n"
        f"{note.raw_notes or 'Not specified'}\n"
    )

    return safe_title, content

# ------------------------------------------------------------------
# Individuals
# ------------------------------------------------------------------

def write_individual_note(note: IndividualNote) -> str:
    safe_name = _safe_filename(note.name)

    content = _render_individual(note)
    return safe_name, content

# ------------------------------------------------------------------
# Organisations
# ------------------------------------------------------------------

def write_organisation_note(note: OrganisationNote) -> str:
    safe_name = _safe_filename(note.name)

    connection_rows = "".join(
        f"| [[{connection.name}]] | {connection.relationship} |\n"
        for connection in note.connections
    )
    content = (
        f"---\n"
        f"Organisation: {note.name}\n"
        f"---\n"
        f"## Description\n"
        f"{note.description or ''}\n\n"
        f"## Connections\n"
        f"| Person | Relationship |\n|---|---|\n"
        f"{connection_rows}\n"
    )
    return safe_name, content


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_filename(value: str, max_len: int = 50) -> str:
    value = value.strip()
    value = re.sub(r'[\\/:*?"<>|]', "", value)
    value = re.sub(r"\s+", " ", value)
    return value[:max_len].strip() or "Untitled Meeting"


def _format_bullets(items: list[str]) -> str:
    if not items:
        return "- Not specified"
    return "\n".join(f"- {item}" for item in items if item.strip()) or "- Not specified"

def _render_individual(note: IndividualNote) -> str:
    connections_rows = "".join(
        f"| [[{connection.name}]] | {connection.relationship} |\n" for connection in note.connections
    )
    conn_table = "| Person | Relationship |\n|---|---|\n" + connections_rows

    meeting_link = f"[[{_safe_filename(note.meeting.title, 50)}]]"
    meeting_row = f"| {note.meeting.date} | {meeting_link} |"
    meetings_table = f"| Date | Title/Link |\n|---|---|\n{meeting_row}\n"

    return (
        f"---\n"
        f"name: {note.name}\n"
        f"---\n"
        f"## Profile\n"
        f"### Personal\n{note.personal}\n\n"
        f"### Occupation / Education\n{note.occupation_education}\n\n"
        f"## Interests\n{note.interests}\n\n"
        f"## Connections\n{conn_table}\n"
        f"## Underlying Personality\n{note.personality}\n\n"
        f"## Meetings\n{meetings_table}"
    )



