"""Simulated chat model for deterministic development and testing.

Provides a keyword-driven response generator that mimics LLM behavior
without requiring external API calls. Each agent type receives contextually
appropriate responses based on keyword detection in the input prompt.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

from singularity.core.agent_base import AgentResponse, AgentStatus, TelemetryFrame


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
        agent_role: The role key used to select response templates.
        response_delay: Simulated latency in seconds (default ``0.05``).
    """

    def __init__(
        self,
        agent_role: str,
        response_delay: float = 0.05,
    ) -> None:
        self.agent_role = agent_role.lower()
        self.response_delay = response_delay
        self._templates = _RESPONSE_TEMPLATES.get(
            self.agent_role, _RESPONSE_TEMPLATES["core"]
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
            f"<SimulatedChatModel role={self.agent_role!r} "
            f"delay={self.response_delay}s>"
        )

import datetime

class GemmaChatModel:
    """Google GenAI LLM interface for Gemma models."""

    def __init__(
        self,
        agent_role: str = "core",
        model_name: str = "gemma-2b",
    ) -> None:
        self.agent_role = agent_role
        self.model_name = model_name
        self._llm = None
        try:
            from langchain_google_genai import ChatGoogleGenerativeAI
            self._llm = ChatGoogleGenerativeAI(model=self.model_name)
        except ImportError:
            pass

    async def generate(self, prompt_text: str) -> str:
        if self._llm:
            response = await self._llm.ainvoke(prompt_text)
            return response.content
        return f"[{datetime.datetime.now().isoformat()}] mock"

    def generate_sync(self, prompt_text: str) -> str:
        if self._llm:
            response = self._llm.invoke(prompt_text)
            return response.content
        return f"[{datetime.datetime.now().isoformat()}] mock"
