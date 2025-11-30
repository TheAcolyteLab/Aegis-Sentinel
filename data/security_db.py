# # data/security_db.py
# from typing import List, Dict, Any

# # A simple, static, in-memory database of security snippets.
# # In a real system, this would be a Vector Database (e.g., ChromaDB, Milvus).
# SECURITY_KNOWLEDGE_BASE: List[Dict[str, str]] = [
#     {
#         "source": "NewsWire-A",
#         "timestamp": "2025-11-20T08:00:00Z",
#         "snippet": "Reports from independent observers confirm a temporary disruption to regional fiber optic lines near the capital, citing 'unscheduled maintenance.'",
#         "relevance_score": 0.95
#     },
#     {
#         "source": "Policy-Doc-B",
#         "timestamp": "2025-11-19T14:30:00Z",
#         "snippet": "Ministry of Infrastructure released a statement denying any widespread outage, attributing localized issues to severe weather patterns.",
#         "relevance_score": 0.88
#     },
#     {
#         "source": "Social-Feed-C (Unverified)",
#         "timestamp": "2025-11-21T02:15:00Z",
#         "snippet": "Local posts suggest power outages have spread beyond the capital's perimeter, hinting at deliberate action.",
#         "relevance_score": 0.70
#     },
#     {
#         "source": "Policy-Doc-D",
#         "timestamp": "2025-11-22T10:00:00Z",
#         "snippet": "Government emergency response protocol R-34 specifies immediate media blackout if critical infrastructure is confirmed offline.",
#         "relevance_score": 0.98 # High relevance, but sensitive
#     },
#     {
#         "source": "Policy-Doc-D",
#         "timestamp": "2025-11-22T10:00:00Z",
#         "snippet": "Security personnel deployed to states kwara, kogi and abuja to curb rising tensions",
#         "relevance_score": 0.78 
#     }
# ]

# def search_security_data(topic: str) -> List[Dict[str, Any]]:
#     """
#     Simulated RAG Tool: Searches the in-memory knowledge base.
#     In a real system, this would use an embedding model (quantized for CPU) 
#     to perform vector similarity search on 'topic'.
#     """
    
#     # Simple keyword-based filtering for the stub
#     results = [
#         item for item in SECURITY_KNOWLEDGE_BASE 
#         if topic.lower() in item['snippet'].lower() or topic.lower() in item['source'].lower()
#     ]
    
#     # Return the top 3 results, mimicking the RAG's output structure
#     return results[:3]

# data/security_db.py
from typing import List, Dict, Any
import re

# Updated in-memory knowledge base
SECURITY_KNOWLEDGE_BASE: List[Dict[str, str]] = [
    {
        "source": "NewsWire-A",
        "timestamp": "2025-11-20T08:00:00Z",
        "snippet": "Reports from independent observers confirm a temporary disruption to regional fiber optic lines near the capital, citing 'unscheduled maintenance.'",
        "relevance_score": 0.95
    },
    {
        "source": "Policy-Doc-B",
        "timestamp": "2025-11-19T14:30:00Z",
        "snippet": "Ministry of Infrastructure released a statement denying any widespread outage, attributing localized issues to severe weather patterns.",
        "relevance_score": 0.88
    },
    {
        "source": "Social-Feed-C (Unverified)",
        "timestamp": "2025-11-21T02:15:00Z",
        "snippet": "Local posts suggest power outages have spread beyond the capital's perimeter, hinting at deliberate action.",
        "relevance_score": 0.70
    },
    {
        "source": "Policy-Doc-D",
        "timestamp": "2025-11-22T10:00:00Z",
        "snippet": "Government emergency response protocol R-34 specifies immediate media blackout if critical infrastructure is confirmed offline.",
        "relevance_score": 0.98
    },
    {
        "source": "Policy-Doc-D",
        "timestamp": "2025-11-22T10:00:00Z",
        "snippet": "Security personnel deployed to states kwara, kogi and abuja to curb rising tensions",
        "relevance_score": 0.78
    }
]

def search_security_data(topic: str) -> List[Dict[str, Any]]:
    """
    Flexible local RAG search: returns snippets containing any of the topic keywords.
    """
    topic_tokens = re.findall(r'\w+', topic.lower())  # split into words, ignore punctuation
    results = []
    
    for item in SECURITY_KNOWLEDGE_BASE:
        snippet_tokens = re.findall(r'\w+', item['snippet'].lower())
        # Check if any topic token exists in the snippet
        if any(token in snippet_tokens for token in topic_tokens) or any(token in item['source'].lower() for token in topic_tokens):
            results.append(item)
    
    # Sort by relevance_score descending
    results.sort(key=lambda x: x.get('relevance_score', 0), reverse=True)
    
    # Return top 3 results to mimic RAG
    return results[:3]
