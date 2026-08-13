"""Critic Weaver Agent - Evaluates output utility for the evolutionary engine."""

import logging

logger = logging.getLogger(__name__)

def evaluate_output(content: str) -> float:
    """Evaluate output utility and return a reward scalar (0.0 to 1.0)."""
    length = len(content)
    if length == 0:
        return 0.01
        
    score = 0.5
    
    # Keyword-based heuristics
    if "error" in content.lower() or "exception" in content.lower():
        score -= 0.3
    if "success" in content.lower() or "resolved" in content.lower():
        score += 0.2
        
    # Length heuristic (prefer slightly longer, detailed responses, up to a point)
    if length > 50:
        score += 0.1
    if length > 200:
        score += 0.1
        
    # Ensure bounds
    score = max(0.0, min(1.0, score))
    logger.debug(f"Critic Weaver evaluated output (len={length}) -> score={score}")
    
    return score
