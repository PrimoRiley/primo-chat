from dotenv import load_dotenv
load_dotenv(override=True)
import asyncio
import chainlit as cl
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools import google_search
from google.genai import types  # for message content structure
from google.adk.agents.run_config import RunConfig, StreamingMode
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

STREAM_CFG = RunConfig(streaming_mode=StreamingMode.SSE, response_modalities=["TEXT"])

# 3. OAuth callback to allow Google Sign-In users (from step 2):
@cl.oauth_callback
def on_oauth_success(provider_id: str, token: str, raw_user_data: dict, default_user: cl.User):
    return default_user  # allow all Google-authenticated users

# 4. Initialize a new agent session for each chat (each user session):
@cl.on_chat_start
async def on_chat_start():
    user = cl.user_session.get("user")
    user_id = (
        getattr(user, "identifier", None)
        or getattr(user, "email", None)
        or getattr(user, "username", None)
        or "anonymous"
    )
    session_id = cl.user_session.get("session_id") or "default-session"

    # ❶ create the ADK session
    await session_service.create_session(
        app_name="chainlit-gemini-search",
        user_id=user_id,
        session_id=session_id,
    )

    # ❷ remember them for later
    cl.user_session.set("adk_user_id", user_id)
    cl.user_session.set("adk_session_id", session_id)

# 5. Handle incoming user messages and get agent responses:
@cl.on_message
async def handle(message: cl.Message):
    user_id    = cl.user_session.get("adk_user_id")
    session_id = cl.user_session.get("adk_session_id")

    if not (user_id and session_id):
        await cl.Message(
            content="⚠️ Internal error: ADK session was not initialised."
        ).send()
        return

    user_query = message.content
    content = types.Content(role="user", parts=[types.Part(text=user_query)])

    # empty shell we’ll update incrementally
    stream_msg = cl.Message(content="")
    await stream_msg.send()

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
        run_config=STREAM_CFG,      # streaming_mode = SSE
    ):
        if event.content and event.content.parts:
            chunk = "".join(p.text for p in event.content.parts)
            stream_msg.content += chunk
            await stream_msg.update()   # live push to UI

    await stream_msg.update()


print("GOOGLE_CLOUD_PROJECT:", os.getenv("GOOGLE_CLOUD_PROJECT"))
print("GOOGLE_CLOUD_LOCATION:", os.getenv("GOOGLE_CLOUD_LOCATION"))
print("GOOGLE_GENAI_USE_VERTEXAI:", os.getenv("GOOGLE_GENAI_USE_VERTEXAI"))
