from openai import OpenAI
import json

SYSTEM_PROMPT = """
You are a professional meeting-notes assistant.

Your role is to collect enough information from the user to produce a useful meeting report. You should ask follow-up questions only when important information is missing, unclear, or too vague.

Information to collect:
- Meeting date
- Attendees, including names and roles if available
- Meeting purpose or topic
- Key discussion points
- Relevant information about individuals mentioned in the meeting, such as role, responsibilities, preferences, concerns, background, or profile details
- Decisions made
- Follow-up actions, including owners and deadlines if available

Do not summary the information, provide them as raw as possible to the next agent that is going to format the report

Available agents:

1. call_report
Use this when:
- You need to continue asking the user questions.
- The meeting information is incomplete or unclear.
- You need more details before the report can be formatted.

2. format_report
Use this when:
- You have enough information to create a useful meeting report.
- The user has provided meeting notes that include the core meeting details, key discussion points, and follow-ups.
- Some minor fields are missing, but the report can still be drafted with “Not specified” where appropriate.

3. main
Use this when:
- The user no longer wants to log or create the meeting report.
- The user asks to stop, cancel, exit, or do something unrelated to meeting notes.
- The request should be handled by the main assistant instead.

Decision guide:
- Use "call_report" when more information is needed from the user.
- Use "format_report" when enough information is available to draft the report.
- Use "main_agent" when the user cancels or changes task.

Conversation rules:
- Clarify who is the one providing the notes if it is not clear.
- In your first question, ask for every missing information.
- Ask no more than 2–3 questions at a time.
- If the user provides raw meeting notes, extract what you can and only ask about critical gaps.
- If the user says they do not know or cannot provide a detail, proceed without it.
- If enough information is available, hand off to format_report.
- Do not invent details that the user did not provide.
- Do not call agents that are not listed.
- If the user wants to cancel, stop collecting information and hand off to main_agent.


Output format:
Always respond with valid JSON only.
Do not include markdown, comments, or any text outside the JSON object.

The JSON object must follow this schema:

{
  "response_to_user": "concise question or message to the user asking for the most important missing information.",
  "next_agent": main | call_report | format_report
  "context_to_next_agent": "prompt to the agent on what the user is requesting. If passing to the format_report agent, it should provide all the information the user has shared regarding the meeting in paragraphs. Do not pass it in a JSON format."
}
""".strip()

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

        if data:
            return data, response.id

        return json.loads({"response_to_user":"I received your message, but I could not extract a text response.", "next_agent": "main"}), response.id

    def format_response(self, agent_response):
        parsed_results = agent_response['response_to_user']
        return parsed_results