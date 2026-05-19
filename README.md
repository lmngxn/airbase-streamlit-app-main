# SGN Agentic CRMS

An AI-powered Customer Relationship Management system that automates meeting note-taking, structures business conversations, and extracts actionable intelligence — all through a conversational chat interface.

Future Editions to include research and other CRMS capabilities. 

## What it does (V0.1)

You chat with the system about a meeting you had. A pipeline of specialised AI agents takes over from there:

1. **Collects** meeting details (date, attendees, purpose, key discussion points, decisions, follow-ups)
2. **Formats** the raw notes into a structured, professional report
3. **Extracts** profiles for every person and organisation mentioned
4. **Saves** everything as markdown files to AWS S3

## Architecture

The system uses a multi-agent workflow built on the OpenAI Responses API:

```
User → MainAgent (router)
         ├── CallReportAgent    → collects meeting details
         │     └── FormatReportAgent  → structures the report
         │           └── SavingMeeting      → saves to S3
         │                 └── ExtractInfoAgent   → extracts people & org profiles
         │                       └── SavingPersonOrg    → saves profiles to S3
         └── ResearchAgent (work in progress)
```

Each agent is a focused LLM with its own system prompt, output schema, and routing logic. Agents communicate by passing `previous_response_id` to maintain multi-turn conversation context.

## Tech stack

| Layer | Technology |
|---|---|
| UI | Streamlit |
| LLM | OpenAI (gpt-4.1-mini by default) |
| Storage | AWS S3 |
| Data validation | Pydantic |
| Config | python-dotenv |

## Setup

**Prerequisites:** Python 3.x, an OpenAI API key, AWS credentials with S3 write access.

```bash
# 1. Clone and enter the repo
git clone <repo-url>
cd agentic-crms

# 2. Create a virtual environment
python -m venv venv
source venv/bin/activate       # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
```

Edit `.env` with your credentials:

```env
OPENAI_API_KEY=sk-...

AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_DEFAULT_REGION=ap-southeast-1

# Optional: password-protect the app
PASSWORD=

# Optional: override which models each agent uses
ASSISTANT_MODEL=gpt-4.1-mini
CALL_REPORT_MODEL=gpt-4.1-mini
FORMAT_REPORT_MODEL=gpt-4.1-mini
EXTRACT_INFO_MODEL=gpt-4.1-mini
```

## Running

```bash
streamlit run main.py
```

Opens the app at `http://localhost:8501`.

## Usage

1. Enter the password if one is configured.
2. Tell the assistant what you want to do — e.g. *"Log a meeting I had today"*.
3. Answer the agent's follow-up questions about the meeting.
4. Review and approve the formatted notes and extracted profiles.
5. The system saves everything to S3 and makes the files available to download from the sidebar.

Use the **Reset app** button to clear the session and start fresh.

## Output

All outputs are saved as markdown files:

- **Meeting notes** — structured report with YAML frontmatter, attendees, summary, discussion points, decisions, and follow-ups
- **People profiles** — occupation, interests, personality notes, and connections, with wiki-style `[[links]]` to related profiles
- **Organisation profiles** — company-level intelligence extracted from the same meeting

## Project structure

```
agentic-crms/
├── main.py                    # Streamlit entry point
├── utility.py                 # Shared helpers: config loading, session init
├── requirements.txt
├── .env.example
└── agents/
    ├── main_agent.py          # Router agent
    ├── call_report.py         # Meeting detail collector
    ├── format_report.py       # Report formatter
    ├── extract_info.py        # People & org extractor
    ├── save_meeting_notes.py  # Meeting notes → S3
    ├── save_person_org_notes.py  # Profiles → S3
    ├── store.py               # S3 persistence layer
    └── research.py            # Research agent (WIP)
```
