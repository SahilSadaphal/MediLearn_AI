from langgraphflow.flow import *
from fastapi import (
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    HTTPException,
)
from utils.utils import *
import asyncio
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage
from const.const import PATH_TO_DOCS
from fastapi.responses import JSONResponse
from pathlib import Path
from datetime import datetime

app = FastAPI()
from typing import Annotated


class UserQuery(BaseModel):
    user_msg: str


from langgraphflow.flow import *
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import asyncio
from pydantic import BaseModel
from langchain_core.messages import HumanMessage, AIMessage

app = FastAPI()
from typing import Annotated


class UserQuery(BaseModel):
    user_msg: str


async def process_chat_message(user_input: str, thread_id: str = "user_session_1"):
    """Process a single chat message with proper memory management"""

    # Initialize configuration for thread management
    config = {"configurable": {"thread_id": thread_id}}

    # Handle exit commands
    if user_input.lower() in ["exit", "quit", "bye"]:
        return "Goodbye! Take care!"

    if not user_input.strip():
        return "Please enter a message."

    try:
        # Create user message
        user_message = HumanMessage(content=user_input)

        # Run graph with proper configuration - LangGraph will manage state
        result = graph.invoke({"messages": [user_message]}, config=config)

        # Bot reply
        bot_reply = result["messages"][-1].content
        return bot_reply

    except Exception as e:
        logger.error(f"Error processing message: {e}")
        return "I'm sorry, I encountered an error processing your message. Please try again."


@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat with the MediLearn AI Chatbot"""
    await websocket.accept()

    # Generate unique session ID for this WebSocket connection
    import uuid

    session_id = str(uuid.uuid4())

    # Send welcome message
    await websocket.send_text(
        "🤖 MediLearn AI Chatbot connected! How can I help you today?"
    )

    try:
        while True:
            # Receive message from client
            user_message = await websocket.receive_text()

            # Process the message
            bot_response = await process_chat_message(user_message, session_id)

            # Send response back to client
            await websocket.send_text(bot_response)

            # Handle exit conditions
            if user_message.lower() in ["exit", "quit", "bye"]:
                await websocket.close()
                break

    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_text(
            "Connection error occurred. Please refresh and try again."
        )


UPLOAD_DIR = Path(PATH_TO_DOCS)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@app.post("/upload-pdf/")
async def upload_pdf(file: UploadFile = File(...)):
    """Upload a single PDF file only if it doesn't already exist"""

    # Validate file type
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Check if file already exists in the directory
    file_path = UPLOAD_DIR / file.filename
    if file_path.exists():
        return JSONResponse(
            status_code=409,  # Conflict status code
            content={
                "success": False,
                "message": f"PDF '{file.filename}' already exists in the directory",
                "existing_file_path": str(file_path),
            },
        )

    # Validate file size (10MB limit)
    file_content = await file.read()
    file_size = len(file_content)

    if file_size > 10 * 1024 * 1024:  # 10MB
        raise HTTPException(
            status_code=400, detail="File size too large. Maximum 10MB allowed"
        )

    try:
        # Save file with original filename (since we already checked it doesn't exist)
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        process_pdfs()
        return JSONResponse(
            status_code=200,
            content={
                "success": True,
                "message": "PDF uploaded and added to knowledge base successfully",
                "file": {
                    "original_name": file.filename,
                    "saved_name": file.filename,  # Using original name since it doesn't exist
                    "file_path": str(file_path),
                    "file_size": file_size,
                    "upload_time": datetime.now().isoformat(),
                },
            },
        )

    except Exception as e:
        # Clean up partial file if it exists
        if file_path.exists():
            file_path.unlink()
        raise HTTPException(status_code=500, detail=f"Failed to save file: {str(e)}")
