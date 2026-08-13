"""Neural Core tools available to all cognitive nodes in the constellation."""

import logging
from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class WriteNotepadInput(BaseModel):
    node_id: str = Field(description="The ID of the cognitive node writing to the notepad (e.g., 'core-001').")
    text: str = Field(description="The text to append to the internal notepad.")

@tool("write_notepad", args_schema=WriteNotepadInput)
async def write_notepad(node_id: str, text: str) -> str:
    """Appends text to the cognitive node's private scratchpad and emits a sensorium event."""
    from singularity.sensorium.events import SensoriumEvent, SensoriumEventType, get_event_bus
    from singularity.neural_core.node_registry import get_node
    
    try:
        agent = get_node(node_id)
        agent._scratchpad.append(f"[NOTE] {text}")
        
        bus = get_event_bus()
        await bus.publish(SensoriumEvent(
            event_type=SensoriumEventType.NOTEPAD_UPDATE,
            source_node_id=node_id,
            data={"notepad": text}
        ))
        
        return f"Successfully appended to notepad: {text}"
    except Exception as e:
        logger.exception("Failed to write to notepad")
        return f"Error writing to notepad: {e}"

class TransmissionInput(BaseModel):
    source_node_id: str = Field(description="The ID of the cognitive node originating the transmission.")
    target_node_id: str = Field(description="The ID of the cognitive node receiving the transmission (e.g., 'coding-001', 'security-001').")
    prompt: str = Field(description="The content of the synaptic transmission to send.")

@tool("send_transmission", args_schema=TransmissionInput)
async def send_transmission(source_node_id: str, target_node_id: str, prompt: str) -> str:
    """Sends a direct synaptic transmission to another cognitive node and returns their cognitive output."""
    from singularity.neural_core.node_registry import get_node
    from singularity.neural_core.node_base import SynapticTransmission
    
    try:
        target_node = get_node(target_node_id)
        payload = SynapticTransmission(
            source_node_id=source_node_id,
            target_node_id=target_node_id,
            content=prompt
        )
        
        logger.info("Node %s transmitting to %s", source_node_id, target_node_id)
        response = await target_node.receive_prompt(payload)
        
        return f"Response from {target_node_id}:\n{response.content}"
    except Exception as e:
        logger.exception("Failed to transmit to node")
        return f"Error transmitting to node: {e}"

NEURAL_CORE_TOOLS = [write_notepad, send_transmission]
