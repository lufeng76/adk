import datetime
from zoneinfo import ZoneInfo
from google.adk.agents import LlmAgent as Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support

def get_weather(city: str) -> dict:
    """Retrieves the current weather report for a specified city.

    Args:
        city (str): The name of the city for which to retrieve the weather report.

    Returns:
        dict: status and result or error msg.
    """
    if city.lower() == "new york":
        return {
            "status": "success",
            "report": (
                "The weather in New York is sunny with a temperature of 25 degrees"
                " Celsius (77 degrees Fahrenheit)."
            ),
        }
    else:
        return {
            "status": "error",
            "error_message": f"Weather information for '{city}' is not available.",
        }


def get_current_time(city: str) -> dict:
    """Returns the current time in a specified city.

    Args:
        city (str): The name of the city for which to retrieve the current time.

    Returns:
        dict: status and result or error msg.
    """

    if city.lower() == "new york":
        tz_identifier = "America/New_York"
    else:
        return {
            "status": "error",
            "error_message": (
                f"Sorry, I don't have timezone information for {city}."
            ),
        }

    tz = ZoneInfo(tz_identifier)
    now = datetime.datetime.now(tz)
    report = (
        f'The current time in {city} is {now.strftime("%Y-%m-%d %H:%M:%S %Z%z")}'
    )
    return {"status": "success", "report": report}

MODEL_GEMINI_2_5_FLASH = "litellm_proxy/gemini-2.5-flash"
API_BASE_URL = "https://litellm-cloudrun-988469099469.us-central1.run.app/"
#API_KEY = "sk-syQ6JpqXU--h7g8giEsyyA"
API_KEY = "sk-8wdj4Py_SG1-LgtnW10fwg"
root_agent = Agent(
    model=LiteLlm(
        model=MODEL_GEMINI_2_5_FLASH,
        api_base=API_BASE_URL,
        # Pass authentication headers if needed
        # extra_headers=auth_headers
        # Alternatively, if endpoint uses an API key:
        api_key=API_KEY
    ),    
    name="weather_time_agent",
    description=(
        "Agent to answer questions about the time and weather in a city."
    ),
    instruction=(
        "You are a helpful agent who can answer user questions about the time and weather in a city."
    ),
    tools=[get_weather, get_current_time],
)