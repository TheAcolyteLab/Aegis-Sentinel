import sys
import uuid
from shared_models import MissionState
from agents.router_coordinator_agent import RouterCoordinatorAgent
from agents.data_retrival_agent import DataRetrievalAgent
from agents.sysnthesis_agent import SynthesisAgent
from agents.output_filter_agent import OutputFilterAgent
from agents.verification_agent import VerificationAgent
def initialize_aegis_sentinel():
    """Initializes all agents and sets up the Coordinator hierarchy."""
    
    # Define individual agents (assuming they take a shared LLM client/config)
    retrieval_agent = DataRetrievalAgent(agent_id="DR-1",name="DataRetrievalAgent")
    filter_agent = OutputFilterAgent(agent_id="FILTER-1",name="OutputFilterAgent")
    synthesis_agent = SynthesisAgent(agent_id="SNY-1",name="SynthesisAgent")
    verification_agent = VerificationAgent(agent_id="VER-1",name="VerificationAgent")

    # The Coordinator is the main entry point and orchestrates the flow
    coordinator = RouterCoordinatorAgent(
        name="RouterCoordinatorAgent",
        agent_id="RC-0",
        # Pass the sub-agents so the coordinator knows who to delegate to
        sub_agents={
            "retrieval": retrieval_agent,
            "filter": filter_agent,
            "synthesis": synthesis_agent,
            "verification": verification_agent
        }
    )
    
    # In a fully connected system, the coordinator would establish communication 
    # links to all the sub-agents
    print("🤖 Aegis Sentinel Agents Initialized successfully.")
    return coordinator

# --- 2. Mission Execution ---

def run_mission(query: str):
    """Initializes the MissionState and starts the coordinated mission."""
    try:
        coordinator = initialize_aegis_sentinel()
        
        mission_state = MissionState(
            # 1. Fix 'mission_id': Generate a unique ID (required by Pydantic)
            mission_id=str(uuid.uuid4()), 
            
            # 2. Fix 'user_query': Use the correct Pydantic field name
            user_query=query, 
            
            # 3. If 'initial_query' is also required in your model, include it:
            initial_query=query, 
            
            status="MISSION_INITIALIZED"
        )
        print("-" * 50)
        print(f"🎯 Starting Mission: '{query}'")
        print("-" * 50)
        
        # 2. Run the Coordinator Agent
        # The coordinator's 'run' method executes the entire sequential pipeline
        final_state = coordinator.run(mission_state)

        # 3. Output the Final Results (The Execution Trajectory and Final Report)
        
        print("\n" + "#" * 60)
        print("MISSION COMPLETE: Execution Trajectory (Final Status)")
        print("#" * 60)
        
        # Print the final report content
        print(f"\nFINAL STATUS: {final_state.status}")
        score_display = 'N/A'
        if final_state.verification_score is not None:
             # Ensure it's treated as a float, not an object with a .score attribute
                try:
                    score_display = f"{final_state.verification_score:.1f}"
                except Exception:
                    score_display = "Invalid Score"
        
            # The field verification_score_reasoning.score does not exist, only verification_score
        print(f"VERIFICATION SCORE: {score_display}/5.0")
        report_content = final_state.final_report if final_state.final_report else "No final report generated (status: {final_state.status})."
        print(report_content) 
        # Print the log/trace for auditability
        print("\n--- AUDIT LOG / EXECUTION TRACE ---\n")
        # In the real system, final_state would contain a structured log/trace list
        print("... Trace Data goes here (showing planning, RAG calls, filter actions) ...") 

    except Exception as e:
        print(f"\n🚨 A critical error occurred during mission execution: {e}")
        sys.exit(1)


if __name__ == "__main__":
    # The script expects the mission query as a command-line argument
    if len(sys.argv) < 2:
        print("Usage: python main_runner.py \"<Your Mission Query Here>\"")
        sys.exit(1)
    
    # The query is the second argument (index 1)
    mission_query = sys.argv[1]
    run_mission(mission_query)