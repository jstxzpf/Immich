#!/bin/bash

# List of Docker mirror addresses to test
MIRRORS=(
    "docker-0.unsee.tech"
    "docker.1panel.live"
    "registry.dockermirror.com"
    "docker.imgdb.de"
    "docker.m.daocloud.io"
    "hub.firefly.store"
    "hub.littlediary.cn"
    "hub.rat.dev"
    "dhub.kubesre.xyz"
    "cjie.eu.org"
    "docker.kejilion.pro"
    "docker.1panelproxy.com"
    "docker.hlmirror.com"
    "hub.fast360.xyz"
)

# Test image to pull
TEST_IMAGE="hello-world"
TEST_TAG="latest" # You can use a specific tag if you prefer

echo "Starting Docker mirror test..."
echo "---------------------------------"

for MIRROR in "${MIRRORS[@]}"; do
    echo "Testing mirror: ${MIRROR}"
    # Set up Docker daemon with the current mirror
    # Note: This temporarily changes the Docker daemon configuration.
    # On most Linux systems, you'd edit /etc/docker/daemon.json
    # For testing, we'll try to run a command with the mirror.
    # A more robust test would be to temporarily modify daemon.json and restart Docker,
    # but that's beyond a simple script for quick testing.

    # Instead of modifying daemon.json, we'll try to directly pull using the mirror in the image name.
    # This might not work for all mirrors, as some require daemon-level configuration.
    # However, it's the most common way to test public mirrors without deep system changes.

    # Attempt to pull the image using the mirror
    # We use `docker.io` explicitly for standard images when behind a mirror
    # If the mirror expects a direct image path, adjust accordingly.
    if [[ "$MIRROR" == *"daocloud"* || "$MIRROR" == *"1panel"* ]]; then
        # DaoCloud and 1Panel often work by prefixing the original registry
        # e.g., docker.m.daocloud.io/docker.io/hello-world
        PULL_COMMAND="docker pull ${MIRROR}/docker.io/${TEST_IMAGE}:${TEST_TAG}"
    elif [[ "$MIRROR" == *"ghcr.io"* ]]; then
        # Some mirrors might proxy specific registries like ghcr.io
        PULL_COMMAND="docker pull ${MIRROR}/ghcr.io/${TEST_IMAGE}:${TEST_TAG}"
    else
        # For general mirrors, try pulling directly with the mirror as the registry
        PULL_COMMAND="docker pull ${MIRROR}/${TEST_IMAGE}:${TEST_TAG}"
    fi


    if ${PULL_COMMAND} > /dev/null 2>&1; then
        echo -e "  \e[32mSUCCESS: ${MIRROR} is likely working.\e[0m"
        # Clean up the pulled image to save space
        docker rmi "${MIRROR}/${TEST_IMAGE}:${TEST_TAG}" > /dev/null 2>&1
    else
        # Fallback to standard Docker Hub if direct pull failed,
        # trying a different pattern for mirrors that expect daemon.json config.
        # This part is tricky because direct `docker pull` doesn't inherently use daemon.json mirrors.
        # The most reliable way to test `daemon.json` configured mirrors is to actually configure and restart docker daemon.
        # For this script, we'll just report the direct pull failure.

        echo -e "  \e[31mFAILED: ${MIRROR} did not work for direct pull.\e[0m"
        echo "    (Note: Some mirrors require configuration in /etc/docker/daemon.json and a Docker daemon restart.)"
    fi
    echo "---------------------------------"
done

echo "Test complete."
