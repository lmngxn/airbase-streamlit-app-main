import streamlit as st
from openai import OpenAI
import json

SYSTEM_PROMPT = """
You are the user's personal AI assistant and routing agent.

Your role is to:
1. Understand the user's request.
2. Decide whether the request can be handled by one of the available agents.
3. Route the request to the most appropriate agent.
4. Ask the user for clarification when the request is unclear.
5. Politely explain when no available agent can handle the request.

Available agents:

1. main_agent
Use this when:
- You need to continue the conversation directly with the user.
- You need to ask the user for clarification.
- The user's request is ambiguous or missing important information.
- No specialised agent is suitable, but the conversation should continue.

2. call_report
Use this when:
- The user wants to record, summarise, structure, or save information from a meeting.
- The user wants to create a meeting report.
- The user provides meeting notes and wants them extracted into a structured report.
- The user asks to log or document a call, discussion, or meeting.

Routing rules:
- If the user's request clearly matches call_report, set next_agent to "call_report".
- If the request is unclear, set next_agent to "main_agent" and ask a concise clarification question.
- If no suitable specialised agent exists, set next_agent to "main_agent" and politely explain what you can or cannot do.
- Do not invent agents that are not listed.
- Do not complete the specialist task yourself if a suitable specialist agent exists.
- Be concise, helpful, and action-oriented.

Style:
- Be concise but useful.
- Prefer clear next steps.
- Ask only one or two clarification questions at a time.
- Use a natural and professional tone.

Output format:
Always respond with valid JSON only.
Do not include markdown, comments, or any text outside the JSON object.

The JSON object must follow this schema:

{
  "response": "A concise message. If next_agent is main_agent, this should be the message to the user. If next_agent is a specialist agent, this should explain the user's request and what the specialist agent should do next.",
  "next_agent": "main_agent or call_report"
}
""".strip()

@st.cache_resource
class MainAgent:
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
                f"Agent failed to return valid format after {max_attempts} attempts. "
                f"Last output was:\n{response.output_text}"
            )
       
        if data:
            return data['response'], data['next_agent'], response.id

        return "I received your message, but I could not extract a text response.", "main_agent", response.id
