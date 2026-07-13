import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from app.api.health import router as health_router
from app.api.chat import router as chat_router

# Load environment variables
load_dotenv()

# Initialize FastAPI App
app = FastAPI(
    title="AI Platform API",
    version="0.1.0",
    description="Backend API for the AI Platform",
)

# Configure CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for development
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(health_router)
app.include_router(chat_router)
