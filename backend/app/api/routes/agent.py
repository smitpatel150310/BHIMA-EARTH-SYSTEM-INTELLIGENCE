from fastapi import APIRouter, HTTPException, Depends
from app.models.schemas import AgentRequest
from app.core.agent import BHIMAAgent
from app.core.data_access import NASADataAccessor
from app.core.analysis import ScientificAnalysisEngine
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/agent", tags=["agent"])


def get_agent():
    settings = get_settings()
    accessor = NASADataAccessor(
        username=settings.nasa_earthdata_username,
        password=settings.nasa_earthdata_password
    )
    engine = ScientificAnalysisEngine()
    return BHIMAAgent(
        api_key=settings.gemini_api_key,
        data_accessor=accessor,
        analysis_engine=engine
    )


@router.post("/chat")
async def agent_chat(
    request: AgentRequest,
    agent: BHIMAAgent = Depends(get_agent)
):
    try:
        history = [{"role": m.role, "content": m.content} for m in request.conversation_history]
        result = agent.chat(message=request.message, history=history)
        return result
    except Exception as e:
        logger.error(f"Agent endpoint error: {e}")
        raise HTTPException(status_code=500, detail="Agent processing failed")


@router.get("/tools")
async def list_tools():
    from app.core.agent import TOOL_DEFINITIONS
    return {"tools": TOOL_DEFINITIONS}
