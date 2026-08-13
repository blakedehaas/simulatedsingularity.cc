"""Language-based simulation core logic."""

import asyncio
import logging
import json
import base64
from typing import Any

from google import genai

from singularity.persistence.database import get_session
from singularity.persistence.models import (
    LanguageSimulationConfig,
    SimulationMessage,
)

logger = logging.getLogger(__name__)

def parse_content_to_parts(content: str) -> list[Any]:
    """Parse JSON string into a list of Gemini Parts for multi-modal support."""
    parts = []
    try:
        parsed = json.loads(content)
        if isinstance(parsed, list):
            for item in parsed:
                if "text" in item:
                    parts.append(genai.types.Part.from_text(item["text"]))
                elif "inlineData" in item:
                    mime = item["inlineData"].get("mimeType", "")
                    data_b64 = item["inlineData"].get("data", "")
                    data_bytes = base64.b64decode(data_b64)
                    parts.append(genai.types.Part.from_bytes(data=data_bytes, mime_type=mime))
        else:
            parts.append(genai.types.Part.from_text(content))
    except Exception:
        parts.append(genai.types.Part.from_text(str(content)))
    return parts

def build_history_parts(history: list[dict[str, Any]]) -> list[Any]:
    parts = []
    for msg in history:
        parts.append(genai.types.Part.from_text(f"{msg['sender']}:\n"))
        parts.extend(parse_content_to_parts(msg['content']))
        parts.append(genai.types.Part.from_text("\n\n"))
    return parts

async def evaluate_end_condition(client: genai.Client, condition: str, history_parts: list[Any]) -> bool:
    """Evaluate if the end condition has been met (Stateless)."""
    prompt = f"Based on the history, has this condition been met? Condition: {condition}\nAnswer YES or NO (and nothing else)."
    
    contents = [genai.types.Part.from_text("You are an evaluator for a simulation. History:\n")]
    contents.extend(history_parts)
    contents.append(genai.types.Part.from_text("\n\n" + prompt))
    
    try:
        response = await asyncio.to_thread(
            client.interactions.create,
            model="gemini-2.5-flash-8b",
            contents=contents,
            config={"store": False}
        )
        text = response.text.strip().upper()
        return "YES" in text
    except Exception as e:
        logger.error(f"Error evaluating end condition: {e}")
        return False

async def generate_interjection_intent(client: genai.Client, agent_name: str, system_prompt: str, history_parts: list[Any], verbose_mode: bool) -> dict[str, Any]:
    """Poll an agent to see if they want to interject (Stateless intent polling unless verbose)."""
    prompt_text = (
        f"Do you want to speak next? If you have nothing to say, output exactly: {{\"intent\": \"PASS\"}}\n"
        f"If you want to interject, output a JSON object: {{\"intent\": \"INTERJECT\", \"priority\": <1-10>, \"message\": \"<your response>\"}}\n"
        f"Higher priority (10) means it is urgent for you to speak. Output ONLY valid JSON."
    )
    
    contents = [genai.types.Part.from_text(f"You are {agent_name}. Here is the simulation history:\n")]
    contents.extend(history_parts)
    contents.append(genai.types.Part.from_text("\n\n" + prompt_text))

    try:
        response = await asyncio.to_thread(
            client.interactions.create,
            model="gemini-2.5-flash-8b",
            contents=contents,
            config={"system_instruction": system_prompt, "store": verbose_mode}
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
        verbose_mode = getattr(config, 'verbose_mode', False)
        
        while True:
            history_parts = build_history_parts(history)
            
            logger.info(f"Polling {len(agents_config)} agents for interjection intents...")
            tasks = [
                generate_interjection_intent(
                    client, 
                    agent.get("name", "UnknownAgent"), 
                    agent.get("system_prompt", ""), 
                    history_parts,
                    verbose_mode
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
                
                try:
                    kwargs = {
                        "model": "gemini-2.5-flash-8b",
                        "contents": "The conversation has stalled. Provide your next response.",
                        "config": {"system_instruction": system_prompt, "store": True}
                    }
                    if canonical_interaction_id:
                        kwargs["config"]["previous_interaction_id"] = canonical_interaction_id
                    else:
                        kwargs["contents"] = [genai.types.Part.from_text("History:\n")] + history_parts + [genai.types.Part.from_text("\n\n" + kwargs["contents"])]
                        
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
                        kwargs["contents"] = [genai.types.Part.from_text("History:\n")] + history_parts + [genai.types.Part.from_text("\n\n" + kwargs["contents"])]
                        
                    response = await asyncio.to_thread(client.interactions.create, **kwargs)
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
                met = await evaluate_end_condition(client, config.end_state_condition, history_parts)
                if met:
                    logger.info(f"End condition met for session {session_id}. Terminating simulation.")
                    return
                    
    except Exception as e:
        logger.error(f"Fatal error in non-linear loop for session {session_id}: {e}")
