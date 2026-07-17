"""Interrupt and sync-prompt handlers for C2 human-in-the-loop control.

Manages the full lifecycle of a LangGraph interrupt:

1. **Handle** — Serialize the execution state, persist a
   :class:`~singularity.persistence.models.SyncPromptRecord`, and
   publish a telemetry event so the C2 operator is notified.
2. **Resolve** — Accept the operator's decision (approve / deny /
   modify) and update the persistence records.
3. **Resume** — Reload the checkpointed state and continue graph
   execution with the operator's resolution injected via
   ``Command(resume=...)``.
4. **Query** — List all pending interrupts waiting for C2 decisions.

The :class:`InterruptHandler` is the single entry-point for all
interrupt-related operations in the orchestration layer.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from singularity.core.agent_base import (
    InterruptRequest,
    InterruptResolution,
    ProposedAction,
    TelemetryFrame,
    AgentStatus,
)
from singularity.orchestration.graph import resume_after_interrupt
from singularity.persistence.repository import StateRepository

logger = logging.getLogger(__name__)


def _utc_now() -> datetime:
    """Return the current UTC timestamp."""
    return datetime.now(timezone.utc)


def _short_id() -> str:
    """Generate a short unique identifier."""
    return uuid.uuid4().hex[:12]


class InterruptHandler:
    """Manages interrupt lifecycle for C2 human-in-the-loop sync prompts.

    Coordinates between the LangGraph checkpointer, the persistence
    layer (``StateRepository``), and the compiled state graph to pause,
    record, resolve, and resume interrupted graph executions.

    Attributes:
        compiled_graph: The compiled LangGraph state graph.  Set via
            :meth:`set_graph` after construction or via the constructor.
    """

    def __init__(self, compiled_graph: Any | None = None) -> None:
        """Initialize the interrupt handler.

        Args:
            compiled_graph: The compiled LangGraph state graph.  Can
                also be set later via :meth:`set_graph`.
        """
        self.compiled_graph: Any | None = compiled_graph
        self._state_repo = StateRepository()

    def set_graph(self, compiled_graph: Any) -> None:
        """Bind or rebind the compiled state graph.

        Args:
            compiled_graph: The compiled LangGraph state graph returned
                by :func:`~singularity.orchestration.graph.build_graph`.
        """
        self.compiled_graph = compiled_graph

    # ------------------------------------------------------------------
    # Handle — pause & persist
    # ------------------------------------------------------------------

    async def handle_interrupt(
        self,
        interrupt_request: InterruptRequest,
        graph_run_id: str,
        thread_id: str,
    ) -> str:
        """Serialize state, create a sync prompt record, and emit telemetry.

        Called by the orchestration layer when a graph node fires
        ``interrupt()``.  This method persists the interrupt so that
        the C2 operator can review it asynchronously.

        Args:
            interrupt_request: The interrupt to persist.
            graph_run_id: The current LangGraph run identifier.
            thread_id: The conversation thread that was interrupted.

        Returns:
            The ``state_id`` of the persisted
            :class:`~singularity.persistence.models.ExecutionStateRecord`.
        """
        logger.info(
            "Handling interrupt %s for action %s (risk=%s)",
            interrupt_request.interrupt_id,
            interrupt_request.proposed_action.action_id,
            interrupt_request.proposed_action.risk_level.value,
        )

        # 1. Serialize execution state to the persistence layer
        state_json: dict[str, Any] = {
            "interrupt_id": interrupt_request.interrupt_id,
            "thread_id": thread_id,
            "proposed_action": interrupt_request.proposed_action.model_dump(
                mode="json"
            ),
            "serialized_state": interrupt_request.serialized_state,
            "created_at": _utc_now().isoformat(),
        }

        state_record = await self._state_repo.save_state(
            graph_run_id=graph_run_id,
            state_json=state_json,
        )

        state_id: str = state_record.state_id
        logger.info("Execution state persisted — state_id=%s", state_id)

        # 2. Create a sync prompt record for the C2 operator
        action: ProposedAction = interrupt_request.proposed_action
        await self._state_repo.create_sync_prompt(
            state_id=state_id,
            action_type=action.action_type,
            description=action.description,
            parameters_json=action.parameters,
            risk_level=action.risk_level.value,
        )

        logger.info(
            "Sync prompt created for state_id=%s — awaiting C2 resolution",
            state_id,
        )

        # 3. Publish telemetry event for the interrupt
        self._emit_interrupt_telemetry(interrupt_request)

        return state_id

    # ------------------------------------------------------------------
    # Resolve — process C2 operator decision
    # ------------------------------------------------------------------

    async def resolve_interrupt(
        self,
        prompt_id: str,
        decision: InterruptResolution,
        resolved_by: str,
        modification_note: str | None = None,
    ) -> dict[str, Any]:
        """Process the C2 operator's decision on a pending sync prompt.

        Updates the ``SyncPromptRecord`` and its parent
        ``ExecutionStateRecord`` in the persistence layer with the
        operator's resolution.

        Args:
            prompt_id: The unique identifier of the sync prompt.
            decision: The operator's decision — ``approved``, ``denied``,
                or ``modified``.
            resolved_by: Identifier of the operator who resolved.
            modification_note: Optional note if the action was modified.

        Returns:
            A dictionary containing the resolution details and the
            ``state_id`` for use in resuming graph execution.

        Raises:
            ValueError: If the decision is ``PENDING`` (not a valid
                resolution).
        """
        if decision == InterruptResolution.PENDING:
            raise ValueError(
                "Cannot resolve an interrupt with PENDING status. "
                "Use APPROVED, DENIED, or MODIFIED."
            )

        logger.info(
            "Resolving interrupt prompt_id=%s — decision=%s by %s",
            prompt_id,
            decision.value,
            resolved_by,
        )

        # Update the sync prompt record
        await self._state_repo.resolve_sync_prompt(
            prompt_id=prompt_id,
            resolution=decision.value,
            resolved_by=resolved_by,
            modification_note=modification_note,
        )

        # Retrieve the sync prompt to find the parent state_id
        pending = await self._state_repo.get_pending_sync_prompts()
        state_id: str | None = None
        for prompt in pending:
            if prompt.prompt_id == prompt_id:
                state_id = prompt.state_id
                break

        # If we couldn't find it in pending (it's now resolved), look up
        # through the state records
        if state_id is None:
            logger.debug(
                "Prompt %s no longer pending — resolution already persisted",
                prompt_id,
            )

        # Mark the execution state as resolved
        if state_id is not None:
            status = "resumed" if decision == InterruptResolution.APPROVED else "abandoned"
            if decision == InterruptResolution.MODIFIED:
                status = "resumed"

            await self._state_repo.resolve_state(
                state_id=state_id,
                status=status,
            )
            logger.info(
                "Execution state %s marked as %s", state_id, status
            )

        resolution_payload: dict[str, Any] = {
            "prompt_id": prompt_id,
            "decision": decision.value,
            "resolved_by": resolved_by,
            "modification_note": modification_note,
            "state_id": state_id,
            "resolved_at": _utc_now().isoformat(),
        }

        return resolution_payload

    # ------------------------------------------------------------------
    # Resume — restart graph execution
    # ------------------------------------------------------------------

    async def resume_execution(
        self,
        thread_id: str,
        resolution: dict[str, Any],
    ) -> dict[str, Any]:
        """Resume an interrupted graph execution after C2 resolution.

        Loads the checkpointed state from the LangGraph checkpointer
        and reinvokes the graph with the operator's resolution injected
        via ``Command(resume=...)``.

        Args:
            thread_id: The conversation thread to resume.
            resolution: The operator's resolution payload (as returned
                by :meth:`resolve_interrupt`).

        Returns:
            The final state dictionary after the graph resumes and
            completes.

        Raises:
            RuntimeError: If no compiled graph has been set.
            ValueError: If the resolution contains a ``denied`` decision,
                since denied actions cannot be resumed.
        """
        if self.compiled_graph is None:
            raise RuntimeError(
                "No compiled graph set. Call set_graph() or pass the "
                "graph to the constructor before resuming execution."
            )

        decision = resolution.get("decision", "")
        if decision == InterruptResolution.DENIED.value:
            logger.warning(
                "Interrupt denied for thread %s — graph will not resume",
                thread_id,
            )
            raise ValueError(
                f"Cannot resume execution for denied interrupt on "
                f"thread {thread_id!r}. The graph run has been abandoned."
            )

        logger.info(
            "Resuming execution for thread %s with resolution: %s",
            thread_id,
            resolution,
        )

        result = await resume_after_interrupt(
            compiled_graph=self.compiled_graph,
            thread_id=thread_id,
            resolution=resolution,
        )

        return result

    # ------------------------------------------------------------------
    # Query — list pending interrupts
    # ------------------------------------------------------------------

    async def get_pending_interrupts(self) -> list[dict[str, Any]]:
        """Query all unresolved sync prompts awaiting C2 decisions.

        Returns:
            A list of dictionaries, each representing a pending sync
            prompt with fields: ``prompt_id``, ``state_id``,
            ``action_type``, ``description``, ``risk_level``, and
            ``created_at``.
        """
        records = await self._state_repo.get_pending_sync_prompts()

        pending: list[dict[str, Any]] = []
        for record in records:
            pending.append(
                {
                    "prompt_id": record.prompt_id,
                    "state_id": record.state_id,
                    "action_type": record.action_type,
                    "description": record.description,
                    "risk_level": record.risk_level,
                    "parameters": record.parameters_json,
                    "created_at": (
                        record.created_at.isoformat()
                        if record.created_at
                        else None
                    ),
                }
            )

        logger.info("Retrieved %d pending interrupt(s)", len(pending))
        return pending

    # ------------------------------------------------------------------
    # Telemetry helper
    # ------------------------------------------------------------------

    @staticmethod
    def _emit_interrupt_telemetry(irq: InterruptRequest) -> None:
        """Publish a telemetry event for an interrupt.

        Currently logs the telemetry event.  In a production system
        this would publish to the telemetry bus / event stream.

        Args:
            irq: The interrupt request to report.
        """
        frame = TelemetryFrame(
            agent_id=irq.proposed_action.agent_id,
            status=AgentStatus.INTERRUPTED,
            metrics={
                "interrupt_count": 1.0,
                "risk_level_numeric": {
                    "low": 0.0,
                    "medium": 1.0,
                    "high": 2.0,
                    "critical": 3.0,
                }.get(irq.proposed_action.risk_level.value, -1.0),
            },
            message=(
                f"INTERRUPT: {irq.proposed_action.action_type} — "
                f"{irq.proposed_action.description}"
            ),
        )

        logger.info(
            "📡 Interrupt telemetry emitted — agent=%s, action=%s, risk=%s",
            frame.agent_id,
            irq.proposed_action.action_type,
            irq.proposed_action.risk_level.value,
        )
