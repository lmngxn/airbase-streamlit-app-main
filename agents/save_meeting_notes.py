import re
from typing import List
from dataclasses import dataclass, field
from agents.store import SavingAgent

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

class SavingMeeting:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str ) -> None: 
        self.agent = SavingAgent(aws_access_key_id, aws_secret_access_key, region_name)

# ------------------------------------------------------------------
# Meetings
# ------------------------------------------------------------------

    def response(self, note: MeetingNote, id: str) -> str:
        safe_title = _safe_filename(note['title'], max_len=50)

        attendees_linked = (
            "\n".join(f"| [[{attendee}]] | {detail} |" for attendee, detail in zip(note['attendees'], note['attendees_details']))
            if note['attendees']
            else "- Not specified"
        )

        attendees_table = f"| Attendee | Details |\n|---|---|\n{attendees_linked}\n" if note['attendees'] else ""

        follow_ups = _format_bullets(note['follow_ups'])

        content = (
            f"---\n"
            f"date: {note['date']}\n"
            f"---\n\n"
            f"# {note['title'] or 'Untitled Meeting'}\n\n"
            f"## Attendees\n"
            f"{attendees_table}\n\n"
            f"## Summary\n"
            f"{note['summary'] or 'Not specified'}\n\n"
            f"## Details\n"
            f"{note['details'] or 'Not specified'}\n\n"
            f"## Follow-ups\n"
            f"{follow_ups}\n\n"
            f"## Raw Notes / Source Details\n"
            f"{note['raw_notes'] or 'Not specified'}\n"
        )

        self.agent.save_notes(content, safe_title, "notes")

        response = {
            "safe_title": safe_title, 
            "content":content, 
            "next_agent":"extract_info", 
            "context_to_next_agent":f"Please extract information on people or organisations from this report\n" + content,
            "response_to_user": "The formatted meeting notes has been generated. Please see the left section of the window. We will go on to extract information about individuals and organisations",
        }

        return response , ""

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





