"""Ground Control UI component builders.

Factory functions that construct Chainlit :class:`Message` and
:class:`Action` objects for the various dashboard displays: sync prompt
approval cards, constellation overview tables, heartbeat indicators,
and the welcome screen.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from chainlit import Action, Message

from singularity.core.agent_base import (
    AgentStatus,
    AsyncBaseAgent,
    InterruptRequest,
    RiskLevel,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Sync prompt approval card
# ---------------------------------------------------------------------------

def build_sync_prompt_card(interrupt: InterruptRequest) -> Message:
    """Build a Chainlit Message with Approve/Deny buttons for a sync prompt.

    Renders the proposed action details (type, description, risk level,
    parameters) and attaches two :class:`Action` buttons that the operator
    can click to approve or deny the action.

    Args:
        interrupt: The interrupt request containing the proposed action
            under review.

    Returns:
        A :class:`Message` with embedded approval/denial actions.
    """
    action = interrupt.proposed_action

    risk_badge: dict[RiskLevel, str] = {
        RiskLevel.LOW: "🟢 LOW",
        RiskLevel.MEDIUM: "🟡 MEDIUM",
        RiskLevel.HIGH: "🟠 HIGH",
        RiskLevel.CRITICAL: "🔴 CRITICAL",
    }

    risk_display = risk_badge.get(action.risk_level, "⚪ UNKNOWN")

    lines: list[str] = [
        "## 🚨 Sync Prompt — Action Requires Approval",
        "",
        f"**Agent**: `{action.agent_id}`",
        f"**Action Type**: `{action.action_type}`",
        f"**Risk Level**: {risk_display}",
        f"**Action ID**: `{action.action_id}`",
        "",
        "### Description",
        action.description,
    ]

    if action.parameters:
        lines.append("")
        lines.append("### Parameters")
        for key, value in action.parameters.items():
            lines.append(f"  • **{key}**: `{value}`")

    lines.extend([
        "",
        "---",
        "*Select an action below to approve or deny this operation.*",
    ])

    content = "\n".join(lines)

    actions = [
        Action(
            name="approve_action",
            label="✅ Approve",
            value=action.action_id,
            description=f"Approve action {action.action_id}",
            payload={"value": action.action_id},
        ),
        Action(
            name="deny_action",
            label="🚫 Deny",
            value=action.action_id,
            description=f"Deny action {action.action_id}",
            payload={"value": action.action_id},
        ),
    ]

    return Message(
        content=content,
        author="Sync Prompt",
        actions=actions,
    )


# ---------------------------------------------------------------------------
# Constellation overview
# ---------------------------------------------------------------------------

def build_constellation_overview(agents: list[AsyncBaseAgent]) -> str:
    """Build a Markdown table summarizing the status of all agents.

    Renders each agent's ID, name, role, priority, and current status
    with a colored emoji indicator.

    Args:
        agents: The list of agents to include in the overview.

    Returns:
        A Markdown-formatted string containing the status table.
    """
    status_emoji: dict[AgentStatus, str] = {
        AgentStatus.INITIALIZING: "🔄",
        AgentStatus.NOMINAL: "🟢",
        AgentStatus.BUSY: "🟡",
        AgentStatus.INTERRUPTED: "🟠",
        AgentStatus.ERROR: "🔴",
        AgentStatus.OFFLINE: "⚫",
    }

    lines: list[str] = [
        "## 🛰️ Constellation Overview",
        "",
        "| Status | Agent | Role | Priority |",
        "|--------|-------|------|----------|",
    ]

    for agent in agents:
        emoji = status_emoji.get(agent.status, "⚪")
        lines.append(
            f"| {emoji} `{agent.status.value}` "
            f"| **{agent.agent_name}** (`{agent.agent_id}`) "
            f"| {agent.agent_role} "
            f"| {agent.priority} |"
        )

    lines.extend([
        "",
        f"**Total agents**: {len(agents)} | "
        f"**Nominal**: {sum(1 for a in agents if a.status == AgentStatus.NOMINAL)} | "
        f"**Degraded**: "
        f"{sum(1 for a in agents if a.status in (AgentStatus.ERROR, AgentStatus.INTERRUPTED))}",
    ])

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Triadic Constellation overview
# ---------------------------------------------------------------------------

def build_triadic_overview(agents: list[AsyncBaseAgent]) -> str:
    """Build a compact status panel for the triadic architecture.

    Shows Orchestrator, Safeguard, and Synthesis with their statuses.
    Includes node role descriptions: Brain & Clock, Gatekeeper, Doer.

    Args:
        agents: The list of active agents in the system.

    Returns:
        A Markdown-formatted string containing the triadic table.
    """
    status_emoji: dict[AgentStatus, str] = {
        AgentStatus.INITIALIZING: "🔄",
        AgentStatus.NOMINAL: "🟢",
        AgentStatus.BUSY: "🟡",
        AgentStatus.INTERRUPTED: "🟠",
        AgentStatus.ERROR: "🔴",
        AgentStatus.OFFLINE: "⚫",
    }
    
    triadic_roles = {
        "orchestrator-001": "Brain & Clock",
        "safeguard-001": "Gatekeeper",
        "synthesis-001": "Doer",
    }

    lines: list[str] = [
        "## 📐 Triadic Architecture Status",
        "",
        "| Agent | Status | Node Role |",
        "|-------|--------|-----------|",
    ]

    # Filter strictly to the 3 triadic nodes
    triadic_agents = [a for a in agents if a.agent_id in triadic_roles]

    for agent in triadic_agents:
        emoji = status_emoji.get(agent.status, "⚪")
        role_desc = triadic_roles.get(agent.agent_id, "Unknown")
        lines.append(
            f"| **{agent.agent_name}** (`{agent.agent_id}`) "
            f"| {emoji} `{agent.status.value}` "
            f"| {role_desc} |"
        )

    return "\n".join(lines)


# ---------------------------------------------------------------------------

# Heartbeat indicator
# ---------------------------------------------------------------------------

def build_heartbeat_indicator(next_heartbeat_in: float) -> str:
    """Build a compact heartbeat countdown display.

    Args:
        next_heartbeat_in: Seconds until the next scheduled heartbeat.

    Returns:
        A Markdown-formatted countdown string.
    """
    if next_heartbeat_in <= 0:
        return "💓 **Heartbeat**: `NOW` — pulsing..."

    if next_heartbeat_in < 10:
        urgency = "🟡"
    else:
        urgency = "🟢"

    return (
        f"💓 **Next heartbeat** in {urgency} "
        f"`{next_heartbeat_in:.0f}s`"
    )


# ---------------------------------------------------------------------------
# Welcome message
# ---------------------------------------------------------------------------

def build_welcome_message() -> str:
    """Build the welcome banner displayed when Ground Control starts.

    Returns:
        A Markdown-formatted welcome message with system description
        and quick-start instructions.
    """
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return "\n".join([
        "# 🛸 Simulated Singularity — Ground Control",
        "",
        f"**Session started**: `{now}`",
        "",
        "Welcome to the Constellation-Class Multi-Agent C2 Dashboard.",
        "You are connected to the Ground Control station, the human-in-the-loop",
        "interface for monitoring and commanding the orbital agent constellation.",
        "",
        "### Quick Start",
        "- **Send a message** to route prompts through the constellation",
        "- **Approve/Deny** sync prompts when agents request state-mutating operations",
        "- **Trigger heartbeats** manually to check agent health",
        "- **Monitor telemetry** events streamed in real-time",
        "",
        "### Subsystems Online",
        "- ✅ Persistence Layer (SQLite + WAL)",
        "- ✅ Telemetry Event Bus (async pub/sub)",
        "- ✅ Telemetry Collector (metric aggregation)",
        "- ✅ Ground Control UI (Chainlit WebSocket)",
        "",
        "---",
    ])
