import streamlit as st
import boto3
import os
import json
from utility import check_password
from agents.main_agent import MainAgent
from agents.call_report import CallReportAgent
from agents.format_report import FormatReportAgent
from agents.extract_info import ExtractInfoAgent
from agents.writer import write_meeting_note, write_individual_note, write_organisation_note
import logging
from dotenv import load_dotenv

from datetime import datetime, timezone, timedelta

# region <--------- Streamlit Page Configuration --------->

st.set_page_config(
    layout="centered",
    page_title="SGN Agentic CRMS"
)

# Do not continue if valid_password is not True.
if not check_password():
    st.stop()

load_dotenv()

SGT = timezone(timedelta(hours=8))
S3_BUCKET_ENV="user-corrections"
AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID", "")
AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY", "")
AWS_DEFAULT_REGION=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")
openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
assistant_model = os.getenv("ASSISTANT_MODEL", "gpt-4.1-mini").strip()
call_report_model = os.getenv("CALL_REPORT_MODEL", "gpt-4.1-mini").strip()
format_report_model = os.getenv("FORMAT_REPORT_MODEL", "gpt-4.1-mini").strip()
extract_info_model = os.getenv("EXTRACT_INFO_MODEL", "gpt-4.1-mini").strip()
DEFAULT_S3_PREFIX="agentic-crms"

@st.cache_resource
def get_s3_client():
    return boto3.client(
                "s3",
                aws_access_key_id=AWS_ACCESS_KEY_ID,
                aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
                region_name=AWS_DEFAULT_REGION,
            )

s3_client = get_s3_client()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)

logger = logging.getLogger(__name__)

def save_chat_logs():
    """
    Saves the entire current chat session to S3.
    This overwrites the same session file each time.
    """
    s3_key = f"{DEFAULT_S3_PREFIX}/logs/{datetime.now(SGT).isoformat()}.json"

    s3_client.put_object(
        Bucket=S3_BUCKET_ENV,
        Key=s3_key,
        Body=json.dumps(st.session_state.messages, ensure_ascii=False, indent=2),
        ContentType="application/json",
    )

def save_notes(content: str, title: str, type: str):
    """
    Saves the entire current chat session to S3.
    This overwrites the same session file each time.
    """
    s3_key = f"{DEFAULT_S3_PREFIX}/{type}/{title}_{datetime.now(SGT).isoformat()}.md"

    s3_client.put_object(
        Bucket=S3_BUCKET_ENV,
        Key=s3_key,
        Body=content,
        ContentType="text/markdown",
    )

# endregion <--------- Streamlit Page Configuration --------->

st.title("SGN Agentic CRMS")

if st.button("Reset app"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()

# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    st.session_state.messages.append({
        "role": "assistant",
        "content": f"Hi — I am your personal AI assistant v0.1.\n\nCurrently, here are my existing capabilities:\n1. log call report and then format and extract information\n2. (Work in progress) research on a topic and save the research notes in markdown format\n\n",
        "timestamp": datetime.now(SGT).isoformat()
    })

if "downloads" not in st.session_state:
    st.session_state.downloads = []

if "state" not in st.session_state:
    st.session_state.state = {
        "flag": "main_agent",
    }

main_agent = MainAgent(api_key=openai_api_key, model=assistant_model)
call_report_agent = CallReportAgent(api_key=openai_api_key, model=call_report_model)
format_report_agent = FormatReportAgent(api_key=openai_api_key, model=format_report_model)
extract_info_agent = ExtractInfoAgent(api_key=openai_api_key, model=extract_info_model)

if "agents" not in st.session_state:
    st.session_state.agents = {
        "main_agent": main_agent,
        "call_report": call_report_agent,
        "format_report": format_report_agent,
        "extract_info": extract_info_agent,
    }

if "response_id" not in st.session_state:
    st.session_state.response_id = {
        "main_agent": "",
        "call_report": "",
        "format_report": "",
        "extract_info": "",
    }

