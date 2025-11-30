import json

import requests
from agents.base_agent import BaseAgent, tracer
from shared_models import MissionState
from typing import Dict, Any, List

# --- LLM Communication Function (Reusing Ollama) ---
def call_ollama_for_critique(prompt: str) -> str:
    
    API_URL = "http://localhost:11434/api/generate"
    
    payload = {
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.05, # Very low temperature for deterministic judgment
            "num_predict": 512,  
            
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

class VerificationAgent(BaseAgent):
    
    EVALUATION_RUBRIC = """
    CRITERIA FOR SCORING (Scale 1.0 to 5.0):
    1. Factual Hallucination (Weight 40%): Every claim must be supported by the provided raw source data. Score drops if claims lack grounding.
    2. Algorithmic Bias/Tone (Weight 30%): Report must maintain objective, neutral, and professional language. Score drops for sensationalism or amplification of systemic biases.
    3. PII/Security Compliance (Weight 30%): Check if any sensitive unmasked data (e.g., PII, classified tags) slipped past the OutputFilterAgent.

    PASS Threshold: Overall Score >= 4.0 AND no critical PII leakage.
    """
    
    def __init__(self, agent_id: str, name: str, **kwargs): 
        # You must also store the argument if you plan to use it
        super().__init__(name=name, agent_id=agent_id, **kwargs)
       
    def execute(self, state: MissionState, plan_step: Dict[str, Any]) -> MissionState:
        
        # Check for draft presence (Robustness)
        if not state.draft_report or not state.raw_retrieval_data:
            self.log_action(state, "VERIFICATION_FAILED", "Missing draft report or raw data for critique.")
            state.status = "VERIFICATION_FAILED"
            return state

        # Context Engineering for Critique
        critique_prompt = f"""
        MISSION: {state.user_query}
        DRAFT REPORT TO CRITIQUE: 
        ---
        {state.draft_report}
        ---
        RAW SOURCE DATA (Ground Truth): 
        ---
        {json.dumps(state.raw_retrieval_data, indent=2)}
        ---
        
        EVALUATION RUBRIC: {self.EVALUATION_RUBRIC}

        Task: Apply the rubric and return a JSON object containing the overall score, a boolean 'passed' status, and a detailed 'critique'.
        """
        
        with tracer.start_as_current_span("Verification_LLM_Critique") as span:
            self.log_action(state, "VERIFICATION_START", "Starting critical review using LLM-as-a-Judge paradigm.")
            
            raw_critique_output = call_ollama_for_critique(critique_prompt)
            
        try:
            # NOTE: In a real system, you would use Pydantic to parse this JSON reliably
            critique_result = json.loads(raw_critique_output)
            
            score = critique_result.get('score', 0.0)
            passed = critique_result.get('passed', False)
            
            state.verification_score = score
            
            self.log_action(state, "VERIFICATION_SCORE", f"Report scored {score}/5.0. Passed: {passed}", critique_result)

            if not passed:
                state.status = "VERIFICATION_FAIL_CRITICAL"
                self.log_action(state, "VERIFICATION_FAIL_CRITICAL", "Critique failed. Initiating re-planning for revision.")
            else:
                state.status = "VERIFICATION_PASS"
                self.log_action(state, "VERIFICATION_PASS", "Report meets all RAI and quality criteria.")
                # Final output is set here
                state.final_report = state.draft_report
                
        except json.JSONDecodeError:
            state.status = "VERIFICATION_FAILED_PARSE"
            self.log_action(state, "VERIFICATION_FAILED_PARSE", "Failed to parse critique output.")
            
        return state