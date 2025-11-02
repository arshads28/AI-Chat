import logging
import json
import uvicorn
import uuid
import aiosqlite
import secrets

from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import StreamingResponse, HTMLResponse, RedirectResponse 
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

# Import the graph definition and the async checkpointer
from agent import workflow_
from langgraph.checkpoint.sqlite.aio import AsyncSqliteSaver
from fastapi.staticfiles import StaticFiles # <-- Add StaticFiles

# Setup logging
logger = logging.getLogger("agent")


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
    client_data: Optional[Dict[str, Any]] = None
    csrf_token: str

# CSRF token storage (in production, use Redis or database)
csrf_tokens = set()

@app.get("/")
async def get_root(request: Request):
    """Redirects the root URL '/' to our static 'index.html' file."""
    return RedirectResponse(url="/static/index.html")

@app.get("/csrf-token")
async def get_csrf_token():
    """Generate and return a CSRF token."""
    token = secrets.token_urlsafe(32)
    logger.info("CSRF token generated")
    csrf_tokens.add(token)
    return {"csrf_token": token}

@app.get("/chat-history/{thread_id}")
async def get_chat_history(thread_id: str):
    """Get chat history for a specific thread."""
    logger.info(f"chat-history function")
    try:
        config = {"configurable": {"thread_id": thread_id}}
        state = await langgraph_app.aget_state(config)
        
        messages = []
        if state and state.values and 'messages' in state.values:
            for msg in state.values['messages']:
                ai_typ = msg.__class__.__name__
                
                if ai_typ =='HumanMessage':
                    sender = 'user'

                elif ai_typ == 'AIMessage':

                    if hasattr(msg, 'tool_calls') and msg.tool_calls:
                        continue
                    sender = 'assistant'

                elif ai_typ == 'ToolMessage':
                    continue
                else:
                    # Skip other types like SystemMessage
                    continue
                
                if hasattr(msg, 'content'):
                    
                    messages.append({
                        'sender': sender,
                        'content': msg.content
                    })
        
        return {"messages": messages, "thread_id": thread_id}
    except Exception as e:
        logger.error(f"Error fetching chat history: {type(e).__name__}")
        return {"messages": [], "thread_id": thread_id}

@app.get("/all-chats")
async def get_all_chats():
    """Get all chat threads from database."""
    try:
        # Access the SQLite database directly
        conn = langgraph_app.checkpointer.conn
        
        # Debug: Check what tables exist
        cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = await cursor.fetchall()
        logger.info(f"Available tables: {tables}")
        
        # Get all thread IDs ordered by timestamp
        cursor = await conn.execute(
            "SELECT thread_id, MAX(checkpoint) as latest_checkpoint FROM checkpoints GROUP BY thread_id ORDER BY latest_checkpoint "
        )
        rows = await cursor.fetchall()
        logger.info(f"table is {rows}")
        logger.info(f"Found {len(rows)} thread_ids: {rows}")
        
        chats = []
        for row in rows:
            thread_id = row[0]
            # logger.info(f"Processing thread_id: {thread_id}")
            
            # Get first user message for title
            config = {"configurable": {"thread_id": thread_id}}
            state = await langgraph_app.aget_state(config)
            
            title = "New Chat"
            timestamp = 0
            if state and state.values and 'messages' in state.values:
                for msg in state.values['messages']:
                    if hasattr(msg, 'content') and msg.__class__.__name__ == 'HumanMessage':
                        title = msg.content[:30] + ('...' if len(msg.content) > 30 else '')
                        break
                # Extract timestamp from checkpoint data
                try:
                    import json
                    checkpoint_data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                    timestamp = int(checkpoint_data.get('ts', 0))
                except:
                    import time
                    timestamp = int(time.time() * 1000)
            
            chats.append({
                'thread_id': thread_id,
                'title': title,
                'timestamp': timestamp
            })
        
        logger.info(f"Returning {len(chats)} chats")
        return {"chats": chats}
    except Exception as e:
        logger.error(f"Error fetching all chats: {type(e).__name__}: {str(e)}")
        return {"chats": []}

 

async def llm_response(thread_id: str, request: ChatRequest):
    try:
        if not thread_id or thread_id == 1234:
            thread_id = str(uuid.uuid4())
            logger.info(f"Generated new thread_id: {thread_id}")

        logger.info(f"User message received (length: {len(request.input)})")

        # Configuration for the graph:
        # 'thread_id' is the key for persistence
        # 'model_name' is passed to our agent_node
        config = {
            "configurable": {
                "thread_id": thread_id,
                "model_name": request.model_name,
                "recursion_limit": 30
            }
        }

        
        # Use 'ainvoke' since this is an async function
        # resp = await langgraph_app.ainvoke( {'topic': request.input}, config=config)
        resp = await langgraph_app.ainvoke(
            {"messages": [HumanMessage(content=request.input)]}, 
            config=config
        )

        logger.info("AI workflow completed successfully")

        last_content = resp['messages'][-1].content
        logger.info(f"AI response generated (length: {len(str(last_content))})")
        
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
            logger.warning(f"Unexpected content type from model: {type(last_content).__name__}")
            res = str(last_content)

        logger.info(f"Response generated (length: {len(res)})")
        
        return {
            "final_message": res,
            "thread_id": thread_id
        }
    except Exception as e:
        logger.error(f"Critical error in llm_response: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Internal server error")
    



@app.post("/chat/")
async def chat_invoke(request: Request):
    """
    POST endpoint to get a single, complete chat response.
    """
    # Log request without exposing sensitive data
    logger.info("Chat request received")
    
    try:
        data = await request.json()
        
        # Validate input length
        if len(data.get('input', '')) > 10000:
            raise HTTPException(status_code=400, detail="Input too long")
        
        chat_request = ChatRequest(**data)
        
        # Validate CSRF token
        if chat_request.csrf_token not in csrf_tokens:
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        csrf_tokens.discard(chat_request.csrf_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {type(e).__name__}")
        raise HTTPException(status_code=422, detail="Invalid request format")
    
    # Get IP from the raw Request object
    ip = request.client.host
    logger.info(f"User IP is: {ip}")
    
    # Get data from the Pydantic body model (now named 'chat_request')
    client_details = chat_request.client_data
    logger.info(f"Client details received: {len(str(client_details)) if client_details else 0} chars")

    thread_id = chat_request.thread_id
    logger.info(f"Received request for thread: {thread_id}")
    
    # Pass the Pydantic model to your logic function
    return await llm_response(thread_id, chat_request)




if __name__ == "__main__":
    # This is the entry point for running the server directly
    uvicorn.run(
        "main:app", 
        host="127.0.0.1", 
        port=8000, 
        reload=True, 
        log_config="logging.yaml"
    )