#Display files that can be downloaded
with st.sidebar:
    st.subheader("Generated Files")

    if not st.session_state.downloads:
        st.caption("No files generated yet.")
    else:
        for i, file in enumerate(st.session_state.downloads):
            st.download_button(
                label=file["label"],
                data=file["data"],
                file_name=file["file_name"],
                mime=file["mime"],
                key=f"sidebar_download_{i}",
            )

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])


# Chat input
user_input = st.chat_input("Type your message here...")

if user_input:
    # Save and display user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now(SGT).isoformat()
    })

    with st.chat_message("user"):
        st.write(user_input)

    # put a placeholder and call the agent to get response and next agent flag
    with st.chat_message("assistant"):
        placeholder = st.empty()

        placeholder.markdown("Thinking...")
        agent_response, flag, st.session_state.response_id[st.session_state.state["flag"]] = st.session_state.agents[st.session_state.state["flag"]].response(user_input, st.session_state.response_id[st.session_state.state["flag"]])

        logger.info(agent_response)
        logger.info(flag)
        logger.info("response 1")

        if st.session_state.state["flag"] != flag:
            st.session_state.response_id[st.session_state.state["flag"]] = ""
            st.session_state.state["flag"] = flag
            agent_response, flag, st.session_state.response_id[flag] = st.session_state.agents[flag].response(agent_response, st.session_state.response_id[flag])
            logger.info(agent_response)
            logger.info(flag)
            logger.info("response 2, change agent")
            if st.session_state.state["flag"] == "format_report":
                parsed_results = (
                    f"Date: {agent_response.date}\n\n"
                    f"Title: {agent_response.title or 'Untitled Meeting'}\n\n"
                    f"Attendees:\n"
                    f"{('\n'.join(f'- {attendee} ({details})' for attendee, details in zip(agent_response.attendees, agent_response.attendees_details)))}\n\n"
                    f"Summary:\n"
                    f"{agent_response.summary or 'Not specified'}\n\n"
                    f"Details:\n"
                    f"{agent_response.details or 'Not specified'}\n\n"
                    f"Follow-ups:\n"
                    f"{'\n'.join(f'- {follow_up}' for follow_up in agent_response.follow_ups)}\n\n"
                    f"---\n"
                    f"{agent_response.response}\n\n"                
                )
            else:
                parsed_results = agent_response
            placeholder.markdown(parsed_results)
            st.session_state.messages.append({
                "role": "assistant",
                "content": parsed_results,
                "timestamp": datetime.now(SGT).isoformat()
            })

        # for formated report, special handling to display the results
        elif flag == 'format_report':
            # to display the result as it is if it is still being checked
            if agent_response.response != "SAVE":
                parsed_results = (
                    f"Date: {agent_response.date}\n\n"
                    f"Title: {agent_response.title or 'Untitled Meeting'}\n\n"
                    f"Attendees:\n"
                    f"{('\n'.join(f'- {attendee} ({details})' for attendee, details in zip(agent_response.attendees, agent_response.attendees_details)))}\n\n"
                    f"Summary:\n"
                    f"{agent_response.summary or 'Not specified'}\n\n"
                    f"Details:\n"
                    f"{agent_response.details or 'Not specified'}\n\n"
                    f"Follow-ups:\n"
                    f"{'\n'.join(f'- {follow_up}' for follow_up in agent_response.follow_ups)}\n\n"
                    f"---\n"
                    f"{agent_response.response}\n\n"                
                )
                placeholder.markdown(parsed_results)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": parsed_results,
                    "timestamp": datetime.now(SGT).isoformat()
                })
                st.session_state.state["flag"] = flag
            # display the results as a file if completed
            else:
                logger.info("save 1, report")
                file_name, content = write_meeting_note(agent_response)
                save_notes(content, file_name, "notes")
                # Add file separately to download box
                st.session_state.downloads.append({
                    "label": file_name+".md",
                    "data": content,
                    "file_name": file_name+".md",
                    "mime": "text/markdown",
                    "created_at": datetime.now().isoformat(),
                })
                st.session_state.response_id["format_report"] = ""
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I have generated the formatted meeting notes. You can download them from the file box on the left. Please start a new conversation",
                    "timestamp": datetime.now(SGT).isoformat(),
                })
                input = "Please extract information about individual and organisation from this set of information" + content
                logger.info(input)
                logger.info("extract_info")
                logger.info("pass 1, change to extract info")
                agent_response, st.session_state.state["flag"], st.session_state.response_id["extract_info"] = st.session_state.agents["extract_info"].response(input, "")
                parsed_results = ""
                if agent_response.people:
                    for person in agent_response.people:
                        parsed_results += (
                            f"### {person.name}\n\n"
                            f"**Occupation / Education**  \n{person.occupation_education or 'Not provided'}\n\n"
                            f"**Interests**  \n{person.interests or 'Not provided'}\n\n"
                            f"**Personality**  \n{person.personality or 'Not provided'}\n\n"
                            f"**Personal**  \n{person.personal or 'Not provided'}\n\n"
                            "---\n\n"
                        )

                if agent_response.organisations:
                    for org in agent_response.organisations:
                        parsed_results += (
                            f"### {org.name}\n\n"
                            f"**Description**  \n{org.description or 'Not provided'}\n\n"
                            "---\n\n"
                        )
                if agent_response.response:
                    parsed_results += f"{agent_response.response}\n\n"
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": parsed_results,
                    "timestamp": datetime.now(SGT).isoformat(),
                })
                save_chat_logs()
                st.rerun()

        elif flag == "extract_info" :
            if agent_response.response != "SAVE":
                parsed_results = ""
                if agent_response.people:
                    for person in agent_response.people:
                        parsed_results += (
                            f"### {person.name}\n\n"
                            f"**Occupation / Education**  \n{person.occupation_education or 'Not provided'}\n\n"
                            f"**Interests**  \n{person.interests or 'Not provided'}\n\n"
                            f"**Personality**  \n{person.personality or 'Not provided'}\n\n"
                            f"**Personal**  \n{person.personal or 'Not provided'}\n\n"
                            "---\n\n"
                        )

                if agent_response.organisations:
                    for org in agent_response.organisations:
                        parsed_results += (
                            f"### {org.name}\n\n"
                            f"**Description**  \n{org.description or 'Not provided'}\n\n"
                            "---\n\n"
                        )
                if agent_response.response:
                    parsed_results += f"{agent_response.response}\n\n"
                placeholder.markdown(parsed_results)
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": parsed_results,
                    "timestamp": datetime.now(SGT).isoformat()
                    }
                )
                st.session_state.state["flag"] = flag
            # display the results as a file if completed
            else:
                logger.info("save 2, report")
                for person in agent_response.people:
                    file_name, content = write_individual_note(person)
                    save_notes(content, file_name, "people")
                    st.session_state.downloads.append({
                        "label": file_name+".md",
                        "data": content,
                        "file_name": file_name+".md",
                        "mime": "text/markdown",
                        "created_at": datetime.now().isoformat(),
                    })
                for org in agent_response.organisations:
                    file_name, content = write_organisation_note(org)
                    save_notes(content, file_name, "organisations")
                    st.session_state.downloads.append({
                        "label": file_name+".md",
                        "data": content,
                        "file_name": file_name+".md",
                        "mime": "text/markdown",
                        "created_at": datetime.now().isoformat(),
                    })
              
                st.session_state.response_id["extract_info"] = ""
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": "I have generated the formatted notes. You can download them from the file box on the left.",
                    "timestamp": datetime.now(SGT).isoformat(),
                })
                save_chat_logs()
                st.rerun()

        else:
            placeholder.markdown(agent_response)
            st.session_state.messages.append({
                "role": "assistant",
                "content": agent_response,
                "timestamp": datetime.now(SGT).isoformat()
            })






