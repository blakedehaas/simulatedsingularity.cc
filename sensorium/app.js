/**
 * Simulated Singularity — C2 Ground Control Substrate
 * JavaScript Interaction Engine & Telemetry Stream Controller
 */

document.addEventListener("DOMContentLoaded", () => {
    // -----------------------------------------------------------------------
    // DOM Element References
    // -----------------------------------------------------------------------
    const countdownDisplay = document.getElementById("countdown-display");
    const heartbeatSeqDisplay = document.getElementById("heartbeat-seq-display");
    const systemStateBadge = document.getElementById("system-state-badge");
    const pulseBar = document.getElementById("pulse-bar");

    const globalTelemetryTerminal = document.getElementById("global-telemetry-terminal");
    const hitlGatekeeperModule = document.getElementById("hitl-gatekeeper-module");
    const hitlStatusTag = document.getElementById("hitl-status-tag");
    const hitlActionDesc = document.getElementById("hitl-action-desc");
    const hitlTargetAgent = document.getElementById("hitl-target-agent");
    const hitlActionType = document.getElementById("hitl-action-type");
    const hitlRiskLevel = document.getElementById("hitl-risk-level");
    const hitlTimestamp = document.getElementById("hitl-timestamp");

    const btnHitlApprove = document.getElementById("btn-hitl-approve");
    const btnHitlDeny = document.getElementById("btn-hitl-deny");
    const btnHitlOverride = document.getElementById("btn-hitl-override");

    const btnManualHeartbeat = document.getElementById("btn-manual-heartbeat");
    const btnTriggerHitl = document.getElementById("btn-trigger-hitl");

    const streamAnima = document.getElementById("stream-anima");
    const streamSensorium = document.getElementById("stream-sensorium");
    const streamPragma = document.getElementById("stream-pragma");

    const nodeAnima = document.getElementById("terminal-node-anima");
    const nodeSensorium = document.getElementById("terminal-node-sensorium");
    const nodePragma = document.getElementById("terminal-node-pragma");

    const metricCompactions = document.getElementById("metric-compactions");
    const metricIngestion = document.getElementById("metric-ingestion");
    const metricTokens = document.getElementById("metric-tokens");

    const commandInput = document.getElementById("command-input");
    const btnSendCommand = document.getElementById("btn-send-command");

    // -----------------------------------------------------------------------
    // Application State Variables
    // -----------------------------------------------------------------------
    let heartbeatSequence = 42;
    let countdownSeconds = 60;
    const CYCLE_DURATION = 60;
    let hitlPending = false;

    let compactionsCount = 14;
    let totalTokens = 142890;

    let schedulerInterval = null;

    // Auto-scroll track state for terminals
    const userScrollStates = {
        global: false,
        anima: false,
        sensorium: false,
        pragma: false,
    };

    // -----------------------------------------------------------------------
    // Helper: Timestamp formatting [HH:MM:SS:ms]
    // -----------------------------------------------------------------------
    function getTimestamp() {
        const now = new Date();
        const hh = String(now.getHours()).padStart(2, "0");
        const mm = String(now.getMinutes()).padStart(2, "0");
        const ss = String(now.getSeconds()).padStart(2, "0");
        const ms = String(now.getMilliseconds()).padStart(3, "0");
        return `[${hh}:${mm}:${ss}:${ms}]`;
    }

    // -----------------------------------------------------------------------
    // Auto-scrolling Logic with User-Scroll Intercept
    // -----------------------------------------------------------------------
    function appendLog(element, text, category = "normal", stateKey = "global") {
        const line = document.createElement("div");
        line.className = "log-line";

        const timeSpan = document.createElement("span");
        timeSpan.className = "log-timestamp";
        timeSpan.textContent = getTimestamp();

        const contentSpan = document.createElement("span");
        contentSpan.className = `log-content ${category}`;
        contentSpan.textContent = text;

        line.appendChild(timeSpan);
        line.appendChild(contentSpan);
        element.appendChild(line);

        // Limit DOM node count to max 150 items per terminal
        while (element.children.length > 150) {
            element.removeChild(element.firstChild);
        }

        // Auto-scroll if user has not scrolled up
        if (!userScrollStates[stateKey]) {
            element.scrollTop = element.scrollHeight;
        }
    }

    // Setup Scroll Event Listeners for Terminals
    function bindScrollCheck(terminalElem, stateKey) {
        terminalElem.addEventListener("scroll", () => {
            const distanceToBottom =
                terminalElem.scrollHeight - terminalElem.scrollTop - terminalElem.clientHeight;
            userScrollStates[stateKey] = distanceToBottom > 30;
        });
    }

    bindScrollCheck(globalTelemetryTerminal, "global");
    bindScrollCheck(streamAnima, "anima");
    bindScrollCheck(streamSensorium, "sensorium");
    bindScrollCheck(streamPragma, "pragma");

    // -----------------------------------------------------------------------
    // Timestamped Heartbeat Prompt Dispatcher
    // -----------------------------------------------------------------------
    async function dispatchTimestampedHeartbeatPrompt() {
        if (hitlPending) return;

        const nowUtcIso = new Date().toISOString();
        heartbeatSequence++;

        heartbeatSeqDisplay.textContent = `#${String(heartbeatSequence).padStart(4, "0")}`;
        countdownSeconds = CYCLE_DURATION;
        countdownDisplay.textContent = `${CYCLE_DURATION}s`;

        appendLog(
            globalTelemetryTerminal,
            `💓 HEARTBEAT PROMPT BROADCAST #${heartbeatSequence} @ ${nowUtcIso} -> Sent to all 3 agents (orchestrator-001, safeguard-001, synthesis-001)`,
            "nominal",
            "global"
        );

        // Try calling live backend /api/heartbeat endpoint
        try {
            const res = await fetch("/api/heartbeat", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ sequence_number: heartbeatSequence, timestamp: nowUtcIso })
            });

            if (res.ok) {
                const data = await res.json();
                const frames = data.frames || [];

                frames.forEach(frame => {
                    if (frame.agent_id === "orchestrator-001") {
                        appendLog(streamAnima, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node I (orchestrator-001) status: ${frame.status.toUpperCase()} | Message: ${frame.message}`, "highlight", "anima");
                    } else if (frame.agent_id === "safeguard-001") {
                        appendLog(streamSensorium, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node II (safeguard-001) status: ${frame.status.toUpperCase()} | Message: ${frame.message}`, "sys", "sensorium");
                    } else if (frame.agent_id === "synthesis-001") {
                        appendLog(streamPragma, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node III (synthesis-001) status: ${frame.status.toUpperCase()} | Message: ${frame.message}`, "nominal", "pragma");
                    }
                });
                return;
            }
        } catch (err) {
            // Fallback to local timestamped dispatch format if endpoint unavailable
        }

        // Direct Local Timestamped Heartbeat Delivery
        appendLog(streamAnima, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node I (orchestrator-001) memory compaction check & clock sync #${heartbeatSequence}`, "highlight", "anima");
        appendLog(streamSensorium, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node II (safeguard-001) sentinel scan & infrastructure status: NOMINAL`, "sys", "sensorium");
        appendLog(streamPragma, `[HEARTBEAT PROMPT @ ${nowUtcIso}] Node III (synthesis-001) execution frame sync. Total Tokens: ${totalTokens.toLocaleString()}`, "nominal", "pragma");

        totalTokens += 45;
        metricTokens.textContent = totalTokens.toLocaleString();
    }

    // -----------------------------------------------------------------------
    // I. Cyclic Scheduler & Kinetic Pulse
    // -----------------------------------------------------------------------
    function startScheduler() {
        if (schedulerInterval) clearInterval(schedulerInterval);

        schedulerInterval = setInterval(() => {
            if (hitlPending) return; // Freeze countdown on HITL interrupt

            countdownSeconds--;
            countdownDisplay.textContent = `${countdownSeconds}s`;

            // Progress bar width percentage
            const pct = ((CYCLE_DURATION - countdownSeconds) / CYCLE_DURATION) * 100;
            pulseBar.style.transition = "width 1s linear";
            pulseBar.style.width = `${pct}%`;

            // The Snap at state 0
            if (countdownSeconds <= 0) {
                triggerPulseSnap();
            }
        }, 1000);
    }

    function triggerPulseSnap() {
        // 1. Flash pure white (#ffffff) for 100ms
        pulseBar.classList.add("snap-flash");
        pulseBar.style.width = "100%";

        setTimeout(() => {
            // 2. Reset width to 0% instantly (zero transition delay)
            pulseBar.classList.remove("snap-flash");
            pulseBar.style.transition = "none";
            pulseBar.style.width = "0%";

            // Broadcast timestamped heartbeat prompt
            dispatchTimestampedHeartbeatPrompt();

            // Resume smooth transition for next tick
            setTimeout(() => {
                pulseBar.style.transition = "width 1s linear";
            }, 50);
        }, 100);
    }

    // -----------------------------------------------------------------------
    // III. Execution Freeze & HITL Gatekeeper Logic
    // -----------------------------------------------------------------------

    function triggerHitlInterrupt(actionType = "MUTATE_STATE_PRIVILEGED", risk = "CRITICAL (LEVEL 4)") {
        hitlPending = true;

        // 1. Update Header Badge
        systemStateBadge.textContent = "INTERRUPT";
        systemStateBadge.className = "badge badge-interrupt";

        // 2. Snap Gatekeeper to Active Pending State (opacity: 1, pulse shadow)
        hitlGatekeeperModule.classList.remove("dimmed");
        hitlGatekeeperModule.classList.add("active-pending");
        hitlStatusTag.textContent = "[STATUS: PENDING OPERATOR RESOLUTION]";
        hitlStatusTag.style.color = "var(--state-interrupt)";

        hitlActionType.textContent = actionType;
        hitlRiskLevel.textContent = risk;
        hitlTimestamp.textContent = new Date().toISOString();

        // 3. Execution Freeze: Dim triadic agent terminals
        nodeAnima.classList.add("execution-freeze");
        nodeSensorium.classList.add("execution-freeze");
        nodePragma.classList.add("execution-freeze");

        appendLog(
            globalTelemetryTerminal,
            `🚨 LANGGRAPH INTERRUPT TRIGGERED — Execution frozen pending HITL authorization!`,
            "interrupt",
            "global"
        );
        appendLog(
            streamPragma,
            `🛑 MATH EXECUTION FREEZE — Pragma blueprint generation suspended by Safeguard.`,
            "critical",
            "pragma"
        );
    }

    function resolveHitlInterrupt(resolutionType) {
        if (!hitlPending) return;
        hitlPending = false;

        // 1. Restore Badge
        systemStateBadge.textContent = "NOMINAL";
        systemStateBadge.className = "badge badge-nominal";

        // 2. Reset Gatekeeper to Dimmed Standby
        hitlGatekeeperModule.classList.remove("active-pending");
        hitlGatekeeperModule.classList.add("dimmed");
        hitlStatusTag.textContent = "[STATUS: INACTIVE / STANDBY]";
        hitlStatusTag.style.color = "var(--text-dim)";

        // 3. Remove Execution Freeze from Agent Terminals
        nodeAnima.classList.remove("execution-freeze");
        nodeSensorium.classList.remove("execution-freeze");
        nodePragma.classList.remove("execution-freeze");

        let logCategory = "nominal";
        if (resolutionType === "DENIED") logCategory = "critical";
        if (resolutionType === "OVERRIDDEN") logCategory = "interrupt";

        appendLog(
            globalTelemetryTerminal,
            `✅ HITL RESOLUTION: Operator decision [${resolutionType}] applied. Execution unfrozen.`,
            logCategory,
            "global"
        );
        appendLog(
            streamPragma,
            `▶️ EXECUTION UNFROZEN: Resuming Pragma cognitive blueprint stream.`,
            "nominal",
            "pragma"
        );
    }

    // -----------------------------------------------------------------------
    // IV. Event Listeners & Buttons
    // -----------------------------------------------------------------------

    btnHitlApprove.addEventListener("click", () => resolveHitlInterrupt("APPROVED"));
    btnHitlDeny.addEventListener("click", () => resolveHitlInterrupt("DENIED"));
    btnHitlOverride.addEventListener("click", () => resolveHitlInterrupt("OVERRIDDEN"));

    btnManualHeartbeat.addEventListener("click", () => {
        triggerPulseSnap();
    });

    btnTriggerHitl.addEventListener("click", () => {
        triggerHitlInterrupt("MANUAL_PODMAN_MUTATION", "CRITICAL (LEVEL 4)");
    });

    // Command Input Handling
    async function handleCommandSubmit() {
        const text = commandInput.value.trim();
        if (!text) return;

        const isoTimestamp = new Date().toISOString();
        appendLog(globalTelemetryTerminal, `>> DIRECTIVE @ ${isoTimestamp}: ${text}`, "highlight", "global");
        appendLog(streamSensorium, `[PROMPT ROUTING @ ${isoTimestamp}] Ingested directive: "${text}"`, "sys", "sensorium");

        commandInput.value = "";

        // Send to backend prompt API if available
        try {
            const res = await fetch("/api/prompt", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ message: text })
            });

            if (res.ok) {
                const data = await res.json();
                const verdict = data.security_verdict || "CLEAR";
                const route = data.route_decision || "local";
                const responseContent = data.response || data.synthesis_output || "Directive processed.";

                appendLog(streamSensorium, `[SAFEGUARD SCAN @ ${isoTimestamp}] Verdict: ${verdict}`, "sys", "sensorium");
                appendLog(streamAnima, `[ORCHESTRATOR ROUTE @ ${isoTimestamp}] Route: ${route} | Memory log committed`, "highlight", "anima");
                appendLog(streamPragma, `[PRAGMA SYNTHESIS @ ${isoTimestamp}] ${responseContent}`, "nominal", "pragma");
                appendLog(globalTelemetryTerminal, `[NOMINAL] Directive processed by Triadic State Engine. Verdict: ${verdict}`, "nominal", "global");

                if (data.proposed_actions && data.proposed_actions.length > 0) {
                    const action = data.proposed_actions[0];
                    triggerHitlInterrupt(action.action_type, `RISK: ${action.risk_level.toUpperCase()}`);
                }
                return;
            } else {
                const errData = await res.json();
                appendLog(globalTelemetryTerminal, `[ERROR @ ${isoTimestamp}] Prompt API failed: ${errData.error || errData.response}`, "critical", "global");
            }
        } catch (err) {
            appendLog(globalTelemetryTerminal, `[ERROR @ ${isoTimestamp}] Network error sending directive: ${err.message}`, "critical", "global");
        }
    }

    btnSendCommand.addEventListener("click", handleCommandSubmit);
    commandInput.addEventListener("keydown", (e) => {
        if (e.key === "Enter") handleCommandSubmit();
    });

    // -----------------------------------------------------------------------
    // Initial Boot Sequence
    // -----------------------------------------------------------------------
    const bootTime = new Date().toISOString();
    appendLog(globalTelemetryTerminal, `☩ C2 MISSION CONTROL SUBSTRATE ONLINE @ ${bootTime} ☩`, "nominal", "global");
    appendLog(globalTelemetryTerminal, "Connected to Triadic State Engine (orchestrator-001, safeguard-001, synthesis-001)", "sys", "global");
    appendLog(globalTelemetryTerminal, "Substrate Hypervisor active: Go Daemon listening on :50051", "nominal", "global");

    appendLog(streamAnima, `[Anima @ ${bootTime}] SQLite & ChromaDB Vector Store online.`, "highlight", "anima");
    appendLog(streamSensorium, `[Sensorium @ ${bootTime}] gemini-3.6-flash ready for multimodal ingestion.`, "sys", "sensorium");
    appendLog(streamPragma, `[Pragma @ ${bootTime}] gemini-1.5-pro ready for blueprint generation.`, "nominal", "pragma");

    startScheduler();
    // Dispatch initial timestamped heartbeat prompt
    dispatchTimestampedHeartbeatPrompt();
});
