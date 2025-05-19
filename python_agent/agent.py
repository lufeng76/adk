from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.agents import LlmAgent
from .prompts import return_instructions_ds
from google.adk.tools import built_in_code_execution

AGENT_NAME="python_agent"
GEMINI_MODEL = "gemini-2.0-flash"


# Agent Definition
root_agent = LlmAgent(
    name=AGENT_NAME,
    model=GEMINI_MODEL,
#    tools=[built_in_code_execution],
    instruction=return_instructions_ds(),
    code_executor=VertexAiCodeExecutor(
        optimize_data_file=True,
        stateful=True,
    ),    
)

