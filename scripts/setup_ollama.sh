#!/bin/bash
echo "Waiting for Ollama to start..."
until curl -sf http://localhost:11434/api/tags > /dev/null 2>&1; do
    sleep 2
done
echo "Ollama is ready. Pulling models..."
docker compose exec -T ollama ollama pull gemma3:4b
echo "gemma3:4b ready (matching/query generation)"
docker compose exec -T ollama ollama pull gemma3:1b
echo "gemma3:1b ready (enrichment)"
echo "All Ollama models ready!"
