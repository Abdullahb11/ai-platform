from fastapi import APIRouter

router = APIRouter()

@router.get("/health", tags=["Health"])
async def get_health():
    """
    Check the health status of the API.
    Returns:
        dict: A status dict indicating the API is healthy.
    """
    return {"status": "healthy"}
