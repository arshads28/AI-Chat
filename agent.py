import os
import logging

from typing import Annotated, Literal

from pydantic import BaseModel, Field 
from langchain_openai import ChatOpenAI
from langchain_google_genai import ChatGoogleGenerativeAI
from typing_extensions import TypedDict
from langgraph.graph import StateGraph, END, START
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode
from langchain_core.messages import BaseMessage, HumanMessage

from tools import tools

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Setup logging
logger = logging.getLogger(__name__)

class MessagesState(TypedDict):
    
    messages: Annotated[list[BaseMessage], add_messages]


# ---------------------------------
# Initialize Models and Tools
# ---------------------------------


gemini_api_key = os.getenv("GEMINI_API_KEY")
if gemini_api_key:

    gemini_model = ChatGoogleGenerativeAI(
        model="models/gemini-2.5-flash", 
        streaming=True, 
        google_api_key=gemini_api_key
    )
    
    gemini_with_tools = gemini_model.bind_tools(tools)

    logger.info("Gemini model loaded.")
else:
    logger.warning("GEMINI_API_KEY not set. Gemini model will not be available.")





# ---------------------------------
# Define the graph nodes
# ---------------------------------

def agent_node(state: MessagesState):
    """
    The primary node that calls the LLM.
    It checks the config for a specified model, otherwise uses the default.
    It takes the current state (list of messages) and invokes the model.
    The model can respond with a message or a tool call.
    """
    messages = state['messages']
    
    # Invoke the model with the current state
    response = gemini_with_tools.invoke(messages)
    
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

