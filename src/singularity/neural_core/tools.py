"""Core tools available to all orbital node agents in the constellation."""

import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WriteNotepadInput(BaseModel):
    node_id: str = Field(description="The ID of the agent writing to the notepad (e.g., 'core-001').")
    text: str = Field(description="The text to append to the internal notepad.")

@tool("write_notepad", args_schema=WriteNotepadInput)
async def write_notepad(node_id: str, text: str) -> str:
    """Appends text to the agent's internal notepad and pushes it to the UI."""
    from singularity.sensorium.events import TelemetryEvent, TelemetryEventType, get_event_bus
    from singularity.neural_core.node_registry import get_agent
    
    try:
        agent = get_agent(node_id)
        agent._scratchpad.append(f"[NOTE] {text}")
        
        bus = get_event_bus()
        await bus.publish(TelemetryEvent(
            event_type=TelemetryEventType.NOTEPAD_UPDATE,
            source_node_id=node_id,
            data={"notepad": text}
        ))
        
        return f"Successfully appended to notepad: {text}"
    except Exception as e:
        logger.exception("Failed to write to notepad")
        return f"Error writing to notepad: {e}"

class PromptAgentInput(BaseModel):
    source_node_id: str = Field(description="The ID of the agent sending the prompt.")
    target_node_id: str = Field(description="The ID of the agent receiving the prompt (e.g., 'coding-001', 'security-001').")
    prompt: str = Field(description="The directive or prompt content to send.")

@tool("synapse_node", args_schema=PromptAgentInput)
async def synapse_node(source_node_id: str, target_node_id: str, prompt: str) -> str:
    """Sends a direct prompt to another agent in the constellation and returns their response."""
    from singularity.neural_core.node_registry import get_agent
    from singularity.neural_core.node_base import SynapticTransmission
    
    try:
        target_agent = get_agent(target_node_id)
        payload = SynapticTransmission(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            content=prompt
        )
        
        logger.info("Agent %s is directly prompting %s", source_node_id, target_node_id)
        response = await target_agent.receive_prompt(payload)
        
        return f"Response from {target_node_id}:\n{response.content}"
    except Exception as e:
        logger.exception("Failed to prompt agent")
        return f"Error prompting agent: {e}"

CORE_TOOLS = [write_notepad, synapse_node]
