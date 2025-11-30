
from agents.base_agent import BaseAgent
from shared_models import MissionState
import re
from typing import Dict, Any

class OutputFilterAgent(BaseAgent):
    """
    Implements mandatory PII scrubbing (Output Filtering) before verification.
    This serves as a security guardrail.
    """
    
    # Simple regex patterns for demonstration (names/IDs/locations)
    PII_PATTERNS = {
        "PERSON_NAME": r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', 
        "PROJECT_ID": r'\b(PROJ|SEC)-\d{4}\b',
        "LOCATION_SPECIFIC": r'\bArea 51\b|\bLagos\b' # Intentional PII to test filter
    }

    def __init__(self, agent_id: str, name: str, **kwargs): 
        # You must also store the argument if you plan to use it
        super().__init__(name=name, agent_id=agent_id, **kwargs)
    
    def execute(self, state: MissionState, plan_step: Dict[str, Any]) -> MissionState:
        
        report = state.draft_report
        if not report:
            self.log_action(state, "FILTER_SKIP", "No draft report to filter.")
            return state

        self.log_action(state, "FILTER_START", "Applying PII and Governance filters to draft report.")
        
        filtered_report = report
        filter_count = 0
        
        # Apply scrubbing to the draft report
        for tag, pattern in self.PII_PATTERNS.items():
            # Use re.sub to find and replace PII with a generic mask
            filtered_report, subs_made = re.subn(pattern, f"[MASKED_{tag}]", filtered_report)
            filter_count += subs_made
            
        # Apply scrubbing to the *raw retrieval data* before storing it for the next agent
        # (This prevents sensitive data from persisting in the state/trajectory logs)
        filtered_raw_data = []
        for item in state.raw_retrieval_data:
            filtered_snippet = item['snippet']
            for tag, pattern in self.PII_PATTERNS.items():
                filtered_snippet, _ = re.subn(pattern, f"[MASKED_{tag}]", filtered_snippet)
            item['snippet'] = filtered_snippet
            filtered_raw_data.append(item)
            
        
        # Update state with the scrubbed report and filtered raw data
        state.draft_report = filtered_report
        state.raw_retrieval_data = filtered_raw_data
        
        self.log_action(state, "FILTER_COMPLETE", f"Finished PII scrubbing. Masks applied: {filter_count}.", {"masks_applied": filter_count})
        state.status = "FILTERING_COMPLETE"
        return state