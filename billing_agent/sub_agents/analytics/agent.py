# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Data Science Agent V2: generate nl2py and use code interpreter to run the code."""
import os
from google.adk.code_executors import VertexAiCodeExecutor
from google.adk.agents import Agent
from .prompts import return_instructions_ds
from google.adk.models.lite_llm import LiteLlm



root_agent = Agent(
    model=LiteLlm(
        model='litellm_proxy/gemini-2.5-pro',
        api_base='https://litellm-cloudrun-668429440317.us-central1.run.app',
        # Pass authentication headers if needed
        # extra_headers=auth_headers
        # Alternatively, if endpoint uses an API key:
        api_key='sk-zQZEBtCjkNzFvxNFUtTDew'
    ),
    name="data_science_agent",
    instruction=return_instructions_ds(),
    code_executor=VertexAiCodeExecutor(
        optimize_data_file=True,
        stateful=True,
    ),
)
