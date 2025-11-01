import logging
import json
import uvicorn
import uuid
import aiosqlite
from fastapi import FastAPI, HTTPException, Request # <-- Add Request
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse # <-- Add RedirectResponse
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager
from typing import Optional

# Import the graph definition and the async checkpointer
from agent import workflow_
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from fastapi.staticfiles import StaticFiles # <-- Add StaticFiles

# Setup logging
logger = logging.getLogger("agent")


class ChatRequest(BaseModel):
    input: str
    model_name: str
    thread_id: Optional[str] = None  # <-- Make this optional


# This will hold our compiled-with-persistence app
langgraph_app = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Async context manager for FastAPI lifespan events.
    This is the new way to handle startup/shutdown in modern FastAPI.
    """
    global langgraph_app
    logger.info("Application startup...")
    
    # Create the async connection
    conn = await aiosqlite.connect("checkpoints.sqlite")
    
    # Pass the connection to the AsyncSqliteSaver
    memory = AsyncSqliteSaver(conn=conn)
    
    # Compile the graph with the checkpointer
    langgraph_app = workflow_.compile(checkpointer=memory)
    
    logger.info("LangGraph app compiled with persistence.")
    
    yield  # This is where the application runs
    
    await conn.close()
    logger.info("Database connection closed. Application shutdown.")

# Pass the lifespan context manager to the FastAPI app
app = FastAPI(lifespan=lifespan)


# Mount the current directory ('.') to serve static files from '/static'
# This is how the server will find and serve your index.html
app.mount("/static", StaticFiles(directory="."), name="static")


class ChatRequest(BaseModel):
    input: str
    model_name: str
    thread_id: Optional[str] = None 

@app.get("/")
async def get_root(request: Request): # <-- Add Request
    """Redirects the root URL '/' to our static 'index.html' file."""
    return RedirectResponse(url="/static/index111.html") 



async def llm_response(thread_id: str, request: ChatRequest):

    if not thread_id or thread_id == 1234:
        thread_id = str(uuid.uuid4())  # Correctly generate a new UUID string
        logger.info(f"Generated new thread_id: {thread_id}")

    logger.info(f" user message is : {request.input}")

    config = {"configurable": {"thread_id": thread_id}}
    
    # Use 'ainvoke' since this is an async function
    # resp = await langgraph_app.ainvoke( {'topic': request.input}, config=config)
    resp = await langgraph_app.ainvoke(
        {"messages": [HumanMessage(content=request.input)]}, 
        config=config
    )

    logger.info(f"Response from FULL AI workflow: {resp}")

    try:

        last_content = resp['messages'][-1].content
        logger.info(f"ai response last_content is {last_content} ")
        
        res = "" 

        # NEW LOGIC to handle multi-part content
        if isinstance(last_content, list):
        
            final_text_parts = []
            for part in last_content:
                if isinstance(part, dict) and 'text' in part:
                    final_text_parts.append(part['text'])
                elif isinstance(part, str):
                    final_text_parts.append(part)
            
            # Join all parts into a single string, separated by a newline
            res = "\n".join(final_text_parts)
        
        elif isinstance(last_content, str):
            # Content is already a simple string
            res = last_content
        
        else:
            # Fallback for unexpected content type (e.g., just in case)
            logger.warn(f"Unexpected content type from model: {type(last_content)}")
            res = str(last_content)

    except (KeyError, IndexError, AttributeError) as e:
        logger.error(f"Error extracting content from response: {e} - Resp: {resp}")
        res = "Error: Could not parse LLM response."


    logger.info(f"Response from AI workflow: {res}")
    
    return {
        "final_message": res,
        "thread_id": thread_id
    }
    



@app.post("/chat/")
async def chat_invoke(request: ChatRequest):
    """
    POST endpoint to get a single, complete chat response.
    """
    thread_id = request.thread_id

    logger.info(f"Received request for thread: {thread_id}")
    
    return await llm_response(thread_id, request)




if __name__ == "__main__":
    # This is the entry point for running the server directly
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True, 
        log_config="logging.yaml"
    )

