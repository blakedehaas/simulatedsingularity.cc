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
    """Evaluate if the end condition has been met (Stateless)."""
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
    """Poll an agent to see if they want to interject (Stateless intent polling)."""
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
    """Run the non-linear event-driven loop for a language-based simulation using Interactions API."""
    logger.info(f"Starting non-linear simulation loop for session {session_id}")
    
    client = genai.Client()
    
    agents_config = config.agents_config
    if not isinstance(agents_config, list) or len(agents_config) == 0:
        logger.error(f"agents_config must be a non-empty list")
        return
        
    try:
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
        canonical_interaction_id = None
        
        while True:
            history_text = "\n".join([f"{msg['sender']}: {msg['content']}" for msg in history])
            
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
                        await queue.put((-priority, fifo_counter, agent_name, message))
                        fifo_counter += 1
                        
            if queue.empty():
                logger.info("Deadlock: Queue empty. Forcing first agent to speak.")
                agent = agents_config[0]
                agent_name = agent.get("name", "UnknownAgent")
                system_prompt = agent.get("system_prompt", "")
                
                # Execute canonical turn
                try:
                    kwargs = {
                        "model": "gemini-2.5-flash-8b",
                        "contents": "The conversation has stalled. Provide your next response.",
                        "config": {"system_instruction": system_prompt, "store": True}
                    }
                    if canonical_interaction_id:
                        kwargs["config"]["previous_interaction_id"] = canonical_interaction_id
                    else:
                        kwargs["contents"] = f"History:\n{history_text}\n\n" + kwargs["contents"]
                        
                    response = await asyncio.to_thread(client.interactions.create, **kwargs)
                    reply = response.text.strip()
                    canonical_interaction_id = getattr(response, "name", getattr(response, "id", None))
                    await queue.put((-10, fifo_counter, agent_name, reply))
                    fifo_counter += 1
                except Exception as e:
                    logger.error(f"Error forcing response: {e}")
                    return

            neg_prio, _, winner_name, winner_message = await queue.get()
            logger.info(f"Agent {winner_name} interjects with priority {-neg_prio}")
            
            # If it wasn't a forced turn, we need to append the winning message to the canonical interaction
            if neg_prio != -10:
                agent = next((a for a in agents_config if a.get("name") == winner_name), agents_config[0])
                system_prompt = agent.get("system_prompt", "")
                
                try:
                    kwargs = {
                        "model": "gemini-2.5-flash-8b",
                        "contents": f"Your generated interjection was: {winner_message}\nAccept this as your turn and continue.",
                        "config": {"system_instruction": system_prompt, "store": True}
                    }
                    if canonical_interaction_id:
                        kwargs["config"]["previous_interaction_id"] = canonical_interaction_id
                    else:
                        kwargs["contents"] = f"History:\n{history_text}\n\n" + kwargs["contents"]
                        
                    response = await asyncio.to_thread(client.interactions.create, **kwargs)
                    # We don't use response.text here because the message was already generated by the intent poll.
                    # This call merely advances the server-side state.
                    canonical_interaction_id = getattr(response, "name", getattr(response, "id", None))
                except Exception as e:
                    logger.error(f"Error updating canonical interaction state: {e}")
            
            async with get_session() as db:
                new_msg = SimulationMessage(
                    session_id=session_id,
                    sender=winner_name,
                    content=winner_message
                )
                db.add(new_msg)
                
            history.append({"sender": winner_name, "content": winner_message})
            
            if config.end_state_condition:
                new_history_text = "\n".join([f"{m['sender']}: {m['content']}" for m in history])
                met = await evaluate_end_condition(client, config.end_state_condition, new_history_text)
                if met:
                    logger.info(f"End condition met for session {session_id}. Terminating simulation.")
                    return
                    
    except Exception as e:
        logger.error(f"Fatal error in non-linear loop for session {session_id}: {e}")
