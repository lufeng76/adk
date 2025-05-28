# ADK LLM Request/Response Logging

## Current Logging Behavior

The ADK framework automatically logs both LLM requests and responses when you run your agent. This logging is implemented in `google/adk/models/google_llm.py`.

### Where Logging Happens

1. **Request Logging** (line 91):
   ```python
   logger.info(_build_request_log(llm_request))
   ```

2. **Response Logging** (line 148):
   ```python
   logger.info(_build_response_log(response))
   ```

### What Gets Logged

#### LLM Request includes:
- **System Instruction**: The agent's instruction
- **Contents**: Full conversation history (user messages and model responses)
- **Functions**: Available tools/functions the model can call

Example from your terminal:
```
LLM Request:
-----------------------------------------------------------
System Instruction:
You are a helpful agent who can answer user questions about the time and weather in a city.

You are an agent. Your internal name is "weather_time_agent".

 The description about you is "Agent to answer questions about the time and weather in a city."
-----------------------------------------------------------
Contents:
{"parts":[{"text":"hello"}],"role":"user"}
{"parts":[{"text":"Hello! How can I help you today? I can provide you with the current weather or time in a specific city.\n"}],"role":"model"}
{"parts":[{"text":"what's the whether like in hk?"}],"role":"user"}
-----------------------------------------------------------
Functions:
get_weather: {'city': {'type': <Type.STRING: 'STRING'>}} -> {'type': <Type.OBJECT: 'OBJECT'>}
get_current_time: {'city': {'type': <Type.STRING: 'STRING'>}} -> {'type': <Type.OBJECT: 'OBJECT'>}
-----------------------------------------------------------
```

#### LLM Response includes:
- **Text**: The model's text response (if any)
- **Function calls**: Any function calls the model decides to make
- **Raw response**: Complete JSON response from the API

Example from your terminal:
```
LLM Response:
-----------------------------------------------------------
Text:
None
-----------------------------------------------------------
Function calls:
name: get_weather, args: {'city': 'hk'}
-----------------------------------------------------------
Raw response:
{"candidates":[{"content":{"parts":[{"function_call":{"args":{"city":"hk"},"name":"get_weather"}}],"role":"model"},"finish_reason":"STOP",...}
-----------------------------------------------------------
```

## How to Control Logging

The logging uses Python's standard logging module with logger name `'google_adk.google.adk.models.google_llm'`.

### To adjust logging level:

1. **Disable these specific logs**:
   ```python
   import logging
   logging.getLogger('google_adk.google.adk.models.google_llm').setLevel(logging.WARNING)
   ```

2. **Enable DEBUG level for more details**:
   ```python
   import logging
   logging.getLogger('google_adk').setLevel(logging.DEBUG)
   ```

3. **Custom logging configuration**:
   ```python
   import logging
   
   # Configure logging format
   logging.basicConfig(
       level=logging.INFO,
       format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
   )
   ```

## Key Functions

### `_build_request_log(req: LlmRequest)`
Formats the LLM request into a readable string showing:
- System instruction
- Conversation contents (excluding binary data like images)
- Available functions with their signatures

### `_build_response_log(resp: GenerateContentResponse)`
Formats the LLM response showing:
- Text content
- Function calls made by the model
- Complete raw JSON response

## Notes

- Binary data (like images) is automatically excluded from logs to keep them readable
- The logging happens at INFO level by default
- Both streaming and non-streaming responses are logged
- Function signatures are formatted as: `function_name: {parameters} -> {return_type}`

This built-in logging is extremely useful for debugging and understanding:
- What exact prompt is sent to the LLM
- How the conversation context builds up
- What functions the LLM has access to
- How the LLM responds and why it makes certain function calls
