#!/bin/bash

# --- Test Runner for Adobe Hackathon 1B ---
# This script finds all subdirectories in the 'input' folder
# and runs the Docker container for each one.

# Name of the Docker image we built
IMAGE_NAME="persona-intel-engine:1b"

# Path to the main input directory
INPUT_BASE_DIR="input"

echo "--- Building Docker Image ---"
docker build --platform linux/amd64 -t $IMAGE_NAME .

# Check if the build was successful
if [ $? -ne 0 ]; then
    echo "Docker build failed. Aborting."
    exit 1
fi

echo -e "\n--- Running Tests ---"

# Loop through each subdirectory in the input folder
for collection_dir in "$INPUT_BASE_DIR"/*/; do
    # Check if it's a directory
    if [ -d "$collection_dir" ]; then
        # Get the clean directory path
        test_case_path=$(realpath "$collection_dir")
        test_case_name=$(basename "$test_case_path")
        
        echo -e "\n[INFO] Processing Test Case: $test_case_name"
        echo "[INFO] Input/Output Path: $test_case_path"
        
        # Check if the required input file exists
        if [ ! -f "$test_case_path/challenge1b_input.json" ]; then
            echo "[WARN] Skipping '$test_case_name': challenge1b_input.json not found."
            continue
        fi

        # The magic is here: We mount the specific test case directory
        # to the container's /app/data directory.
        docker run --rm \
          -v "$test_case_path":/app/data \
          --network none \
          $IMAGE_NAME
          
        # Check if the output file was created
        if [ -f "$test_case_path/challenge1b_output.json" ]; then
            echo "[SUCCESS] Output file generated for Test Case: $test_case_name"
        else
            echo "[FAILURE] No output file generated for Test Case: $test_case_name"
        fi
    fi
done

echo -e "\n--- All tests completed. ---"