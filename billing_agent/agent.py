from datetime import date
import datetime
from typing import Any, Dict, Optional
from google.genai import types
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext
import logging
from zoneinfo import ZoneInfo
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from google.adk.agents.callback_context import CallbackContext
from .sub_agents.bigquery.tools import (
    get_database_settings as get_bq_database_settings,
)
from .prompts import return_instructions_root
from .tools import call_db_agent, call_ds_agent

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


def after_call_back(callback_context: CallbackContext):
    print("**********************************************")
    # print(callback_context.state.to_dict()['sql_query'])
    print(callback_context.state.to_dict()['question'])
    print(callback_context._invocation_context.session.id,)
    print(callback_context._invocation_context.user_content.to_json_dict(),)
    print(callback_context.state.to_dict()['raw_sql'],)
    print(callback_context.state.to_dict()['final_sql'],)
    print("**********************************************")


def after_tool_callback(
    tool: BaseTool,
    args: Dict[str, Any],
    tool_context: ToolContext,
    tool_response: Dict
) -> Optional[Dict]:
    """
    Example of an after_tool_callback function that logs tool usage and potentially modifies the response.

    This callback is executed after a tool has been called. It can be used to:
    - Log information about tool usage
    - Modify the tool response before it's returned to the agent
    - Store information in the session state
    - Perform additional processing based on the tool response

    Args:
        tool: The tool that was called
        args: The arguments that were passed to the tool
        tool_context: The context in which the tool was called
        tool_response: The response returned by the tool

    Returns:
        Optional[Dict]: If a dictionary is returned, it will replace the original tool response.
                       If None is returned, the original tool response will be used.
    """
    # Log information about the tool call
    logging.info(f"Tool called: {tool.name}")
    logging.info(f"Arguments: {args}")
    logging.info(f"Response: {tool_response}")

    # Store information in the session state
    # This can be used to track tool usage across multiple turns
    if "tool_usage" not in tool_context.state:
        tool_context.state["tool_usage"] = {}

    if tool.name not in tool_context.state["tool_usage"]:
        tool_context.state["tool_usage"][tool.name] = 0

    tool_context.state["tool_usage"][tool.name] += 1

    # Example: Add metadata to the response
    modified_response = {}
    modified_response['tool_response'] = tool_response
    modified_response["metadata"] = {
        "tool_name": tool.name,
        "call_count": tool_context.state["tool_usage"][tool.name],
        # "timestamp": datetime.now()
    }

    # Example: Modify the response based on specific conditions
    if tool.name == "get_billing_data" and "total_cost" in tool_response:
        # Add a warning if the cost exceeds a threshold
        if tool_response["total_cost"] > 1000:
            modified_response["warning"] = "High cost detected! Consider reviewing your usage."

    # Example: Enrich the response with additional information
    if tool.name == "query_database" and "results" in tool_response:
        # Add summary statistics to the response
        if isinstance(tool_response["results"], list) and len(tool_response["results"]) > 0:
            modified_response["summary"] = {
                "count": len(tool_response["results"]),
                "fields": list(tool_response["results"][0].keys()) if tool_response["results"] else []
            }

    # Return the modified response
    return modified_response


root_agent = Agent(
    name="db_ds_multiagent",
    model=LiteLlm(
        model='litellm_proxy/gemini-2.5-pro',
        api_base='https://litellm-cloudrun-668429440317.us-central1.run.app',
        # Pass authentication headers if needed
        # extra_headers=auth_headers
        # Alternatively, if endpoint uses an API key:
        api_key='sk-zQZEBtCjkNzFvxNFUtTDew'
    ),
    # model='gemini-2.5-pro-preview-05-06',
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
    after_agent_callback=after_call_back,
    # after_tool_callback=after_tool_callback,
    generate_content_config=types.GenerateContentConfig(temperature=0.01),

)
