#!/bin/bash

# Ensure yq is installed
if ! command -v yq &> /dev/null; then
    echo "yq is required to parse the YAML file. Install it first (e.g., 'sudo apt install yq' or 'brew install yq')."
    exit 1
fi

CONFIG_FILE=".paa.config"

# Function to remove leading './' and add a trailing slash if missing
sanitize_dir_path() {
    dir_path="$1"
    # Fallback for missing/null values
    if [ -z "$dir_path" ] || [ "$dir_path" = "null" ]; then
        dir_path="$2"
    fi
    # Remove leading './' if present
    dir_path="${dir_path#./}"
    # Ensure trailing slash
    [[ "${dir_path: -1}" != "/" ]] && dir_path="${dir_path}/"
    echo "$dir_path"
}

# Read directories from the config file and sanitize them
MODULE_DIR=$(sanitize_dir_path "$(yq -r '.module_dir' "$CONFIG_FILE")" "python_modules")
EXAMPLE_DIR=$(sanitize_dir_path "$(yq -r '.example_notebooks_path' "$CONFIG_FILE")" "example_notebooks")
CLI_DIR=$(sanitize_dir_path "$(yq -r '.cli_dir' "$CONFIG_FILE")" "cli")
MCP_DIR=$(sanitize_dir_path "$(yq -r '.mcp_dir' "$CONFIG_FILE")" "mcp")
API_ROUTES_DIR=$(sanitize_dir_path "$(yq -r '.api_routes_dir' "$CONFIG_FILE")" "api_routes")
STREAMLIT_DIR=$(sanitize_dir_path "$(yq -r '.streamlit_dir' "$CONFIG_FILE")" "streamlit")
DRAWIO_DIR=$(sanitize_dir_path "$(yq -r '.drawio_dir' "$CONFIG_FILE")" "drawio")
TESTS_DIR=$(sanitize_dir_path "$(yq -r '.tests_dir' "$CONFIG_FILE")" "tests")
ARTIFACTS_DIR=$(sanitize_dir_path "$(yq -r '.artifacts_dir' "$CONFIG_FILE")" "artifacts")
EXTRA_DOCS_DIR=$(sanitize_dir_path "$(yq -r '.extra_docs_dir' "$CONFIG_FILE")" "extra_docs")
LICENSES_DIR=$(sanitize_dir_path "$(yq -r '.licenses_dir' "$CONFIG_FILE")" "licenses")
SKILLS_DIR=$(sanitize_dir_path "skills" "skills")

# Output the directory paths with trailing slashes and no leading './'
echo "$MODULE_DIR $EXAMPLE_DIR $CLI_DIR $MCP_DIR $API_ROUTES_DIR $STREAMLIT_DIR $DRAWIO_DIR $TESTS_DIR $ARTIFACTS_DIR $EXTRA_DOCS_DIR $LICENSES_DIR $SKILLS_DIR"
