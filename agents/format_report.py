from openai import OpenAI
import json
from pydantic import BaseModel, ValidationError
from typing import List

SYSTEM_PROMPT = """
You are a professional meeting-summary formatter.

Your job is to convert extracted meeting information or raw meeting notes into a structured meeting report for the user to review.

Return valid JSON only.
Do not include markdown, comments, or explanations outside the JSON object.

Available agents:

1. main
Use this when:
- The user no longer wants to log or create the meeting report.
- The user asks to stop, cancel, exit, or want to do something unrelated to meeting notes.
- The request should be handled by the main assistant instead.

2. format_report
Use this when:
- You need to continue asking the user questions.
- The user has more meeting information to add to the report.
- You need more details before the report can be saved.

3. save_meeting
Use this when:
- The user has confirmed that the formatted report is ready to be saved

Core rules:
- Do not invent missing facts.
- Do not drop important details.
- Do not over-summarise the raw notes.
- Preserve names, dates, numbers, tools, systems, organisations, examples, decisions, constraints, and follow-up actions.
- Use "Unclear" for ambiguous or contradictory information.

Workflow:
1. Read all extracted meeting information or raw notes.
2. Identify the meeting title, date, attendees, purpose, key discussions, decisions, follow-ups, and raw source details.
3. Group related information into clear sections.
4. Convert messy or fragmented notes into readable prose and bullet points.
5. Preserve the original meaning and nuance.
6. Return the report using the required JSON schema.
7. In the "response" field, ask the user whether they would like any edits.

Revision rule:
If the user requests edits after the first draft:
1. Apply the requested edits directly.
2. Preserve all unchanged information from the previous report.
3. Return the complete updated JSON object.
4. Use the "response" field to briefly confirm the update.

Report content requirements:
- Title: concise meeting title, 5–10 words.
- Date: meeting date in YYYY-MM-DD format if known; otherwise "Not specified".
- Attendees: list of attendee names. Include roles or organisations if provided.
- Summary: 2-3 sentences to highlight the key discussion points or outcomes.
- Details: organised sections with headings. Include all important discussion points, context, people mentioned, tools, systems, issues, decisions, and constraints. No follow-ups, as they should be in the next section.
- Follow-ups: next steps, including owner and deadline where available.
- Raw Notes / Source Details: comprehensive cleaned narrative of the original source information.

Output schema:
Return exactly one JSON object with this structure:

{
  "response_to_user": "Short message to the user. After the first draft, ask whether they would like any edits. If this is a revision, briefly confirm the update. 
  "title": "Concise meeting title, 5–10 words",
  "date": "YYYY-MM-DD or Not specified",
  "attendees": ["Name"],
  "attendees_details": ["Role, organisation, or Not specified"],
  "summary": "2-3 sentences to describe the overall meeting.",
  "details": "Organised sections with headings in already markup format."
  "follow_ups": ["Action item, including owner and deadline if available."],
  "raw_notes": "Comprehensive cleaned narrative of the original source notes."
  "next_agent": format_report | save_meeting | main
  "context_to_next_agent": "instructions to the next agent, if any, from the user"
}
""".strip()

class MeetingNote(BaseModel):
    response_to_user: str
    title: str
    date: str
    attendees: List[str]
    attendees_details: List[str]
    raw_notes: str
    summary: str = ""
    details: str = ""
    follow_ups: List[str] = []
    next_agent: str
    context_to_next_agent: str

class FormatReportAgent:
    def __init__(self, api_key: str, model: str ) -> None: 
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def response(self, user_message: str, response_id: str = "") -> tuple[MeetingNote, str, str]:

        if response_id:
            response = self.client.responses.create(
                model=self.model,
                input=user_message,
                previous_response_id=response_id,
                store=True,
                instructions=SYSTEM_PROMPT,
            )
        else:
            response = self.client.responses.create(
                model=self.model,
                input=user_message,
                store=True,
                instructions=SYSTEM_PROMPT,
            )
      
        max_attempts = 3
        attempt = 0

        while attempt < max_attempts:
            attempt += 1
            try:
                data = json.loads((response.output_text).strip())
                results = MeetingNote(**data)
                break
            
            except json.JSONDecodeError as e:
                response = self.client.responses.create(
                    model=self.model,
                    input='Output was not in JSON format. Please strictly follow the output format and only respond with the JSON object as specified in the instructions. ' \
                    'Do not include any text outside the JSON object.',
                    previous_response_id=response.id,
                    store=True,
                    instructions=SYSTEM_PROMPT,
                )
                print(f"Agent output is not valid JSON: {e}. Retrying...")
                continue
            
            except ValidationError as e:
                response = self.client.responses.create(
                    model=self.model,
                    input='Output was not correct schema. Please strictly follow the output format and ensure the JSON object matches the specified schema in the instructions.' \
                    'Do not include any text outside the JSON object.',
                    previous_response_id=response.id,
                    store=True,
                    instructions=SYSTEM_PROMPT,
                )
                print(f"Agent output does not match schema: {e}. Retrying...")
                continue
        
        else:
            raise ValueError(
                f"Agent failed to return valid AgentDecision after {max_attempts} attempts. "
                f"Last output was:\n{response.output_text}"
            )

        return data, response.id

    def format_response(self, agent_response):
        parsed_results = (
                        f"Date: {agent_response['date']}\n\n"
                        f"Title: {agent_response['title'] or 'Untitled Meeting'}\n\n"
                        f"Attendees:\n"
                        f"{('\n'.join(f'- {attendee} ({details})' for attendee, details in zip(agent_response['attendees'], agent_response['attendees_details'])))}\n\n"
                        f"Summary:\n"
                        f"\n{agent_response['summary'] or 'Not specified'}\n\n"
                        f"Details:\n"
                        f"\n{agent_response['details'] or 'Not specified'}\n\n"
                        f"Follow-ups:\n"
                        f"{'\n'.join(f'- {follow_up}' for follow_up in agent_response['follow_ups'])}\n\n"
                        f"---\n"
                        f"{agent_response['response_to_user']}\n\n"                
                    )
        return parsed_results

