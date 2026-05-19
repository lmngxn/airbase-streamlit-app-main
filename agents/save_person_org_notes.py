import re
from typing import List
from dataclasses import dataclass, field
from agents.store import SavingAgent

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

@dataclass
class PeopleOrgLst:
    people: List[IndividualNote]
    organisations: List[OrganisationNote]

class SavingPersonOrg:
    def __init__(self, aws_access_key_id: str, aws_secret_access_key: str, region_name: str ) -> None: 
        self.agent = SavingAgent(aws_access_key_id, aws_secret_access_key, region_name)

# ------------------------------------------------------------------
# Meetings
# ------------------------------------------------------------------

    def response(self, people_org_object: PeopleOrgLst, id: str ) -> str:
        file_name_list = []
        content_list = []

        for person in people_org_object['people']:
            file_name, content = write_individual_note(person)
            self.agent.save_notes(content=content, title=file_name, type="people")
            file_name_list.append(file_name)
            content_list.append(content)

        for org in people_org_object['organisations']:
            file_name, content = write_organisation_note(org)
            self.agent.save_notes(content=content, title=file_name, type="organisations")
            file_name_list.append(file_name)
            content_list.append(content)

        response = {
            "safe_titles": file_name_list,
            "contents":content_list,
            "next_agent":"main", 
            "context_to_next_agent":"User has completed recording the meeting. Please start a new conversation with the user.",
            "response_to_user": "The people and organisation notes have been generated. Please see the left section of the window.",
        }

        return response, ""

# ------------------------------------------------------------------
# Individuals
# ------------------------------------------------------------------

def write_individual_note(note: IndividualNote) -> str:
    safe_name = _safe_filename(note['name'])

    content = _render_individual(note)
    return safe_name, content

# ------------------------------------------------------------------
# Organisations
# ------------------------------------------------------------------

def write_organisation_note(note: OrganisationNote) -> str:
    safe_name = _safe_filename(note['name'])

    connection_rows = "".join(
        f"| [[{connection['name']}]] | {connection['relationship']} |\n"
        for connection in note['connections']
    )
    content = (
        f"---\n"
        f"Organisation: {note['name']}\n"
        f"---\n"
        f"## Description\n"
        f"{note['description'] or ''}\n\n"
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


def _render_individual(note: IndividualNote) -> str:
    connections_rows = "".join(
        f"| [[{connection['name']}]] | {connection['relationship']} |\n" for connection in note['connections']
    )
    conn_table = "| Person | Relationship |\n|---|---|\n" + connections_rows

    meeting_link = f"[[{_safe_filename(note['meeting']['title'], 50)}]]"
    meeting_row = f"| {note['meeting']['date']} | {meeting_link} |"
    meetings_table = f"| Date | Title/Link |\n|---|---|\n{meeting_row}\n"

    return (
        f"---\n"
        f"name: {note['name']}\n"
        f"---\n"
        f"# Profile\n"
        f"## Occupation / Education\n{note['occupation_education']}\n\n"
        f"# Interests\n{note['interests']}\n\n"
        f"# Connections\n{conn_table}\n"
        f"# Underlying Personality\n{note['personality']}\n\n"
        f"# Other Information\n{note['others']}\n\n"
        f"# Meetings\n{meetings_table}"
    )



