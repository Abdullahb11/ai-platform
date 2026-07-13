import os
from fastapi import FastAPI
from dotenv import load_dotenv
from app.api.health import router as health_router

# Load environment variables
load_dotenv()

# Initialize FastAPI App
app = FastAPI(
    title="AI Platform API",
    version="0.1.0",
    description="Backend API for the AI Platform",
)

# Include Routers
app.include_router(health_router)
