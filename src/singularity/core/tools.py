"""Core tools available to all orbital node agents in the constellation."""

import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WriteNotepadInput(BaseModel):
    agent_id: str = Field(description="The ID of the agent writing to the notepad (e.g., 'core-001').")
    text: str = Field(description="The text to append to the internal notepad.")

@tool("write_notepad", args_schema=WriteNotepadInput)
async def write_notepad(agent_id: str, text: str) -> str:
    """Appends text to the agent's internal notepad and pushes it to the UI."""
    from singularity.telemetry.events import TelemetryEvent, TelemetryEventType, get_event_bus
    from singularity.core.agent_registry import get_agent
    
    try:
        agent = get_agent(agent_id)
        agent._scratchpad.append(f"[NOTE] {text}")
        
        bus = get_event_bus()
        await bus.publish(TelemetryEvent(
            event_type=TelemetryEventType.NOTEPAD_UPDATE,
            source_agent_id=agent_id,
            data={"notepad": text}
        ))
        
        return f"Successfully appended to notepad: {text}"
    except Exception as e:
        logger.exception("Failed to write to notepad")
        return f"Error writing to notepad: {e}"

class PromptAgentInput(BaseModel):
    source_agent_id: str = Field(description="The ID of the agent sending the prompt.")
    target_agent_id: str = Field(description="The ID of the agent receiving the prompt (e.g., 'coding-001', 'security-001').")
    prompt: str = Field(description="The directive or prompt content to send.")

@tool("prompt_agent", args_schema=PromptAgentInput)
async def prompt_agent(source_agent_id: str, target_agent_id: str, prompt: str) -> str:
    """Sends a direct prompt to another agent in the constellation and returns their response."""
    from singularity.core.agent_registry import get_agent
    from singularity.core.agent_base import PromptPayload
    
    try:
        target_agent = get_agent(target_agent_id)
        payload = PromptPayload(
            source_agent_id=source_agent_id,
            target_agent_id=target_agent_id,
            content=prompt
        )
        
        logger.info("Agent %s is directly prompting %s", source_agent_id, target_agent_id)
        response = await target_agent.receive_prompt(payload)
        
        return f"Response from {target_agent_id}:\n{response.content}"
    except Exception as e:
        logger.exception("Failed to prompt agent")
        return f"Error prompting agent: {e}"

CORE_TOOLS = [write_notepad, prompt_agent]
