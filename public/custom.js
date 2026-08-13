// Inject Navbar into Chainlit
document.addEventListener("DOMContentLoaded", () => {
    // Chainlit runs a React app that mounts later, but appending to body is safe.
    // Wait for a brief moment to ensure body is ready.
    setTimeout(() => {
        const navbar = document.createElement('div');
        navbar.className = "sensorium-navbar";
        navbar.innerHTML = `
            <a href="http://localhost:8000" class="nav-tab active">[HOME]</a>
            <a href="http://localhost:8001/?tab=view-overview" class="nav-tab">System Overview</a>
            <a href="http://localhost:8001/?tab=view-core" class="nav-tab">Core Agent</a>
            <a href="http://localhost:8001/?tab=view-coding" class="nav-tab">Coding Agent</a>
            <a href="http://localhost:8001/?tab=view-analytical" class="nav-tab">Analytical Agent</a>
            <a href="http://localhost:8001/?tab=view-creative" class="nav-tab">Creative Agent</a>
            <a href="http://localhost:8001/?tab=view-environment" class="nav-tab">Environment Agent</a>
            <a href="http://localhost:8001/?tab=view-memory" class="nav-tab">Memory Agent</a>
            <a href="http://localhost:8001/?tab=view-security" class="nav-tab">Security Agent</a>
        `;
        document.body.prepend(navbar);
    }, 100);
});
