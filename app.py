from dotenv import load_dotenv
load_dotenv(override=True)
import asyncio
import chainlit as cl
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types  # for message content structure
import os

# 1. Define the Vertex AI agent with Google Search tool:
agent = Agent(
    name="web_search_assistant",
    model="gemini-2.0-flash",  # choose a Gemini model variant (Flash is a fast, capable model).
    description="An AI assistant that can answer questions by searching the web.",
    instruction="You are a helpful assistant with access to Google Search. Use it to find up-to-date information for the user when needed.",
    tools=[google_search]  # Attach the built-in Google Search tool
)
# Note: The google_search tool allows web searches but **works only with Gemini-2 models**:contentReference[oaicite:17]{index=17}.

# 2. Set up session management for the agent:
session_service = InMemorySessionService()
runner = Runner(agent=agent, session_service=session_service, app_name="chainlit-gemini-search")

# 3. OAuth callback to allow Google Sign-In users (from step 2):
@cl.oauth_callback
def on_oauth_success(provider_id: str, token: str, raw_user_data: dict, default_user: cl.User):
    return default_user  # allow all Google-authenticated users

# 4. Initialize a new agent session for each chat (each user session):
@cl.on_chat_start
async def on_chat_start():
    # Each Chainlit session gets a unique ID and user object (if logged in)
    user = cl.user_session.get('user')  # the authenticated user info
    user_id = getattr(user, "identifier", None) or getattr(user, "email", None) or getattr(user, "username", None) or "anonymous"
    session_id = getattr(cl.user_session, "session_id", None) or getattr(cl.user_session, "id", None) or "default-session"
    # Create a fresh session for the agent (conversation state):
    await session_service.create_session(app_name="chainlit-gemini-search", user_id=user_id, session_id=session_id)
    # (No need to store the session object explicitly; session_service holds it.)

# 5. Handle incoming user messages and get agent responses:
@cl.on_message
async def handle_message(message: cl.Message):
    user_query = message.content  # text the user sent
    # Wrap the user query into the format expected by the agent:
    content = types.Content(role='user', parts=[types.Part(text=user_query)])
    # Get user_id and session_id as in on_chat_start
    user = cl.user_session.get('user')
    user_id = getattr(user, "identifier", None) or getattr(user, "email", None) or getattr(user, "username", None) or "user"
    session_id = getattr(cl.user_session, "session_id", None) or getattr(cl.user_session, "id", None) or "default-session"
    # Run the agent reasoning process (async). This returns an async iterator of events (steps in reasoning):
    events = runner.run_async(user_id=user_id, session_id=session_id, new_message=content)
    final_answer = ""
    # Iterate through events to capture the final answer (you could also stream intermediate results if desired):
    async for event in events:
        if event.is_final_response():
            final_answer = event.content.parts[0].text  # final answer text
    # Send the final answer back to the user via Chainlit
    await cl.Message(content=final_answer).send()

print("GOOGLE_CLOUD_PROJECT:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("GOOGLE_CLOUD_LOCATION:", os.getenv("GOOGLE_CLOUD_LOCATION"))
print("GOOGLE_GENAI_USE_VERTEXAI:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
