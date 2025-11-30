# agents/data_retrieval_agent.py
from agents.base_agent import BaseAgent, tracer
from shared_models import MissionState
from data.security_db import search_security_data
import json
from typing import List, Dict, Any

class DataRetrievalAgent(BaseAgent):

    def __init__(self, agent_id: str, name: str, **kwargs): 
        # You must also store the argument if you plan to use it
        super().__init__(name=name, agent_id=agent_id, **kwargs)
    
    def execute(self, state: MissionState, plan_step: Dict[str, Any]) -> MissionState:
        """
        Executes a specific data retrieval task defined by the Router's plan.
        
        Args:
            state: The current MissionState object.
            plan_step: The dictionary defining the current task (e.g., {"input": "topic"}).
        """
        topic = plan_step.get("input", state.user_query) # Use the plan's input
        
        # Pillar 2: Tracing - Start a span for the external Tool Call
        with tracer.start_as_current_span("Retrieval_Tool_Call") as span:
            span.set_attribute("tool.name", "search_security_data")
            span.set_attribute("search.topic", topic)
            
            self.log_action(state, "RETRIEVAL_START", f"Executing RAG tool search for topic: {topic}")
            state.status = "RETRIEVING"

            try:
                # --- The Tool Use Mechanism ---
                raw_results: List[Dict[str, Any]] = search_security_data(topic)
                # --- End Tool Use ---

                if not raw_results:
                    self.log_action(state, 
                                    "RETRIEVAL_EMPTY",
                                      f"RAG search returned no relevant snippets for: {topic}"
                                      )
                    state.status = "RETRIEVAL_EMPTY"
                    return state
                
                self.log_action(
                        state, 
                        "RETRIEVAL_SUCCESS", 
                        f"Found {len(raw_results)} relevant snippets.", 
                        {"retrieved_count": len(raw_results)}
                    )
                    
                    # Store results in the central state for the next agent (Synthesis)
                if not hasattr(state, "raw_retrieval_data") or state.raw_retrieval_data is None:
                    state.raw_retrieval_data = []
                    
                state.raw_retrieval_data.extend(raw_results)
                state.status = "RETRIEVING_COMPLETE"

            except Exception as e:
                # Robustness: Graceful failure on tool execution error
                error_msg = f"RAG Tool execution failed: {e.__class__.__name__}"
                self.log_action(state, "RETRIEVAL_FAILED", error_msg, {"error_detail": str(e)})
                state.status = "RETRIEVING_FAILED"

            return state