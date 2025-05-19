from google.adk.agents import Agent
from google.adk.tools.toolbox_tool import ToolboxTool
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.genai import types


from google.adk.models.lite_llm import LiteLlm # For multi-model support

MODEL_GEMINI_2_5_FLASH = "litellm_proxy/gemini-2.5-flash"
API_BASE_URL = "https://litellm-cloudrun-988469099469.us-central1.run.app/"
API_KEY = "sk-8wdj4Py_SG1-LgtnW10fwg"

# toolbox_tools = ToolboxTool("http://127.0.0.1:5000")
toolbox_tools = ToolboxTool("https://toolbox-avco6pj6ma-uc.a.run.app")

prompt = """
  You're a helpful hotel assistant. You handle hotel searching, booking and
  cancellations. When the user searches for a hotel, mention it's name, id,
  location and price tier. Always mention hotel ids while performing any
  searches. This is very important for any operations. For any bookings or
  cancellations, please provide the appropriate confirmation. Be sure to
  update checkin or checkout dates if mentioned by the user.
  Don't ask for confirmations from the user.
"""

root_agent = Agent(
    model=LiteLlm(
        model=MODEL_GEMINI_2_5_FLASH,
        api_base=API_BASE_URL,
        api_key=API_KEY
    ),    
    name='hotel_agent',
    description='A helpful AI assistant.',
    instruction=prompt,
    tools=toolbox_tools.get_toolset(toolset_name="my-toolset"),
)
