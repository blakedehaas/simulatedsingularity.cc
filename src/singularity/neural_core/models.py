"""Simulated chat model for deterministic development and testing.

Provides a keyword-driven response generator that mimics LLM behavior
without requiring external API calls. Each agent type receives contextually
appropriate responses based on keyword detection in the input prompt.
"""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any

from singularity.neural_core.node_base import CognitiveOutput, NodeStatus, DiagnosticFrame

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Response templates per agent role
# ---------------------------------------------------------------------------

_RESPONSE_TEMPLATES: dict[str, dict[str, str]] = {
    "security": {
        "threat": (
            "⚠️ THREAT DETECTED — Initiating containment protocol. "
            "Isolating affected subsystems and escalating to C2 for review."
        ),
        "hack": (
            "🚨 CRITICAL ALERT — Unauthorized access pattern identified. "
            "All state-mutating operations suspended pending C2 authorization."
        ),
        "audit": (
            "📋 Security audit complete. All agent credentials verified. "
            "No anomalies detected in the current constellation state."
        ),
        "policy": (
            "🔒 Policy enforcement active. Access control rules validated "
            "across all orbital nodes. Compliance status: NOMINAL."
        ),
        "_default": (
            "🛡️ Security check: CLEAR. No threats detected in the current "
            "payload. Forwarding to Core Agent for routing."
        ),
    },
    "core": {
        "route": (
            "📡 Routing payload to designated functional agent. "
            "Priority queue updated. Estimated processing time: <2s."
        ),
        "allocate": (
            "🔧 Resource allocation adjusted. Compute budget redistributed "
            "across active orbital nodes based on current workload metrics."
        ),
        "delegate": (
            "📤 Task delegated to specialized agent. Tracking ID generated. "
            "Awaiting acknowledgment from target node."
        ),
        "_default": (
            "⚙️ Core operations nominal. Payload processed and queued "
            "for functional agent routing."
        ),
    },
    "environment": {
        "health": (
            "💚 System health: ALL NOMINAL. Container resources within "
            "acceptable thresholds. Network latency: 12ms avg."
        ),
        "container": (
            "🐳 Container status report — 3/3 active, 0 degraded. "
            "Memory utilization: 42%. CPU load: 18%."
        ),
        "network": (
            "🌐 Network diagnostics complete. All inter-node links "
            "operational. Bandwidth: 850Mbps. Packet loss: 0.001%."
        ),
        "_default": (
            "🖥️ Infrastructure status: NOMINAL. All systems operational "
            "within defined parameters."
        ),
    },
    "prompt": {
        "broadcast": (
            "📢 Broadcast dispatched to all orbital nodes. "
            "Delivery confirmed for 8/8 agents in the constellation."
        ),
        "relay": (
            "📨 Message relayed successfully. Routing path logged. "
            "Telemetry aggregation updated with latest frames."
        ),
        "heartbeat": (
            "💓 Heartbeat distribution complete. All agents synchronized "
            "to constellation clock. Next pulse in T-60s."
        ),
        "_default": (
            "📡 Comms relay operational. Message routed through standard "
            "channel. Telemetry stream active."
        ),
    },
    "memory": {
        "store": (
            "💾 Data committed to persistent storage. Write-ahead log "
            "entry created. State snapshot preserved."
        ),
        "search": (
            "🔍 Semantic search executed across memory banks. "
            "Top 5 results ranked by relevance score returned."
        ),
        "serialize": (
            "📦 Execution state serialized to flight data store. "
            "Recovery point established for interrupt resume."
        ),
        "_default": (
            "🗄️ Memory subsystem nominal. Read/write operations "
            "processing within acceptable latency bounds."
        ),
    },
    "coding": {
        "generate": (
            "🏗️ Code generation complete. Module structure defined with "
            "type annotations and docstrings. Ready for review."
        ),
        "analyze": (
            "🔬 Static analysis performed. Code complexity: LOW. "
            "No security vulnerabilities detected. Test coverage: 87%."
        ),
        "refactor": (
            "♻️ Refactoring suggestions prepared. 3 optimization "
            "opportunities identified. Backward compatibility preserved."
        ),
        "_default": (
            "👨‍💻 Coding Agent operational. Awaiting architecture directives "
            "from Core Agent for implementation tasks."
        ),
    },
    "analytical": {
        "pattern": (
            "📊 Pattern analysis complete. 2 recurring anomalies flagged "
            "for review. Confidence interval: 94.7%."
        ),
        "anomaly": (
            "🔴 Anomaly detected in telemetry stream. Deviation exceeds "
            "2σ threshold. Escalating to Security Agent."
        ),
        "metric": (
            "📈 Metric aggregation report generated. Trend analysis shows "
            "stable performance across all monitored parameters."
        ),
        "_default": (
            "📉 Analytical observation: All monitored signals within "
            "nominal ranges. No actionable deviations detected."
        ),
    },
    "creative": {
        "brainstorm": (
            "💡 Brainstorming session complete. 5 alternative approaches "
            "generated. Ranked by feasibility and innovation score."
        ),
        "innovate": (
            "🚀 Innovation proposal drafted. Novel solution pathway "
            "identified. Requires Core Agent approval for implementation."
        ),
        "alternative": (
            "🔄 Alternative strategy formulated. Divergent thinking "
            "applied to current constraint set. 3 viable options produced."
        ),
        "_default": (
            "🎨 Creative subsystem active. Ready for ideation tasks "
            "and unconventional problem-solving approaches."
        ),
    },
}


