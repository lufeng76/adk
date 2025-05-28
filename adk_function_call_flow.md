# ADK Agent Function Call Flow

This document traces the exact function calls when an agent processes a message in the ADK framework.

## Function Call Sequence

When a user sends a message (e.g., "hello") to the agent, here's the complete function call flow:

### 1. **Web UI → FastAPI Endpoint**
```
POST /run_sse
└── fast_api.agent_run_sse(req: AgentRunRequest)
```

### 2. **FastAPI → Runner**
```python
agent_run_sse()
├── _get_runner_async(req.app_name)
│   ├── _get_root_agent_async(app_name)
│   │   └── importlib.import_module(app_name)  # Loads simple_agent.agent.root_agent
│   └── Runner.__init__(app_name, root_agent, ...)
└── runner.run_async(user_id, session_id, new_message, run_config)
```

### 3. **Runner Execution**
```python
Runner.run_async()
├── session_service.get_session()  # Get conversation history
├── _new_invocation_context()      # Create execution context
├── _find_agent_to_run()           # Determine which agent to run
├── _append_new_message_to_session()  # Add user message to session
└── invocation_context.agent.run_async(invocation_context)
```

### 4. **Agent Execution (LlmAgent)**
```python
LlmAgent._run_async_impl(ctx)
└── self._llm_flow.run_async(ctx)  # Uses AutoFlow or SingleFlow
```

### 5. **LLM Flow Execution (SingleFlow/AutoFlow)**
```python
BaseLlmFlow.run_async(invocation_context)
└── while True:
    └── _run_one_step_async(invocation_context)
        ├── _preprocess_async()     # Prepare LLM request
        ├── _call_llm_async()       # Call the LLM
        └── _postprocess_async()    # Process LLM response
```

### 6. **Preprocessing Phase**
```python
_preprocess_async(invocation_context, llm_request)
├── Run request processors:
│   ├── basic.request_processor      # Basic setup
│   ├── auth_preprocessor.request_processor  # Auth handling
│   ├── instructions.request_processor  # Add system instructions
│   ├── identity.request_processor   # Agent identity
│   ├── contents.request_processor   # Add conversation history
│   ├── _nl_planning.request_processor  # Natural language planning
│   └── _code_execution.request_processor  # Code execution setup
└── tool.process_llm_request() for each tool  # Process tools
```

### 7. **LLM Call**
```python
_call_llm_async(invocation_context, llm_request, model_response_event)
├── _handle_before_model_callback()  # Optional pre-processing
├── llm.generate_content_async(llm_request)  # Actual LLM call
│   └── Sends request to Gemini with:
│       ├── System instruction
│       ├── Conversation history
│       └── Available functions/tools
└── _handle_after_model_callback()   # Optional post-processing
```

### 8. **Postprocessing Phase**
```python
_postprocess_async(invocation_context, llm_request, llm_response, model_response_event)
├── _postprocess_run_processors_async()
│   ├── _nl_planning.response_processor
│   └── _code_execution.response_processor
├── _finalize_model_response_event()  # Build final event
└── _postprocess_handle_function_calls_async()  # If LLM called functions
    └── functions.handle_function_calls_async()
        └── Executes the actual Python function (e.g., get_weather)
```

### 9. **Function Execution (if LLM decides to call a function)**
```python
functions.handle_function_calls_async()
├── For each function call:
│   ├── Find the function in tools_dict
│   ├── Execute the function with provided arguments
│   │   └── e.g., get_weather(city="hk")
│   └── Return function response
└── Create function response event
```

### 10. **Event Streaming**
```python
# Events are yielded back through the chain:
BaseLlmFlow → LlmAgent → Runner → FastAPI → SSE Stream → Web UI
```

## Example Execution Trace

For the user message "what's the weather like in hk?":

1. **Request Processing**:
   - `instructions.request_processor` adds: "You are a helpful agent who can answer user questions about the time and weather in a city."
   - `contents.request_processor` adds conversation history
   - Tools are registered: `get_weather`, `get_current_time`

2. **LLM Request**:
   ```
   System: You are a helpful agent...
   User: "hello"
   Model: "Hello! How can I help you today?..."
   User: "what's the weather like in hk?"
   Functions: get_weather, get_current_time
   ```

3. **LLM Response**:
   - LLM decides to call: `get_weather(city="hk")`

4. **Function Execution**:
   ```python
   get_weather("hk")
   # Returns: {"status": "error", "error_message": "Weather information for 'hk' is not available."}
   ```

5. **Second LLM Call**:
   - LLM receives function response
   - Generates final response: "I am sorry, weather information for hk is not available..."

## Key Components

### Request Processors
- Transform and enrich the LLM request
- Add system instructions, identity, conversation history
- Configure tools and capabilities

### Response Processors  
- Process LLM responses
- Handle special cases (planning, code execution)
- Transform responses before returning to user

### Function Handling
- `functions.handle_function_calls_async()` orchestrates function execution
- Maps LLM function calls to actual Python functions
- Returns results back to LLM for final response

### Event System
- Each interaction generates events
- Events contain content, metadata, and actions
- Events are stored in session and streamed to UI

## Summary

The ADK framework uses a layered architecture:
1. **Web Layer**: FastAPI handles HTTP/SSE
2. **Runner Layer**: Manages sessions and agent execution
3. **Agent Layer**: Defines behavior and tools
4. **Flow Layer**: Orchestrates LLM interactions
5. **Processor Layer**: Modular request/response handling
6. **LLM Layer**: Actual model communication

This design allows for:
- Modular processing pipeline
- Easy extension through processors
- Clean separation of concerns
- Flexible tool integration
- Multi-turn conversation support
