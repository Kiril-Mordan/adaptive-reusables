#!/bin/bash

CONFIG_FILE=".paa.config"

# Read config values with sensible defaults.
BASE_URL=""
PY_FILES_DIR="python_modules"
DOCKER_USERNAME=""

if [ -f "$CONFIG_FILE" ]; then
    if command -v yq &> /dev/null; then
        BASE_URL=$(yq -r '.gh_pages_base_url' "$CONFIG_FILE")
        PY_FILES_DIR=$(yq -r '.module_dir' "$CONFIG_FILE")
        DOCKER_USERNAME=$(yq -r '.docker_username' "$CONFIG_FILE")
    else
        BASE_URL=$(grep -E '^[[:space:]]*gh_pages_base_url:' "$CONFIG_FILE" | head -n1 | sed -E 's/^[^:]+:[[:space:]]*//')
        PY_FILES_DIR=$(grep -E '^[[:space:]]*module_dir:' "$CONFIG_FILE" | head -n1 | sed -E 's/^[^:]+:[[:space:]]*//')
        DOCKER_USERNAME=$(grep -E '^[[:space:]]*docker_username:' "$CONFIG_FILE" | head -n1 | sed -E 's/^[^:]+:[[:space:]]*//')
    fi
fi

[ -z "$PY_FILES_DIR" ] || [ "$PY_FILES_DIR" = "null" ] && PY_FILES_DIR="python_modules"
[ "$BASE_URL" = "null" ] && BASE_URL=""
[ "$DOCKER_USERNAME" = "null" ] && DOCKER_USERNAME=""


# Check if the directory exists
if [ ! -d "$PY_FILES_DIR" ]; then
    echo "Directory $PY_FILES_DIR does not exist."
    exit 0
fi

# Iterate over each .py file in the specified directory
for file in "$PY_FILES_DIR"/*.py;
do
    # Check if there are no .py files in the directory
    if [ ! -e "$file" ]; then
        echo "No .py files found in the directory."
        exit 0
    fi

    if ! grep -Eq '^[[:space:]]*__package_metadata__[[:space:]]*=' "$file"; then
        continue
    fi

    # Extract the base name of the file (without extension)
    base_name=$(basename "$file" .py)

    # Construct the URL
    url="${BASE_URL}/${base_name}"

    # Check if pypi module exists
    pypi_module_link="https://pypi.org/project/${base_name//_/-}/"
    pypi_badge=""
    if curl -s --head  --request GET "$pypi_module_link" | grep "200 " > /dev/null; then
        pypi_badge="[![PyPiVersion](https://img.shields.io/pypi/v/${base_name//_/-})](https://pypi.org/project/${base_name//_/-}/)"
    fi

    # Check if Docker Hub repository exists
    docker_hub_repo_link="https://hub.docker.com/v2/repositories/${DOCKER_USERNAME}/${base_name//_/-}"
    docker_hub_badge=""
    if [ -n "$DOCKER_USERNAME" ] && curl -s --head --request GET "$docker_hub_repo_link" | grep "200 " > /dev/null; then
        docker_hub_badge="[![Docker Hub](https://img.shields.io/docker/v/${DOCKER_USERNAME}/${base_name//_/-}?label=dockerhub&logo=docker)](https://hub.docker.com/r/${DOCKER_USERNAME}/${base_name//_/-})"
    fi

    if [ -z "$BASE_URL" ]; then
        continue
    fi

    # Replace underscores with dashes and capitalize each word
    display_name=$(echo "${base_name//_/-}" | awk '{for(i=1;i<=NF;i++) $i=toupper(substr($i,1,1)) tolower(substr($i,2))}1')

    mkdocs_badge="https://img.shields.io/static/v1?label=&message=${display_name}&color=darkgreen&logo=mkdocs"

    echo "- [![MkDocs]($mkdocs_badge)]($url) $pypi_badge $docker_hub_badge"
done
