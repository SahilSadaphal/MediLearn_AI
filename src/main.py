import uvicorn
from fastapi import (
    Form,
    FastAPI,
    WebSocket,
    WebSocketDisconnect,
    UploadFile,
    File,
    HTTPException,
    Depends,
    Cookie,
    Request,
    Response,
)
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.security import HTTPBasic
from pymongo import MongoClient
from typing import List, Annotated
import secrets
import asyncio
import jwt
import time
import os
import logging
from pathlib import Path
from datetime import datetime

import bcrypt
from pydantic import BaseModel
from langchain_core.messages import HumanMessage
from dotenv import load_dotenv

# --- Load Environment Variables ---
# Best practice: load configurations from a .env file for security
load_dotenv()

# --- Placeholder Setups (Replace with your actual implementations) ---

# 1. Configure Logging
# Set up a basic logger. In a real application, you might configure this more robustly.
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 2. Define your LangGraph graph
# This is a placeholder. You need to define your actual LangGraph instance here.
# from src.langgraphflow.flow import * # Assuming your graph is defined here
# graph = ... # Your graph instance

# A mock graph class for demonstration purposes so the code can run.
class MockGraph:
    def invoke(self, inputs, config=None):
        user_message = inputs["messages"][-1].content
        return {"messages": [AIMessage(content=f"AI response to: '{user_message}'")]}

graph = MockGraph() # Replace with your actual graph instance

# 3. Define the PDF processing function
# This function is called after a PDF is uploaded. Implement your logic here.
def process_pdfs():
    logger.info("Processing uploaded PDFs in the knowledge base...")
    # Add your PDF processing, embedding, and indexing logic here
    pass

# --- Constants and Configuration ---
SECRET_KEY = os.getenv("SECRET_KEY", "a-secure-default-secret-key-for-development")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_SECONDS = 300
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Use environment variable for MongoDB connection
MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017/")
DB_NAME = "admin"
USERS_COLLECTION = "Roles_Access"

# --- FastAPI App Initialization ---
app = FastAPI(title="MediLearn AI API")
security = HTTPBasic()

# --- Custom Exception for Token Handling ---
class TokenExceptionHandler(Exception):
    pass

@app.exception_handler(TokenExceptionHandler)
async def token_exception_handler(request: Request, exc: TokenExceptionHandler):
    # Redirect to login page when the custom token exception is raised
    return RedirectResponse(url="/login_page") # Assuming you have a frontend route for login

# --- Password and User Verification Utilities ---

def create_password_hash(password: str) -> str:
    """Hashes a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed_password.decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain-text password against a stored hash."""
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_current_user(access_token: Annotated[str | None, Cookie()] = None):
    """Dependency to verify the JWT access token from cookies and return user data."""
    if access_token is None:
        raise TokenExceptionHandler() # Use custom exception to trigger redirect
    
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        role: str = payload.get("role")
        if username is None or role is None:
            raise HTTPException(status_code=401, detail="Invalid authentication credentials")
        return {"username": username, "role": role}
    except jwt.ExpiredSignatureError:
        # Here you could implement logic to use a refresh token
        raise HTTPException(status_code=401, detail="Token has expired, please log in again")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

# --- Chat Processing Logic ---

async def process_chat_message(user_input: str, thread_id: str):
    """Processes a single chat message using the LangGraph instance."""
    config = {"configurable": {"thread_id": thread_id}}

    if user_input.lower() in ["exit", "quit", "bye"]:
        return "Goodbye! Take care!"

    if not user_input.strip():
        return "Please enter a message."

    try:
        user_message = HumanMessage(content=user_input)
        # Assuming the graph manages state via the config thread_id
        result = await graph.ainvoke({"messages": [user_message]}, config=config)
        bot_reply = result["messages"][-1].content
        return bot_reply
    except Exception as e:
        logger.error(f"Error processing message for thread {thread_id}: {e}")
        return "I'm sorry, I encountered an error. Please try again."

# --- API Endpoints ---

