import streamlit as st
from utility import init_session, check_password, load_config, append_message, add_download
import logging

# region <--------- Streamlit Page Configuration --------->

st.set_page_config(
    layout="centered",
    page_title="SGN Agentic CRMS"
)

# Do not continue if valid_password is not True.
if not check_password():
    st.stop()

config = load_config()

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger(__name__)

# endregion <--------- Streamlit Page Configuration --------->

st.title("SGN Agentic CRMS")

if st.button("Reset app"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]

    st.rerun()

#initial all the session state
init_session(config)

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

# Store chat history
if "messages" not in st.session_state:
    st.session_state.messages = []
    append_message("assistant", f"""
                   Hi - I am your personal AI assistant v0.1.\n
                   Currently, here are my existing capabilities:
                   1. log call report and then format and extract information
                   2. (Work in progress) research on a topic and save the research notes in markdown format
                   """)

# Display past messages
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if st.session_state.state["waiting_for_user"]:
    user_input = st.chat_input("Type your message...")

    if user_input:
        append_message("user", user_input)

        st.session_state.state.update({
            "pending_input": user_input,
            "needs_llm_call": True,
            "waiting_for_user": False,
        })

        st.rerun()

if st.session_state.state["needs_llm_call"]:
    agent_name = st.session_state.state["current_agent"]
    pending_input = st.session_state.state["pending_input"]
    response_id = st.session_state.response_id[agent_name]

    with st.chat_message("assistant"):
        with st.spinner(f"{agent_name} agent is thinking..."):
            logger.info("calling " + agent_name)
            logger.info(pending_input)
            response, new_response_id = st.session_state.agents[agent_name].response(pending_input, response_id)
            if "safe_title" in response:
                add_download(response["safe_title"], response["content"])
            if "safe_titles" in response and "contents" in response:
                for title, content in zip(response["safe_titles"], response["contents"]):
                    add_download(title, content)

    st.session_state.response_id[agent_name] = new_response_id

    if agent_name == response["next_agent"]:
        #converse with the user
        response_to_user = st.session_state.agents[agent_name].format_response(response)
        append_message("assistant", response_to_user)
        st.session_state.state.update({
            "pending_input": None,
            "needs_llm_call": False,
            "waiting_for_user": True,
        })
    else:
        # Continue automatically on next rerun
        if "response_to_user" in response and agent_name != "main": #in ["save_meeting", "save_people_org"]:
            append_message("assistant", response["response_to_user"])
        append_message("assistant", f"Handing over to {response["next_agent"]} agent.")
        st.session_state.state.update({
            "current_agent": response["next_agent"],
            "pending_input": response if "save" in response["next_agent"] else response["context_to_next_agent"],
            "needs_llm_call": True,
            "waiting_for_user": False,
        })

    st.rerun()

    # if agent_name == "format_report":
    #     if agent_response.response != "SAVE":
    #         logger.info(agent_response)
    #         agent_response = st.session_state.agents['format_report'].format_response(agent_response)
    #     else:
    #         #save the content, call the next agent and clear the thread
    #         file_name, content = write_meeting_note(agent_response)
    #         st.session_state.agents["saving_to_s3"].save_notes(content=content, title=file_name, type="notes")
    #         # Add file separately to download box
    #         add_download(file_name, content)
    #         # Respond to user
    #         append_message("assistant", "I have generated the formatted meeting notes. You will see it on the left section of the window. In the meantime, I will go on to extract information about individuals and organisations")
    #         # Reset existing chat
    #         st.session_state.response_id['format_report'] = ""
    #         st.session_state.agents["saving_to_s3"].save_chat_logs(st.session_state.messages)
    #         # Pass on to next agent
    #         agent_response = "Please extract information about individuals and organisations from this set of information" + content
    #         next_agent = "extract_info"

    
    # if agent_name == "extract_info" :
    #     if agent_response.response != "SAVE":
    #         agent_response = st.session_state.agents['extract_info'].format_response(agent_response)
    #     else:
    #         # save and append each person's notes
    #         for person in agent_response.people:
    #             file_name, content = write_individual_note(person)
    #             st.session_state.agents["saving_to_s3"].save_notes(content=content, title=file_name, type="people")
    #             add_download(file_name, content)
    #         # save and append each organisation's notes
    #         for org in agent_response.organisations:
    #             file_name, content = write_organisation_note(org)
    #             st.session_state.agents["saving_to_s3"].save_notes(content=content, title=file_name, type="organisations")
    #             add_download(file_name, content)
    #         #respond to user
    #         append_message("assistant", "I have generated the formatted notes for individuals and organisations. You will see it on the left section of the window.")
    #         #reset the pass convo
    #         st.session_state.response_id["extract_info"] = ""
    #         st.session_state.agents["saving_to_s3"].save_chat_logs(st.session_state.messages)
    #         # hand back to the main agent
    #         agent_response = "The other agents have completed their task. Please start a new conversation with the user."
    #         next_agent = "main"
