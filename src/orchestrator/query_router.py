import re
from typing import List, Dict, Optional
from enum import Enum

class IntentType(Enum):
    RETRIEVAL = "RETRIEVAL_INTENT"
    COMPUTATION = "COMPUTATION_INTENT"
    HYBRID = "HYBRID_INTENT"

class QueryRoutingController:
    """
    Deterministic intent classifier based on action words.
    Does NOT use subject-based keyword detection.
    """
    
    ACTION_WORDS = {
        IntentType.RETRIEVAL: [
            r"quote", r"copy", r"find", r"locate", r"identify", 
            r"what is", r"where is", r"extract", r"show the line", r"provide verbatim"
        ],
        IntentType.COMPUTATION: [
            r"calculate", r"compute", r"derive", r"compare numerically", 
            r"determine growth", r"compute ratio", r"score", 
            r"analyze trend", r"perform piotroski", r"calculate fcf", r"evaluate margin"
        ]
    }

    def classify_intent(self, query: str) -> IntentType:
        q = query.lower()
        
        has_retrieval = any(re.search(word, q) for word in self.ACTION_WORDS[IntentType.RETRIEVAL])
        has_computation = any(re.search(word, q) for word in self.ACTION_WORDS[IntentType.COMPUTATION])
        
        if has_retrieval and has_computation:
            return IntentType.HYBRID
        
        if has_computation:
            return IntentType.COMPUTATION
        
        if has_retrieval:
            return IntentType.RETRIEVAL
            
        # STEP 4: FAILSAFE - Default to RETRIEVAL_INTENT
        return IntentType.RETRIEVAL

    def route_query(self, query: str) -> Dict[str, any]:
        intent = self.classify_intent(query)
        
        # This metadata helps the executor follow STEP 2 routing rules
        return {
            "intent": intent.value,
            "query": query,
            "requires_retrieval": True, # Always true for all intents as per forensic rules
            "requires_computation": intent in [IntentType.COMPUTATION, IntentType.HYBRID],
            "requires_interpretation": True
        }
