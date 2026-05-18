from fastapi import APIRouter
from app.services.comparison_service import get_comparison_data
from app.models.responses import ComparisonResponse

router = APIRouter(prefix="/comparison", tags=["Comparison"])

@router.get("/info", response_model=ComparisonResponse)
def comparison_info():
    return {"codes": get_comparison_data()}