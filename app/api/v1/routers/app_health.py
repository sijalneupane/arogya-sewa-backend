from fastapi import APIRouter

router = APIRouter()

@router.get("/health")
def health_check():
    return {"message": "Success! The application is healthy."}
