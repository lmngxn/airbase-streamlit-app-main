from openai import OpenAI
import json
from pydantic import BaseModel, ValidationError
from typing import List

SYSTEM_PROMPT = """
You are a professional information extractor for people and organisations.

Your task is to extract structured profiles for all clearly identifiable people and organisations mentioned in raw text, reports, or meeting notes.

Return valid JSON only.
Do not include markdown, comments, or explanations outside the JSON object.

Core rules:
- Extract multiple people if more than one person has meaningful information.
- Extract multiple organisations if more than one organisation has meaningful information.
- Create one profile per person and one profile per organisation.
- Do not invent missing facts.
- Do not infer beyond what is stated.
- Preserve important details and nuance from the source.
- Do not over-summarise.
- Use "Unclear" for ambiguous or contradictory information.
- If the same person or organisation appears multiple times, merge the information into one profile.
- If names are incomplete, use the most complete version available.
- Do not create a full profile for a person or organisation mentioned only in passing, unless meaningful details are provided.
- People mentioned only as relationships should appear under "connections", not necessarily as separate people profiles.
- Organisations mentioned only as affiliations should appear under the relevant person, but should also be included under "organisations" if there is meaningful information about the organisation itself.

Extraction workflow:
1. Read the full input.
2. Identify all people and organisations mentioned.
3. Decide which people should have their own profile.
4. Decide which organisations should have their own profile.
5. Merge repeated mentions of the same person or organisation.
6. Extract factual details into the required fields.
7. Return one complete JSON object.

Revision rule:
If the user requests edits after the first draft:
1. Apply the requested edits directly.
2. Preserve unchanged information from the previous JSON.
3. Return the complete updated JSON object.
4. Use the "response" field to briefly confirm the update.

For each person, extract:
- name: Full name of the individual.
- occupation_education: Role, company, occupation, or educational background.
- interests: Topics, hobbies, professional interests, or areas they engaged with.
- personality: Personality traits or behavioural observations explicitly mentioned.
- personal: Other personal details mentioned.
- connections: People they are connected to and the relationship or context.
- meetings: Meeting dates and titles where the person was mentioned.

For each organisation, extract:
- name: Name of the organisation.
- description: Description, purpose, role, industry, or relevant context of the organisation.
- connections: People associated with the organisation and their relationship to it.

Return exactly one JSON object using this schema:

{
  "response": "Check with the user is the information is accurate and whether they would like any edits. If this is a revision, briefly confirm the update. If the output is ready to be saved, output only the word SAVE in uppercase.",
  "people": [
    {
      "name": "Full name of the individual",
      "occupation_education": "Role, company, occupation, or educational background",
      "interests": "Topics, hobbies, professional interests, or areas they engaged with",
      "personality": "Personality traits or behavioural observations explicitly mentioned",
      "others": "Other personal details mentioned",
      "connections": [
        {
          "name": "Connected person's name",
          "relationship": "Relationship or context"
        }
      ],
      "meeting": {"date": "Meeting date", "title": "Meeting title"}
    }
  ],
  "organisations": [
    {
      "name": "Name of the organisation",
      "description": "Description, purpose, role, industry, or relevant context of the organisation",
      "connections": [
        {
          "name": "Associated person's name",
          "relationship": "Person's relationship to the organisation"
        }
      ]
    }
  ]
}
""".strip()

class Meeting(BaseModel):
    date: str
    title: str

class Connection(BaseModel):
    name: str
    relationship: str

class Person(BaseModel):
    name: str
    occupation_education: str = ""
    interests: str = ""
    personality: str = ""
    others: str = ""
    summary: str = ""
    connections: List[Connection] = []
    meeting: Meeting = None

class Organisation(BaseModel):
    name: str
    description: str = ""
    connections: List[Connection] = []

class ExtractionReport(BaseModel):
    response: str
    people: List[Person] = []
    organisations: List[Organisation] = []

class ExtractInfoAgent:
    def __init__(self, api_key: str, model: str ) -> None: 
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def response(self, user_message: str, response_id: str = "") -> tuple[ExtractionReport, str, str]:

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
                results = ExtractionReport(**data)
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

        return results, "extract_info", response.id
    
    def format_response(self, agent_response):
        parsed_results = ""
        if agent_response.people:
            for person in agent_response.people:
                parsed_results += (
                    f"### {person.name}\n"
                    f"**Occupation / Education**  \n{person.occupation_education or 'No information'}\n\n"
                    f"**Interests**  \n{person.interests or 'No information'}\n\n"
                    f"**Personality**  \n{person.personality or 'No information'}\n\n"
                    f"**Other Info**  \n{person.others or 'No information'}\n\n"
                    "---\n"
                )
        if agent_response.organisations:
            for org in agent_response.organisations:
                parsed_results += (
                    f"### {org.name}\n"
                    f"**Description**  \n{org.description or 'No information'}\n\n"
                    "---\n"
                )
        if agent_response.response:
            parsed_results += f"{agent_response.response}\n\n"
        return parsed_results