import os
import logging

from typing import Annotated #Literal

# from pydantic import BaseModel, Field 
# from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.runnables import RunnableConfig
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage ,SystemMessage, HumanMessage

from tools import tools

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class MessagesState(TypedDict):
    
    messages: Annotated[list[BaseMessage], add_messages]

available_models = {}
default_model = None

# ---------------------------------
# Initialize Models and Tools
# ---------------------------------


gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:

    gemini_model_flash = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash", 
        streaming=True, 
        google_api_key=gemini_api_key
    )
    
    gemini_with_tools_flash = gemini_model_flash.bind_tools(tools)
    available_models["fast"] = gemini_with_tools_flash
    if not default_model:
        default_model = "fast"
    logger.info("Gemini (2.5-flash) model loaded.")
else:
    logger.warning("GEMINI_API_KEY not set. Gemini (2.5-flash) model will not be available.")

if gemini_api_key:
    
    gemini_model_flash_lite = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash-lite", 
        streaming=True, 
        google_api_key=gemini_api_key
    )
    
    gemini_with_tools_flash_lite = gemini_model_flash_lite.bind_tools(tools)
    available_models["unlimited"] = gemini_with_tools_flash_lite
    if not default_model:
        default_model = "unlimited"
    logger.info("Gemini (2.5-flash-lite) model loaded.")
else:
    logger.warning("GEMINI_API_KEY not set. Gemini (2.5-flash-lite) model will not be available.")


if gemini_api_key:
    
    gemini_model_pro = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-pro", 
        streaming=True, 
        google_api_key=gemini_api_key,
        temperature = 1
    )
    
    gemini_with_tools_pro = gemini_model_pro.bind_tools(tools)
    available_models["pro"] = gemini_with_tools_pro
    if not default_model:
        default_model = "pro"
    logger.info("Gemini (2.5-pro) model loaded.")
else:
    logger.warning("GEMINI_API_KEY not set. Gemini (2.5-pro) model will not be available.")

if gemini_api_key:
    
    gemini_model_v2_flash = ChatGoogleGenerativeAI(
        model="models/gemini-2.0-flash", 
        streaming=True, 
        google_api_key=gemini_api_key
    )
    
    gemini_with_tools_v2_flash = gemini_model_v2_flash.bind_tools(tools)
    available_models["flash"] = gemini_with_tools_v2_flash
    if not default_model:
        default_model = "flash"
    logger.info("Gemini (2.0-flash) model loaded.")
else:
    logger.warning("GEMINI_API_KEY not set. Gemini (2.0-flash) model will not be available.")






# ---------------------------------
# Define the graph nodes
# ---------------------------------

def agent_node(state: MessagesState, config: RunnableConfig):
    """
    The primary node that calls the LLM.
    It checks the config for a specified model, otherwise uses the default.
    It takes the current state (list of messages) and invokes the model.
    The model can respond with a message or a tool call.
    """
    # Get model_name from config, fallback to default
    model_name = config.get("configurable", {}).get("model_name", default_model)
    
    # Get the model from our available models, or use the default if invalid
    model = available_models.get(model_name)
    if not model:
        logger.warning(f"Invalid model_name: {model_name}. Falling back to default: {default_model}")
        model = available_models[default_model]
    
    logger.info(f"Using model: {model_name}")

    messages = state['messages']
    prompt = [
        SystemMessage(content="You are a Expert docter , if question is related to coding answer it as experience engineer, if question is related to weather use tool calling, else answer it according to user as experience person."),
        HumanMessage(content=f"""  {messages}   """)
    ]
    
    # Invoke the model with the current state
    response = model.invoke(prompt)
    
    # The response store in state
    return {"messages": [response]}

# The ToolNode is a prebuilt node that executes tools
# It takes the list of tools, finds the one(s) the agent called,
# executes them, and returns the output
tool_node = ToolNode(tools)


from langchain_core.messages import AIMessage

def should_continue(state: MessagesState) -> str:
    """Decides the next step: call tools or end."""
    last_message = state['messages'][-1]
    
    # Check if the last message from the AI has any tool calls
    if isinstance(last_message, AIMessage) and last_message.tool_calls:
        # If yes, route to the tool_node
        return "call_tools"
    else:
        # If no, we're done
        return "end"



# ---------------------------------
# Build the graph
# ---------------------------------


workflow = StateGraph(MessagesState)


workflow.add_node("agent", agent_node)
workflow.add_node("call_tools", tool_node)


# 3. Define the entry point
# This tells the graph where to start
workflow.add_edge(START, "agent")

workflow.add_conditional_edges(
    "agent",          # Start node
    should_continue,  # Function to decide the path
    {
        "call_tools": "call_tools", # If it returns "call_tools", go to the tool_node
        "end": END                  # If it returns "end", stop the graph
    }
)

workflow.add_edge("call_tools", "agent")

workflow.add_edge("agent", END)


# ---------------------------------
# Export the workflow
# ---------------------------------


# It will be compiled in main.py during the server startup.
workflow_ = workflow

