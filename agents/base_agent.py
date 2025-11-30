# agents/base_agent.py (Includes setup for structured logging)
from typing import Any, Dict, Optional
import structlog
import logging
from opentelemetry import trace, context
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.resources import Resource # Used for service naming
from shared_models import MissionState, LogEntry

# --- Global Observability Setup ---
# 1. Structured Logging Configuration (JSON for machine readability)
def configure_logging():
    structlog.configure(
        processors=[
            structlog.stdlib.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.JSONRenderer(), # Renders output as JSON
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )
    # Basic Python logging handler to catch structlog output
    logging.basicConfig(level=logging.INFO, format="%(message)s")

# 2. OpenTelemetry Tracing Setup (Minimal, CPU-friendly setup)
resource = Resource.create({"service.name": "ssia-multi-agent"})
provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)
tracer = trace.get_tracer("ssia.agents")

configure_logging() 
logger = structlog.get_logger()
# --- End Global Setup ---

class BaseAgent:
    # ... (rest of the BaseAgent class as defined in the initial blueprint) ..
    def __init__(self, name: str, agent_id: str, **kwargs):
        self.name: str = name
        self.agent_id: str = agent_id

        self.logger = logger.bind(agent_name=self.name, agent_id=self.agent_id)
   
        self.extra_config = kwargs
       
    # Key function:
    def log_action(self, state: MissionState, action_type: str, reasoning: str, data: Optional[Dict[str, Any]] = None):
        """Captures structured log (Pillar 1: Logging) and updates the mission trajectory."""
        
        # Inject Trace and Span IDs if a span is active (Pillar 2: Tracing)
        current_span = trace.get_current_span()
        span_context = current_span.get_span_context()
        
        # Now use the retrieved context for formatting
        if span_context.is_valid:
            trace_id = format(span_context.trace_id, "x")
            span_id = format(span_context.span_id, "x")
        else:
            trace_id = "N/A"
            span_id = "N/A"

        # 1. Structured Logging
        logger.info(
            "AgentAction",
            agent_id=self.agent_id,
            mission_id=state.mission_id,
            action_type=action_type,
            reasoning=reasoning,
            trace_id=trace_id, 
            span_id=span_id,
            **data or {}
        )
        
        # 2. Update the Trajectory
        log_entry = LogEntry(
             # ALL ARGUMENTS MUST BE PASSED AS KEYWORDS
             agent_id=self.agent_id,
             action_type=action_type,
             reasoning=reasoning,
                # Assuming these fields exist in LogEntry:
             trace_id=trace_id, 
             span_id=span_id,
             data=data
            )
        state.execution_trajectory.append(log_entry)
        
    def execute(self, state: MissionState) -> MissionState:
        """The main method for the agent to execute its task."""
        # Must be overridden by subclasses
        ...