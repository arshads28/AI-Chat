import logging
import json
import uvicorn
import uuid
import aiosqlite
import secrets
import asyncio

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
    """Stream chat history for a specific thread."""
    async def generate():
        try:
            config = {"configurable": {"thread_id": thread_id}}
            state = await langgraph_app.aget_state(config)
            
            if state and state.values and 'messages' in state.values:
                for msg in state.values['messages']:
                    ai_typ = msg.__class__.__name__
                    
                    if ai_typ == 'HumanMessage':
                        sender = 'user'
                    elif ai_typ == 'AIMessage':
                        if hasattr(msg, 'tool_calls') and msg.tool_calls:
                            continue
                        sender = 'assistant'
                    elif ai_typ == 'ToolMessage':
                        continue
                    else:
                        continue
                    
                    if hasattr(msg, 'content'):
                        yield f"data: {json.dumps({'sender': sender, 'content': msg.content})}\n\n"
                        await asyncio.sleep(0.01)
            
            yield f"data: {json.dumps({'done': True, 'thread_id': thread_id})}\n\n"
        except Exception as e:
            logger.error(f"Error fetching chat history: {type(e).__name__}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

@app.get("/all-chats")
async def get_all_chats():
    """Stream all chat threads from database."""
    async def generate():
        try:
            conn = langgraph_app.checkpointer.conn
            cursor = await conn.execute(
                "SELECT thread_id, MAX(checkpoint) as latest_checkpoint FROM checkpoints GROUP BY thread_id ORDER BY latest_checkpoint"
            )
            rows = await cursor.fetchall()
            
            for row in rows:
                thread_id = row[0]
                config = {"configurable": {"thread_id": thread_id}}
                state = await langgraph_app.aget_state(config)
                
                title = "New Chat"
                timestamp = 0
                if state and state.values and 'messages' in state.values:
                    for msg in state.values['messages']:
                        if hasattr(msg, 'content') and msg.__class__.__name__ == 'HumanMessage':
                            title = msg.content[:30] + ('...' if len(msg.content) > 30 else '')
                            break
                    try:
                        checkpoint_data = json.loads(row[1]) if isinstance(row[1], str) else row[1]
                        timestamp = int(checkpoint_data.get('ts', 0))
                    except:
                        import time
                        timestamp = int(time.time() * 1000)
                
                yield f"data: {json.dumps({'thread_id': thread_id, 'title': title, 'timestamp': timestamp})}\n\n"
                await asyncio.sleep(0.01)
            
            yield f"data: {json.dumps({'done': True})}\n\n"
        except Exception as e:
            logger.error(f"Error fetching all chats: {type(e).__name__}: {str(e)}")
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")

 

async def llm_response_stream(thread_id: str, request: ChatRequest):
    async def generate():
        try:
            if not thread_id or thread_id == 1234:
                new_thread_id = str(uuid.uuid4())
                logger.info(f"Generated new thread_id: {new_thread_id}")
            else:
                new_thread_id = thread_id

            logger.info(f"User message received (length: {len(request.input)})")

            config = {
                "configurable": {
                    "thread_id": new_thread_id,
                    "model_name": request.model_name,
                    "recursion_limit": 30
                }
            }

            # Send thread_id first
            yield f"data: {json.dumps({'thread_id': new_thread_id})}\n\n"

            # Stream token by token using astream_events
            async for event in langgraph_app.astream_events(
                {"messages": [HumanMessage(content=request.input)]},
                config=config,
                version="v2"
            ):
                kind = event.get("event")
                
                # Stream LLM tokens as they're generated
                if kind == "on_chat_model_stream":
                    content = event.get("data", {}).get("chunk", {}).content
                    if content:
                        yield f"data: {json.dumps({'chunk': content})}\n\n"

            yield f"data: {json.dumps({'done': True})}\n\n"
            logger.info("AI workflow completed successfully")
            
        except Exception as e:
            logger.error(f"Critical error in llm_response_stream: {type(e).__name__}")
            yield f"data: {json.dumps({'error': 'Internal server error'})}\n\n"
    
    return StreamingResponse(generate(), media_type="text/event-stream")
    



@app.post("/chat/")
async def chat_invoke(request: Request):
    """
    POST endpoint to stream chat response.
    """
    logger.info("Chat request received")
    
    try:
        data = await request.json()
        
        if len(data.get('input', '')) > 10000:
            raise HTTPException(status_code=400, detail="Input too long")
        
        chat_request = ChatRequest(**data)
        
        if chat_request.csrf_token not in csrf_tokens:
            raise HTTPException(status_code=403, detail="Invalid CSRF token")
        csrf_tokens.discard(chat_request.csrf_token)
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Validation error: {type(e).__name__}")
        raise HTTPException(status_code=422, detail="Invalid request format")
    
    ip = request.client.host
    logger.info(f"User IP is: {ip}")
    
    client_details = chat_request.client_data
    logger.info(f"Client details received: {len(str(client_details)) if client_details else 0} chars")

    thread_id = chat_request.thread_id
    logger.info(f"Received request for thread: {thread_id}")
    
    return await llm_response_stream(thread_id, chat_request)




if __name__ == "__main__":
    # This is the entry point for running the server directly
    import os
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(
        "main:app", 
        host="0.0.0.0", 
        port=port, 
        reload=True,
        log_config="logging.yaml"
    )

