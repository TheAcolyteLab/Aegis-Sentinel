# shared_models.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class LogEntry(BaseModel):
    """Structured Log Entry for the agent's diary."""
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    agent_id: str
    action_type: str
    reasoning: str
    data: Optional[Dict[str, Any]] = None # Optional payload for tool outputs, errors, etc.

class MissionState(BaseModel):
    """The central shared state for the SSIA mission."""
    mission_id: str
    user_query: str
    status: str = "INITIALIZED" # e.g., INITIALIZED, PLANNING, RETRIEVING, VERIFIED, FAILED
    execution_trajectory: List[LogEntry] = Field(default_factory=list) # The chronological log/trace
    
    # Storage for intermediate results
    plan: Optional[List[Dict[str, str]]] = None # The Router's plan (sub-tasks)
    raw_retrieval_data: List[Dict[str, Any]] = Field(default_factory=list)
    draft_report: Optional[str] = None
    verification_score: Optional[float] = None
    
    final_report: Optional[str] = None