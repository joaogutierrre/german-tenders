#!/bin/bash
echo "Waiting for Ollama to start..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama is ready. Pulling gemma3:4b model..."
docker compose exec -T ollama ollama pull gemma3:4b
echo "Ollama model ready!"
