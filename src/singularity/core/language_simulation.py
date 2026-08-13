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
            model="gemini-2.5-flash-8b",
            contents=prompt,
        )
        text = response.text.strip().upper()
        return "YES" in text
    except Exception as e:
        logger.error(f"Error evaluating end condition: {e}")
        return False

import json

async def generate_interjection_intent(client: genai.Client, agent_name: str, system_prompt: str, history_text: str) -> dict[str, Any]:
    """Poll an agent to see if they want to interject."""
    prompt = (
        f"You are {agent_name}. Your system prompt is:\n{system_prompt}\n\n"
        f"Here is the history of the simulation so far:\n{history_text}\n\n"
        f"Do you want to speak next? If you have nothing to say, output exactly: {{\"intent\": \"PASS\"}}\n"
        f"If you want to interject, output a JSON object: {{\"intent\": \"INTERJECT\", \"priority\": <1-10>, \"message\": \"<your response>\"}}\n"
        f"Higher priority (10) means it is urgent for you to speak. Output ONLY valid JSON."
    )
    try:
        response = await asyncio.to_thread(
            client.models.generate_content,
            model="gemini-2.5-flash-8b",
            contents=prompt,
        )
        text = response.text.strip()
        # Clean up markdown code blocks if present
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        return json.loads(text.strip())
    except Exception as e:
        logger.error(f"Error getting intent for {agent_name}: {e}")
        return {"intent": "PASS"}

async def run_simulation_loop(session_id: str, config: LanguageSimulationConfig) -> None:
    """Run the non-linear event-driven loop for a language-based simulation."""
    logger.info(f"Starting non-linear simulation loop for session {session_id}")
    
    client = genai.Client()
    
    agents_config = config.agents_config
    if not isinstance(agents_config, list) or len(agents_config) == 0:
        logger.error(f"agents_config must be a non-empty list")
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
        
        fifo_counter = 0
        
        while True:
            history_text = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in history])
            
            # Poll all agents concurrently
            logger.info(f"Polling {len(agents_config)} agents for interjection intents...")
            tasks = [
                generate_interjection_intent(
                    client, 
                    agent.get("name", "UnknownAgent"), 
                    agent.get("system_prompt", ""), 
                    history_text
                )
                for agent in agents_config
            ]
            
            intents = await asyncio.gather(*tasks)
            
            queue = asyncio.PriorityQueue()
            
            for agent, intent in zip(agents_config, intents):
                agent_name = agent.get("name", "UnknownAgent")
                if intent.get("intent") == "INTERJECT":
                    try:
                        priority = int(intent.get("priority", 5))
                    except ValueError:
                        priority = 5
                    message = intent.get("message", "")
                    if message:
                        # Negate priority so higher numbers pop first
                        await queue.put((-priority, fifo_counter, agent_name, message))
                        fifo_counter += 1
                        
            if queue.empty():
                logger.info("Deadlock: Queue empty. Forcing first agent to speak.")
                # Force first agent
                agent = agents_config[0]
                agent_name = agent.get("name", "UnknownAgent")
                system_prompt = agent.get("system_prompt", "")
                
                force_prompt = (
                    f"You are {agent_name}. Your system prompt is:\n{system_prompt}\n\n"
                    f"Here is the history of the simulation so far:\n{history_text}\n\n"
                    f"The conversation has stalled. Provide your next response. Do not prefix your response with your name."
                )
                try:
                    response = await asyncio.to_thread(
                        client.models.generate_content,
                        model="gemini-2.5-flash-8b",
                        contents=force_prompt,
                    )
                    reply = response.text.strip()
                    await queue.put((-10, fifo_counter, agent_name, reply))
                    fifo_counter += 1
                except Exception as e:
                    logger.error(f"Error forcing response: {e}")
                    return # fatal

            # Pop highest priority message
            neg_prio, _, winner_name, winner_message = await queue.get()
            logger.info(f"Agent {winner_name} interjects with priority {-neg_prio}")
            
            async with get_session() as db:
                new_msg = SimulationMessage(
                    session_id=session_id,
                    sender=winner_name,
                    content=winner_message
                )
                db.add(new_msg)
                
            history.append({"sender": winner_name, "content": winner_message})
            
            # The remaining items in the queue are intentionally discarded (flushed) 
            # so agents must re-evaluate the new context on the next iteration.
            
            if config.end_state_condition:
                new_history_text = "\n".join([f"{m['sender']}: {m['content']}" for m in history])
                met = await evaluate_end_condition(client, config.end_state_condition, new_history_text)
                if met:
                    logger.info(f"End condition met for session {session_id}. Terminating simulation.")
                    return
                    
    except Exception as e:
        logger.error(f"Fatal error in non-linear loop for session {session_id}: {e}")