class SimulatedChatModel:
    """Deterministic keyword-driven chat model for development and testing.

    Generates contextually appropriate responses based on the agent's role
    and keywords detected in the input. No external API calls are made.

    Attributes:
        node_role: The role key used to select response templates.
        response_delay: Simulated latency in seconds (default ``0.05``).
    """

    def __init__(
        self,
        node_role: str,
        response_delay: float = 0.05,
    ) -> None:
        self.node_role = node_role.lower()
        self.response_delay = response_delay
        self._templates = _RESPONSE_TEMPLATES.get(
            self.node_role, _RESPONSE_TEMPLATES["core"]
        )

    async def generate(self, prompt_text: str) -> str:
        """Generate a simulated response based on keyword matching.

        Scans the input ``prompt_text`` for keywords defined in the
        agent's response template dictionary. Returns the first matching
        template, or the default response if no keywords match.

        Args:
            prompt_text: The input text to process.

        Returns:
            A simulated response string.
        """
        if self.response_delay > 0:
            await asyncio.sleep(self.response_delay)

        lower_prompt = prompt_text.lower()
        for keyword, response in self._templates.items():
            if keyword.startswith("_"):
                continue
            if re.search(rf"\b{re.escape(keyword)}\b", lower_prompt):
                return response

        return self._templates.get("_default", "Acknowledged. Processing.")

    def generate_sync(self, prompt_text: str) -> str:
        """Synchronous variant of :meth:`generate` for non-async contexts.

        Args:
            prompt_text: The input text to process.

        Returns:
            A simulated response string.
        """
        lower_prompt = prompt_text.lower()
        for keyword, response in self._templates.items():
            if keyword.startswith("_"):
                continue
            if re.search(rf"\b{re.escape(keyword)}\b", lower_prompt):
                return response

        return self._templates.get("_default", "Acknowledged. Processing.")

    def __repr__(self) -> str:
        return (
            f"<SimulatedChatModel role={self.node_role!r} "
            f"delay={self.response_delay}s>"
        )

import datetime

class GemmaChatModel:
    """Google GenAI LLM interface for Gemma/Gemini models."""

    def __init__(
        self,
        node_role: str = "core",
        model_name: str | None = None,
        system_prompt: str = "You are a helpful AI assistant.",
        tools: list[Any] | None = None,
    ) -> None:
        from singularity.neural_core.tools import CORE_TOOLS
        
        self.node_role = node_role
        if model_name is None:
            # Map high-speed Sensorium/Safeguard to Gemini 3.6 Flash, and deep reasoning to Pro
            if node_role.lower() in {"security", "safeguard", "sensorium", "core", "environment", "prompt"}:
                self.model_name = "gemini-3.6-flash"
            else:
                self.model_name = "gemini-1.5-pro"
        else:
            self.model_name = model_name

        self.system_prompt = system_prompt
        self.tools = tools if tools is not None else CORE_TOOLS
        self._tools_map = {t.name: t for t in self.tools}
        self._fallback_model = SimulatedChatModel(node_role=self.node_role)
        self._llm = None
        try:
            import os
            if os.getenv("GOOGLE_API_KEY"):
                from langchain_google_genai import ChatGoogleGenerativeAI
                base_llm = ChatGoogleGenerativeAI(model=self.model_name)
                if self.tools:
                    self._llm = base_llm.bind_tools(self.tools)
                else:
                    self._llm = base_llm
        except ImportError:
            pass

    def _build_messages(self, prompt_text: str) -> list[Any]:
        from langchain_core.messages import HumanMessage, SystemMessage
        return [
            SystemMessage(content=self.system_prompt),
            HumanMessage(content=prompt_text),
        ]

    async def generate(self, prompt_text: str) -> str:
        if self._llm:
            from langchain_core.messages import ToolMessage
            try:
                messages = self._build_messages(prompt_text)
                
                # Tool calling loop (max 5 iterations to prevent infinite loops)
                for _ in range(5):
                    response = await self._llm.ainvoke(messages)
                    messages.append(response)
                    
                    tool_calls = getattr(response, "tool_calls", None)
                    if not tool_calls or not isinstance(tool_calls, list):
                        content = response.content
                        if isinstance(content, list):
                            content = "".join(item.get("text", "") for item in content if isinstance(item, dict) and "text" in item)
                        elif not isinstance(content, str):
                            content = str(content)
                        return content
                        
                    for tool_call in tool_calls:
                        selected_tool = self._tools_map[tool_call["name"]]
                        tool_output = await selected_tool.ainvoke(tool_call["args"])
                        messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
                
                return "Error: Exceeded maximum tool call iterations."
            except Exception as e:
                logger.warning("GenAI API call failed (%s) — using SimulatedChatModel fallback", e)
                return await self._fallback_model.generate(prompt_text)
        return await self._fallback_model.generate(prompt_text)

    def generate_sync(self, prompt_text: str) -> str:
        if self._llm:
            from langchain_core.messages import ToolMessage
            try:
                messages = self._build_messages(prompt_text)
                
                # Tool calling loop
                for _ in range(5):
                    response = self._llm.invoke(messages)
                    messages.append(response)
                    
                    tool_calls = getattr(response, "tool_calls", None)
                    if not tool_calls or not isinstance(tool_calls, list):
                        content = response.content
                        if isinstance(content, list):
                            content = "".join(item.get("text", "") for item in content if isinstance(item, dict) and "text" in item)
                        elif not isinstance(content, str):
                            content = str(content)
                        return content
                        
                    for tool_call in tool_calls:
                        selected_tool = self._tools_map[tool_call["name"]]
                        tool_output = selected_tool.invoke(tool_call["args"])
                        messages.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
                        
                return "Error: Exceeded maximum tool call iterations."
            except Exception as e:
                logger.warning("GenAI API call failed (%s) — using SimulatedChatModel fallback", e)
                return self._fallback_model.generate_sync(prompt_text)
        return self._fallback_model.generate_sync(prompt_text)
