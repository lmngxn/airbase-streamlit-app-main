# filename: utility.py
import streamlit as st
import os
from dotenv import load_dotenv
from datetime import datetime, timezone, timedelta
from agents.main_agent import MainAgent
from agents.call_report import CallReportAgent
from agents.format_report import FormatReportAgent
from agents.extract_info import ExtractInfoAgent
from agents.save_meeting_notes import SavingMeeting
from agents.save_person_org_notes import SavingPersonOrg
from agents.store import SavingAgent


SGT = timezone(timedelta(hours=8))

# """
# This file contains the common components used in the Streamlit App.
# This includes the sidebar, the title, the footer, and the password check.
# """

def init_session(config: dict):
    if "downloads" not in st.session_state:
        st.session_state.downloads = []

    if "state" not in st.session_state:
        st.session_state.state = {
            "current_agent": "main",
            "pending_input": None,
            "needs_llm_call": False,
            "waiting_for_user": True,
        }

    if "agents" not in st.session_state:
        st.session_state.agents = {
            "main": MainAgent(api_key=config['openai_api_key'], model=config['assistant_model']),
            "call_report": CallReportAgent(api_key=config['openai_api_key'], model=config['call_report_model']),
            "format_report": FormatReportAgent(api_key=config['openai_api_key'], model=config['format_report_model']),
            "extract_info": ExtractInfoAgent(api_key=config['openai_api_key'], model=config['extract_info_model']),
            "save_meeting": SavingMeeting(aws_access_key_id=config['aws_access_key_id'], aws_secret_access_key=config['aws_secret_access_key'], region_name=config['aws_region']),
            "save_people_org": SavingPersonOrg(aws_access_key_id=config['aws_access_key_id'], aws_secret_access_key=config['aws_secret_access_key'], region_name=config['aws_region']),
            "saving_to_s3": SavingAgent(aws_access_key_id=config['aws_access_key_id'], aws_secret_access_key=config['aws_secret_access_key'], region_name=config['aws_region'])
        }

    if "response_id" not in st.session_state:
        st.session_state.response_id = {
            "main": "",
            "call_report": "",
            "format_report": "",
            "extract_info": "",
            "save_meeting": "",
            "save_people_org": "",
        }

def check_password():
    """Returns `True` if the user has the correct password."""

    def password_entered():
        """Checks whether a password entered by the user is correct."""
        if os.getenv("PASSWORD") == st.session_state.get("password"):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    # Check if the PASSWORD environment variable is set
    password_env = os.getenv("PASSWORD")
    if password_env is None or password_env == "":
        return True  # Skip password check if not set

    # If the password has already been validated, return True
    if st.session_state.get("password_correct", False):
        return True

    # Show input for password
    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )

    # Show error if the password is incorrect
    if "password_correct" in st.session_state and not st.session_state["password_correct"]:
        st.error("😕 Password incorrect")

    return False

def load_config():
    load_dotenv()

    AWS_ACCESS_KEY_ID=os.getenv("AWS_ACCESS_KEY_ID", "")
    AWS_SECRET_ACCESS_KEY=os.getenv("AWS_SECRET_ACCESS_KEY", "")
    AWS_REGION=os.getenv("AWS_DEFAULT_REGION", "ap-southeast-1")
    openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
    assistant_model = os.getenv("ASSISTANT_MODEL", "gpt-4.1-mini").strip()
    call_report_model = os.getenv("CALL_REPORT_MODEL", "gpt-4.1-mini").strip()
    format_report_model = os.getenv("FORMAT_REPORT_MODEL", "gpt-4.1-mini").strip()
    extract_info_model = os.getenv("EXTRACT_INFO_MODEL", "gpt-4.1-mini").strip()

    return {'openai_api_key': openai_api_key,
            'assistant_model': assistant_model,
            'call_report_model': call_report_model,
            'format_report_model': format_report_model,
            'extract_info_model': extract_info_model,
            'aws_access_key_id': AWS_ACCESS_KEY_ID,
            'aws_secret_access_key': AWS_SECRET_ACCESS_KEY,            
            'aws_region': AWS_REGION,
            }

def append_message(role, content):
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "timestamp": datetime.now(SGT).strftime("%Y-%m-%dT%H-%M-%S"),
    })
    
def add_download(file_name, content):
    st.session_state.downloads.append({
        "label": file_name+".md",
        "data": content,
        "file_name": file_name+".md",
        "mime": "text/markdown",
        "created_at": datetime.now(SGT).strftime("%Y-%m-%dT%H-%M"),
    })