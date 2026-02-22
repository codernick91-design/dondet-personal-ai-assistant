#!/bin/bash

# Start Ollama in background
echo "Starting Ollama server..."
ollama serve &
OLLAMA_PID=$!

echo "Waiting for Ollama API..."
until curl -s http://localhost:11434/api/tags > /dev/null; do
    sleep 1
done

BASE_MODEL="llama3.2:1b"
echo "Pulling base model $BASE_MODEL..."
ollama pull $BASE_MODEL

# Build the custom model from Modelfile
CUSTOM_MODEL="dondet-custom"
echo "Creating custom model $CUSTOM_MODEL from Modelfile..."
ollama create $CUSTOM_MODEL -f Modelfile

echo "Ollama is ready with custom model $CUSTOM_MODEL"

# Keep script running
wait $OLLAMA_PID
