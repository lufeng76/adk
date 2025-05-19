from contextlib import AsyncExitStack
from google.adk.agents import  Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters

MODEL_GEMINI_2_5_FLASH = "litellm_proxy/gemini-2.5-flash"
API_BASE_URL = "https://litellm-cloudrun-988469099469.us-central1.run.app/"
API_KEY = "sk-8wdj4Py_SG1-LgtnW10fwg"
google_maps_api_key="AIzaSyAeDVDHNWvnBX8SWl_98ZUAu1CtjCnrusc"

async def create_agent():
  """Gets tools from MCP Server."""
  common_exit_stack = AsyncExitStack()

  file_tools, _ = await MCPToolset.from_server(
      connection_params=StdioServerParameters(
          command='npx',
          args=["-y",    # Arguments for the command
            "@modelcontextprotocol/server-filesystem",
            # TODO: IMPORTANT! Change the path below to an ABSOLUTE path on your system.
            "/Users/lufengsh/adk",
          ],
      ),
      async_exit_stack=common_exit_stack
  )

  map_tools, _ = await MCPToolset.from_server(
      connection_params=StdioServerParameters(
          command='npx',
          args=["-y",
                "@modelcontextprotocol/server-google-maps",
          ],
          # Pass the API key as an environment variable to the npx process
          env={
              "GOOGLE_MAPS_API_KEY": google_maps_api_key
          }
      ),
      async_exit_stack=common_exit_stack
  )  

  agent = Agent(
      model=LiteLlm(
        model=MODEL_GEMINI_2_5_FLASH,
        api_base=API_BASE_URL,
        api_key=API_KEY
      ),    
      name='enterprise_assistant',
      instruction=(
          'if user ask about the location, address, route, use map tools. If user ask about the file, use file tools. '
      ),
      tools=[*map_tools, *file_tools,]
  )
  return agent, common_exit_stack


root_agent = create_agent()
