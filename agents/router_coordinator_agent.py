# agents/router_coordinator_agent.py
import requests
import json
from agents.base_agent import BaseAgent, tracer
from agents.data_retrival_agent import DataRetrievalAgent
from agents.sysnthesis_agent import SynthesisAgent
from agents.output_filter_agent import OutputFilterAgent
from agents.verification_agent import VerificationAgent
from shared_models import MissionState
from typing import Dict, List, Any

# --- LLM Communication Function (Uses local Ollama server) ---
def call_ollama_for_plan(prompt: str) -> str:
    """Calls the local Ollama API to generate a structured plan."""
    # This is highly efficient on CPU because the model is quantized
    
    API_URL = "http://localhost:11434/api/generate"
    
    # Request body for Ollama
    payload = {
        "model": "gemma:2b", # Target the small, fast model
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1, # Keep generation deterministic for planning
            "num_predict": 512  # Limit tokens to save CPU cycles
        }
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=300)
        response.raise_for_status() # Raise exception for bad status codes
        
        # Ollama returns a JSON response structure
        result = response.json()
        
        # The actual generation is in the 'response' field
        return result['response'].strip()
        
    except requests.exceptions.RequestException as e:
        # Crucial for Robustness: If Ollama is down, report the error, not a plan
        print(f"Ollama API Error: {e}")
        return "ERROR: LLM API connection failed." 
# --- End LLM Communication Function ---

