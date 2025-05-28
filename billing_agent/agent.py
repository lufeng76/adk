from datetime import date
from google.genai import types

from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from .sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from .prompts import return_instructions_root
from .tools import call_db_agent, call_ds_agent
from google.adk.tools import google_search

date_today = date.today()


def setup_before_agent_call(callback_context: CallbackContext):
    """Setup the agent."""

    # setting up database settings in session.state
    if "database_settings" not in callback_context.state:
        db_settings = dict()
        db_settings["use_database"] = "BigQuery"
        callback_context.state["all_db_settings"] = db_settings

    # setting up schema in instruction
    if callback_context.state["all_db_settings"]["use_database"] == "BigQuery":
        callback_context.state["database_settings"] = get_bq_database_settings(
        )
        schema = callback_context.state["database_settings"]["bq_ddl_schema"]

        callback_context._invocation_context.agent.instruction = (
            return_instructions_root()
            + f"""

    --------- The BigQuery schema of the relevant data with a few sample rows. ---------
    {schema}

    """
        )


root_agent = Agent(
    name="db_ds_multiagent",
    # model=LiteLlm(
    #     model='litellm_proxy/gemini-2.5-pro',
    #     api_base='https://litellm-cloudrun-668429440317.us-central1.run.app',
    #     # Pass authentication headers if needed
    #     # extra_headers=auth_headers
    #     # Alternatively, if endpoint uses an API key:
    #     api_key='sk-zQZEBtCjkNzFvxNFUtTDew'
    # ),
    model='gemini-2.5-pro-preview-05-06',
    instruction=return_instructions_root(),
    global_instruction=f"""
You are a Data Science and Data Analytics Multi Agent System.
Todays date: {date_today}
    """,
    tools=[
        call_db_agent,
        call_ds_agent,
    ],
    before_agent_callback=setup_before_agent_call,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),

)
