import os

from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.agents import LlmAgent
from .prompts import return_instructions_ds
# from google.adk.code_executors import BuiltInCodeExecutor


# Agent Definition
root_agent = LlmAgent(
    model=os.getenv("ANALYTICS_AGENT_MODEL"),
    name="data_science_agent",
#    tools=[built_in_code_execution],
    instruction=return_instructions_ds(),
    code_executor=VertexAiCodeExecutor(
        optimize_data_file=True,
        stateful=True,
    ),    
)