class RouterCoordinatorAgent(BaseAgent):
    AGENT_MAP = {
        "DataRetrievalAgent": DataRetrievalAgent(agent_id="DR-1",name="Data Retrival Agent"),
        "SynthesisAgent": SynthesisAgent(agent_id="SYN-1",name="Synthesis Agent"),
        "OutputFilterAgent": OutputFilterAgent(agent_id="FILTER-1",name="Filter Agent"),
        "VerificationAgent": VerificationAgent(agent_id="VER-1",name="Verifier Agent"), 
    }

    def __init__(self, name: str, agent_id: str, sub_agents: Dict[str, BaseAgent], **kwargs):
        
        # 1. Initialize the parent (BaseAgent)
        super().__init__(name=name, agent_id=agent_id, **kwargs) 
        
        # 2. CRITICAL: Store the sub_agents dictionary to the instance
        self.sub_agents: Dict[str, BaseAgent] = sub_agents
    
    def run(self, state: MissionState) -> MissionState:
        """
        Orchestrates the entire mission workflow by sequencing agent execution.
        """
        self.log_action(state, "COORDINATOR_START", "Beginning mission orchestration.")
        
        current_step = 1
        
        while state.status != "COMPLETED" and state.status != "TERMINATED":
            
            self.log_action(state, "COORDINATOR_PLAN", f"Executing step {current_step} based on current state.")
            
            # 1. Determine the next step (e.g., call LLM to decide the next agent/action)
            # For simplicity, we'll hardcode a pipeline:
            
            if state.status == "MISSION_INITIALIZED" or state.status == "REPLANNING_NEEDED":
                # Step 1: Data Retrieval
                agent_key = "retrieval"
                plan_step = {"input": state.user_query}
                
            elif state.status == "RETRIEVAL_EMPTY":
              
                self.log_action(
                    state,
                    "COORDINATOR_CONTINUE",
                    "No retrieval results — proceeding to Synthesis for a 'No Findings' report."
                )
                agent_key = "synthesis"
                state.status = "RETRIEVING_COMPLETE"
                plan_step = {"input": "Synthesize an empty retrieval result into a 'No Findings' draft report."}
   
            elif state.status == "RETRIEVING_COMPLETE":
                # Step 2: Synthesis/Drafting
                agent_key = "synthesis"
                plan_step = {"input": "Synthesize data into a draft report."}
            
            elif state.status == "SYNTHESIS_COMPLETE":
                # Step 3: Output Filtering/PII Masking
                agent_key = "filter"
                plan_step = {"input": state.draft_report}

            elif state.status == "FILTERING_COMPLETE":
                # Step 4: Verification/Critique
                agent_key = "verification"
                plan_step = {"input": state.draft_report}
                
            elif state.status == "VERIFICATION_PASS":
                # Final State
                state.status = "COMPLETED"
                break

            elif state.status == "VERIFICATION_FAIL_CRITICAL":
                # Handle failure: This would usually trigger a detailed replanning or simply stop.
                state.status = "TERMINATED"
                self.log_action(state, "COORDINATOR_END", "Mission terminated due to critical verification failure.")
                break
            
            else:
                # Fallback for unexpected status
                state.status = "TERMINATED"
                self.log_action(state, "COORDINATOR_END", f"Mission terminated due to unhandled status: {state.status}.")
                break
                
            # 2. Execute the delegated agent
            self.log_action(state, "COORDINATOR_DELEGATE", f"Delegating to {self.sub_agents[agent_key].name}")
            
            # The agent is retrieved from the sub_agents map and its execute method is called
            # Note: The sub_agents dictionary was passed to the __init__ of the Coordinator
            agent_to_run = self.sub_agents[agent_key]
            state = agent_to_run.execute(state, plan_step)
            
            current_step += 1
            
        self.log_action(state, "COORDINATOR_END", f"Mission concluded with final status: {state.status}.")
        return state

    def _plan_mission(self, state: MissionState) -> MissionState:
        # 1. Logic for PLANNING_START
        self.log_action(state, "PLANNING_START", f"Starting mission for query: {state.user_query}")
        state.status = "PLANNING"
        
        planning_prompt = f"""
        ... (full planning prompt as before) ...
        """
        
        # 2. Call the LLM with Tracing
        with tracer.start_as_current_span("Router_LLM_Call") as span:
            full_prompt = planning_prompt + f"\nUser Query: {state.user_query}"
            raw_plan_output = call_ollama_for_plan(full_prompt)
            span.set_attribute("llm.model", "gemma:2b")
            
        # 3. Process the Output
        if raw_plan_output.startswith("ERROR"):
            state.status = "PLANNING_FAILED"
            self.log_action(state, "PLANNING_FAILED", raw_plan_output)
            return state

        try:
            agent_plan = json.loads(raw_plan_output)
            state.plan = agent_plan
            state.status = "PLANNING_SUCCESS"
            self.log_action(state, "PLANNING_SUCCESS", "Generated and validated the mission plan.", {"plan_length": len(agent_plan)})
        except json.JSONDecodeError as e:
            state.status = "PLANNING_FAILED"
            self.log_action(state, "PLANNING_FAILED", f"Failed to parse LLM's plan output.", {"error": str(e), "raw_output": raw_plan_output})

        return state
        
    # --- The main Execution and Coordination Method ---
    def execute(self, state: MissionState) -> MissionState:
        
        # 1. Initial Planning (or resumtion from previous state)
        if state.status == "INITIALIZED" or state.status == "PLANNING":
            state = self._plan_mission(state)
            if state.status != "PLANNING_SUCCESS": return state

        # 2. Re-Planning/Revision Loop (Robustness Check II)
        if state.status == "VERIFICATION_FAIL_CRITICAL":
            # If the critique failed, we initiate a new sub-plan to fix it
            self.log_action(state, "REVISION_LOOP_START", "Verification failed. Generating a new sub-plan for Synthesis Agent revision.")
            
            # Simple fixed revision plan: Go back to synthesis, then filter, then verify again
            revision_plan = [
                {"task_id": "REV-1", "agent": "SynthesisAgent", "input": "Revision based on previous critique."},
                {"task_id": "REV-2", "agent": "OutputFilterAgent", "input": "Re-filter after revision."},
                {"task_id": "REV-3", "agent": "VerificationAgent", "input": "Final verification."},
            ]
            
            # Replace current plan steps with the revision plan
            state.plan = revision_plan
            state.status = "TASK_COMPLETE" # Set to TASK_COMPLETE to start the new loop iteration
        # Ensure we only proceed if planning was successful or a task just finished
        if state.status == "PLANNING_SUCCESS" or state.status == "TASK_COMPLETE":
            
            # Identify tasks already completed based on the mission trajectory
            executed_task_ids = [entry.data['task_id'] for entry in state.execution_trajectory if entry.action_type == "TASK_COMPLETE"]

            for step in state.plan:
                if step["task_id"] not in executed_task_ids:
                    
                    target_agent_id = step["agent"]
                    task_id = step["task_id"]
                    
                    self.log_action(state, "DELEGATING_TASK", f"Delegating {task_id} to {target_agent_id}", {"task_id": task_id})
                    state.status = f"EXECUTING_{target_agent_id}"

                    # --- Delegation and Execution ---
                    if target_agent_id in self.AGENT_MAP:
                        agent_instance = self.AGENT_MAP[target_agent_id]
                        
                        # Execute the specialized agent, passing the required task step
                        state = agent_instance.execute(state, plan_step=step) 

                        # Check for FAILURE (Robustness Mandate)
                        if state.status.endswith("_FAILED"):
                            self.log_action(state, "MISSION_FAILURE", f"Mission halted at {task_id} due to agent failure: {state.status}.")
                            return state 
                        
                        # Mark task as complete and return to main loop
                        self.log_action(state, "TASK_COMPLETE", f"Task {task_id} executed successfully.", {"task_id": task_id})
                        state.status = "TASK_COMPLETE"
                        return state # Return state to allow external process to resume/check next step

            # If the loop completes, all tasks are done
            self.log_action(state, "MISSION_SUCCESS", "All planned tasks completed. Awaiting final output assembly.")
            state.status = "COMPLETED_PLAN" # Use a distinct status for completion

        # If the loop completes successfully:
            if state.status == "VERIFICATION_PASS":
                self.log_action(state, "MISSION_COMPLETE", "Mission fully verified and ready for delivery.")
                state.status = "FINAL_REPORT_READY"
                return state
                
            # If all original tasks are completed but not final:
            if all(step["task_id"] in executed_task_ids for step in state.plan):
                self.log_action(state, "MISSION_HALTED", "All steps executed, but final status not reached or pending.")   
        return state