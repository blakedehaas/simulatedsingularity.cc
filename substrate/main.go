package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"os"
	"os/exec"
	"strings"
	"time"
)

// DaemonServer manages system telemetry and Podman devcontainer execution.
type DaemonServer struct {
	port           int
	defaultImage   string
	activeBuilds   int
}

// NewDaemonServer constructs a new hypervisor daemon instance.
func NewDaemonServer(port int, defaultImage string) *DaemonServer {
	if defaultImage == "" {
		defaultImage = "genesis-build-env:latest"
	}
	return &DaemonServer{
		port:         port,
		defaultImage: defaultImage,
	}
}

// SpawnBuildAgent executes an isolated Podman container to run a build blueprint.
func (s *DaemonServer) SpawnBuildAgent(ctx context.Context, buildID, blueprint, image string) (int, string, string, error) {
	if image == "" {
		image = s.defaultImage
	}

	log.Printf("[Pragma-Go] Spawning build agent [%s] in container %s", buildID, image)
	s.activeBuilds++
	defer func() { s.activeBuilds-- }()

	// Rootless Podman execution mapping the blueprint into a transient container
	cmd := exec.CommandContext(ctx, "podman", "run", "--rm",
		"--name", fmt.Sprintf("build_agent_%s", buildID),
		"--userns=keep-id",
		image,
		"/bin/sh", "-c", fmt.Sprintf("python build_executor.py '%s'", strings.ReplaceAll(blueprint, "'", "\\'")))

	outputBytes, err := cmd.CombinedOutput()
	outputLog := string(outputBytes)
	exitCode := 0

	if err != nil {
		if exitErr, ok := err.(*exec.ExitError); ok {
			exitCode = exitErr.ExitCode()
		} else {
			exitCode = 1
		}
		log.Printf("[Pragma-Go] Build Agent execution error [%s]: %v\nOutput: %s", buildID, err, outputLog)
		return exitCode, outputLog, "", fmt.Errorf("build execution failed: %w", err)
	}

	log.Printf("[Pragma-Go] Build Agent [%s] execution successful", buildID)
	return exitCode, outputLog, "", nil
}

// GetTelemetry returns hypervisor system load metrics.
func (s *DaemonServer) GetTelemetry() (float64, float64, int, string) {
	podmanVer := "unknown"
	cmd := exec.Command("podman", "--version")
	if out, err := cmd.Output(); err == nil {
		podmanVer = strings.TrimSpace(string(out))
	}
	return 12.5, 256.0, s.activeBuilds, podmanVer
}

func main() {
	port := 50051
	if pStr := os.Getenv("SUBSTRATE_PORT"); pStr != "" {
		fmt.Sscanf(pStr, "%d", &port)
	}

	server := NewDaemonServer(port, "genesis-build-env:latest")
	log.Printf("☩ Simulated Singularity Go Daemon Active on port %d ☩", port)
	_, cpu, active, podmanVer := server.GetTelemetry()
	log.Printf("[Substrate Telemetry] CPU Sim: %.1f%% | Active Containers: %d | Engine: %s", cpu, active, podmanVer)

	// Simple HTTP health / execution listener for lightweight inter-op
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", port))
	if err != nil {
		log.Fatalf("Failed to bind port %d: %v", port, err)
	}
	defer listener.Close()

	log.Printf("Go Hypervisor listening on %s. Awaiting cognitive cortex directives...", listener.Addr().String())
	
	// Keep daemon running in lightweight idle mode
	for {
		time.Sleep(10 * time.Second)
	}
}
