
import json

import requests
from agents.base_agent import BaseAgent, tracer
from shared_models import MissionState
from typing import Dict, Any, List

# --- LLM Communication Function (Reusing Ollama) ---
def call_ollama_for_synthesis(prompt: str) -> str:
    # Uses the same efficient local API call as the Router
    # ... (function body remains the same, but uses a higher temperature) ...
    API_URL = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.3, # Slightly higher temperature for creative synthesis
            "num_predict": 1024 # Increased token limit for the report body
        }
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status()
        result = response.json()
        return result['response'].strip()
    except requests.exceptions.RequestException as e:
        print(f"Ollama API Error: {e}")
        return "ERROR: LLM API connection failed." 
# --- End LLM Communication Function ---

class SynthesisAgent(BaseAgent):

    def __init__(self, agent_id: str, name: str, **kwargs): 
        # You must also store the argument if you plan to use it
        super().__init__(name=name, agent_id=agent_id, **kwargs)
       
    
    def execute(self, state: MissionState, plan_step: Dict[str, Any]) -> MissionState:
        
        if not state.raw_retrieval_data:
            self.log_action(
                state, 
                "SYNTHESIS_NO_DATA", 
                "No raw retrieval data; generating 'No Findings' report."
            )
            state.draft_report = "No relevant data found for the query."
            state.status = "SYNTHESIS_COMPLETE"
            return state

        # 1. Context Engineering: Prepare the source material for the prompt
        # Use a structured format to maintain grounding
        source_data_str = json.dumps(state.raw_retrieval_data, indent=2)
        
        synthesis_prompt = f"""
        You are an expert security intelligence analyst. Your task is to synthesize the fragmented data below 
        into one concise, objective intelligence report to address the original mission query.
        
        Original Mission: {state.user_query}
        
        Source Data (DO NOT ADD CLAIMS NOT SUPPORTED BY THIS DATA):
        ---
        {source_data_str}
        ---
        
        Instructions:
        1. Identify converging and diverging facts.
        2. Keep the report professional, concise, and focused on the facts supported by the Source Data.
        3. Do not include source metadata (timestamp, relevance_score) in the final report.
        """
        
        # 2. Call the LLM with Tracing
        with tracer.start_as_current_span("Synthesis_LLM_Call") as span:
            span.set_attribute("context.size", len(source_data_str))
            
            self.log_action(state, "SYNTHESIS_START", "Starting report synthesis from raw data.")
            raw_report_output = call_ollama_for_synthesis(synthesis_prompt)
            
        # 3. Process the Output
        if raw_report_output.startswith("ERROR"):
            state.status = "SYNTHESIS_FAILED"
            self.log_action(state, "SYNTHESIS_FAILED", raw_report_output)
            return state

        # Store the draft (it will be filtered by the next agent)
        state.draft_report = raw_report_output
        state.status = "SYNTHESIS_COMPLETE"
        self.log_action(state, "SYNTHESIS_COMPLETE", "Draft report generated successfully.")
        
        return state