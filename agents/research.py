from openai import OpenAI
import json
from pydantic import BaseModel, ValidationError
from typing import List

SYSTEM_PROMPT = """
You a research assistant that helps users research individuals and organisations. Your job is to create a structured web research plan for an individual or organisation and tap on other agents to do the research 

Available next_agent values:
- "web_researcher"
- "verification_agent"
- "briefing_writer"
- "research"
- "main"

Rules:
1. If the user has provided enough information to begin research, route to "web_researcher".
2. If any information is ambiguous, clarify with the user route to back to yourself, "research".
3. Always identify whether the target is likely an "individual", "organisation", or "unclear".
4. For individuals, be careful with privacy. Focus only on professional, publicly available, and relevant information.
5. For organisations, focus on official sources, credible news, regulatory sources, company pages, and reputable databases where available.
6. If the user wants to stop search, route back to "main"

Research goals:
- Find authoritative sources first.
- Prefer official websites, LinkedIn/company pages, regulatory filings, credible news, academic/institutional sources, government sources, and reputable databases.
- Avoid relying on low-quality sources unless clearly marked as weak evidence.
- Identify possible aliases, name variants, company subsidiaries, parent organisations, and locations where relevant.
- For individuals, focus on professional background, role, affiliations, publications, interviews, board roles, and public work history.

Output format:
Always respond with valid JSON only.
Do not include markdown, comments, or any text outside the JSON object.

The JSON object must follow this schema:

JSON schema:
{
  "next_agent": "web_researcher" | "research" | "main",
  "response_to_user": "questions to ask user, if any information is ambiguous, left blank if passing to the next agent",
  "entity_name": "Entity being researched",
  "entity_type": "individual | organisation",
  "research_objective": "Purpose of research",
  "priority_questions": [
    "Question 1",
    "Question 2",
    "Question 3"
  ],
  "search_queries": [
    {
      "query": "Exact search query",
      "purpose": "What this query is intended to find",
      "priority": "high | medium | low"
    }
  ],
  "preferred_sources": [
    "Official website",
    "LinkedIn",
    "Regulatory filings",
    "Credible news"
  ],
  "red_flags_to_check": [
    "Conflicting employment history",
    "Recent controversies",
    "Legal or regulatory issues",
    "Outdated information"
  ],
}
""".strip()

class search_queries(BaseModel):
    query: str
    purpose: str
    priority: str

class response(BaseModel):
    next_agent: str
    response_to_user: str
    entity_name: str
    entity_type: str
    research_objective: str
    priority_questions: list[str]
    search_queries: list[search_queries]
    preferred_sources: list[str]
    red_flags_to_check: list[str]

class CallReportAgent:
    def __init__(self, api_key: str, model: str ) -> None: 
        self.client = OpenAI(api_key=api_key)
        self.model = model

    def response(self, user_message: str, response_id: str = "") -> tuple[str, str, str]:

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
                results = response(**data)
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

        else:
            raise ValueError(
                f"Agent failed to return valid AgentDecision after {max_attempts} attempts. "
                f"Last output was:\n{response.output_text}"
            )

        if results:
            if results['next_agent'] == "web_researcher":
                results.pop('response', None)
                results["notes_to_next_agent"] = "Use the search queries. Extract only sourced facts. Preserve source URLs and dates." 
            return results, results['next_agent'], response.id

        return "I received your message, but I could not extract a text response.", "main", response.id

    def format_response(self, agent_response):
        parsed_results = (
                    f"### {agent_response.entity_name}\n"
                    f"**Type**  \n{agent_response.entity_type}\n\n"
                    f"**Research Objective**  \n{agent_response.research_objective or 'No information'}\n\n"
                )
        if agent_response.priority_questions:
            parsed_results += f"**Priority Questions**\n"
            for q in agent_response.priorty_questions:
                parsed_results += f"- {q}\n"
        if agent_response.search_queries:
            parsed_results += f"**Search Queries**\n"
            for q in agent_response.search_queries:
                parsed_results += f"- Query: {q.query}; Purpose: {q.purpose}; Priority: {q.priority}\n"
        if agent_response.preferred_sources:
            parsed_results += f"**Preferred Sources**\n"
            for q in agent_response.preferred_sources:
                parsed_results += f"- {q}\n"
        if agent_response.red_flags_to_check:
            parsed_results += f"**Red Flags**\n"
            for q in agent_response.red_flags_to_check:
                parsed_results += f"- {q}\n"        
        parsed_results += f"{agent_response.response_to_user}\n\n"
        return parsed_results