@app.websocket("/ws/chat")
async def websocket_chat_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time chat."""
    await websocket.accept()
    session_id = secrets.token_hex(16)
    
    await websocket.send_text("🤖 MediLearn AI Chatbot connected! How can I help you today?")
    
    try:
        while True:
            user_message = await websocket.receive_text()
            bot_response = await process_chat_message(user_message, session_id)
            await websocket.send_text(bot_response)
            
            if user_message.lower() in ["exit", "quit", "bye"]:
                break
                
    except WebSocketDisconnect:
        logger.info(f"Client {session_id} disconnected")
    except Exception as e:
        logger.error(f"WebSocket error for session {session_id}: {e}")
        await websocket.send_text("Connection error occurred. Please try again.")
    finally:
        await websocket.close()


@app.post("/login/")
async def login(
    response: Response,
    username: str = Form(...),
    password: str = Form(...)
):
    """Authenticates a user and sets JWT tokens in secure HTTPOnly cookies."""
    try:
        client = MongoClient(MONGO_URI)
        db = client[DB_NAME]
        users_collection = db[USERS_COLLECTION]
        
        user_data = users_collection.find_one({"username": username})
        client.close()

        if not user_data or not verify_password(password, user_data["password"]):
            raise HTTPException(status_code=401, detail="Invalid username or password")

        role = user_data["role"]
        
        # Create Access Token
        access_token_expires = time.time() + ACCESS_TOKEN_EXPIRE_SECONDS
        access_token = jwt.encode(
            {'sub': username, 'role': role, 'exp': access_token_expires}, 
            SECRET_KEY, 
            algorithm=ALGORITHM
        )

        # Create Refresh Token
        refresh_token_expires = time.time() + (REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60)
        refresh_token = jwt.encode(
            {'sub': username, 'role': role, 'exp': refresh_token_expires}, 
            SECRET_KEY, 
            algorithm=ALGORITHM
        )
        
        # Set tokens in cookies
        response.set_cookie(
            key="access_token",
            value=access_token,
            max_age=ACCESS_TOKEN_EXPIRE_SECONDS,
            httponly=True, # Prevents client-side script access
            secure=False,   # Recommended for production (HTTPS)
            samesite="lax"
        )
        response.set_cookie(
            key="refresh_token",
            value=refresh_token,
            max_age=REFRESH_TOKEN_EXPIRE_DAYS * 24 * 60 * 60,
            httponly=True,
            secure=False,
            samesite="lax"
        )
        
        return {"message": "Login successful", "role": role}

    except Exception as e:
        logger.error(f"Login error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Directory for storing uploaded PDFs
PATH_TO_DOCS = os.getenv("PATH_TO_DOCS", "uploaded_docs")
UPLOAD_DIR = Path(PATH_TO_DOCS)
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

@app.post("/upload-pdf/")
async def upload_pdf(
    current_user: Annotated[dict, Depends(get_current_user)], 
    file: UploadFile = File(...)
):
    """Upload a PDF file. Only accessible by authenticated users."""
    if file.content_type != "application/pdf":
        raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    file_path = UPLOAD_DIR / file.filename
    if file_path.exists():
        return JSONResponse(
            status_code=409,
            content={"message": f"File '{file.filename}' already exists."}
        )
    
    # Validate file size (e.g., 10MB limit)
    file_content = await file.read()
    if len(file_content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="File size exceeds 10MB limit")

    try:
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Trigger background processing of the new PDF
        process_pdfs()
        
        return JSONResponse(
            status_code=201, # 201 Created is more appropriate
            content={
                "message": "PDF uploaded successfully and is being processed.",
                "filename": file.filename,
            },
        )
    except Exception as e:
        logger.error(f"Failed to save file '{file.filename}': {e}")
        if file_path.exists():
            file_path.unlink() # Clean up partially saved file
        raise HTTPException(status_code=500, detail="Failed to save file")


if __name__ == "__main__":
    # Example of how to create a user for testing
    # try:
    #     client = MongoClient(MONGO_URI)
    #     db = client[DB_NAME]
    #     collection = db[USERS_COLLECTION]
    #     if not collection.find_one({"username": "admin"}):
    #         hashed_pw = create_password_hash("admin123")
    #         collection.insert_one({"username": "admin", "password": hashed_pw, "role": "administrator"})
    #         logger.info("Admin user created.")
    #     client.close()
    # except Exception as e:
    #     logger.error(f"Could not create admin user: {e}")

    uvicorn.run(app, host="0.0.0.0", port=8000)