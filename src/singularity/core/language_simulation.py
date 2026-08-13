"""Language-based simulation core logic."""

import asyncio
import logging
from typing import Any

from google import genai

from singularity.persistence.database import get_session
from singularity.persistence.models import (
    LanguageSimulationConfig,
    SimulationMessage,
)

logger = logging.getLogger(__name__)

async def evaluate_end_condition(client: genai.Client, condition: str, history_text: str) -> bool:
    """Evaluate if the end condition has been met."""
    prompt = (
        f"You are an evaluator for a simulation.\n"
        f"Based on the following history of a conversation, has this condition been met?\n"
        f"Condition: {condition}\n\n"
        f"History:\n{history_text}\n\n"
        f"Answer YES or NO (and nothing else)."
    )
    
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash",
            contents=prompt,
        )
        text = response.text.strip().upper()
        return "YES" in text
    except Exception as e:
        logger.error(f"Error evaluating end condition: {e}")
        return False


async def run_simulation_loop(session_id: str, config: LanguageSimulationConfig) -> None:
    """Run the main loop for a language-based simulation.
    
    Args:
        session_id: The ID of the simulation session.
        config: The configuration for the simulation.
    """
    logger.info(f"Starting language simulation loop for session {session_id}")
    
    client = genai.Client()
    
    agents_config = config.agents_config
    if not isinstance(agents_config, list):
        logger.error(f"agents_config must be a list, got {type(agents_config)}")
        return
        
    try:
        # Load existing messages if any
        history: list[dict[str, Any]] = []
        async with get_session() as db:
            seed_msg = SimulationMessage(
                session_id=session_id,
                sender="system",
                content=config.seed_prompt
            )
            db.add(seed_msg)
            
        history.append({"sender": "system", "content": config.seed_prompt})
        
        while True:
            for agent in agents_config:
                agent_name = agent.get("name", "UnknownAgent")
                system_prompt = agent.get("system_prompt", "")
                
                logger.info(f"Generating turn for agent {agent_name} in session {session_id}")
                
                history_text = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in history])
                
                agent_prompt = (
                    f"You are {agent_name}. Your system prompt is:\n{system_prompt}\n\n"
                    f"Here is the history of the simulation so far:\n{history_text}\n\n"
                    f"Please provide your next response in the conversation. Do not prefix your response with your name, just provide your reply."
                )
                
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model="gemini-2.5-flash",
                        contents=agent_prompt,
                    )
                    reply = response.text.strip()
                    
                    async with get_session() as db:
                        new_msg = SimulationMessage(
                            session_id=session_id,
                            sender=agent_name,
                            content=reply
                        )
                        db.add(new_msg)
                        
                    history.append({"sender": agent_name, "content": reply})
                    
                    if config.end_state_condition:
                        new_history_text = "\n".join([f"{m['sender']}: {m['content']}" for m in history])
                        met = await evaluate_end_condition(client, config.end_state_condition, new_history_text)
                        if met:
                            logger.info(f"End condition met for session {session_id}. Terminating simulation.")
                            return
                            
                except Exception as e:
                    logger.error(f"Error generating response for agent {agent_name}: {e}")
                    # Continue to try next agent
                    continue
                    
    except Exception as e:
        logger.error(f"Fatal error in simulation loop for session {session_id}: {e}")
