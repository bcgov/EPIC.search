#!/bin/bash

# Get the timeout from environment variable or default to 300 seconds
TIMEOUT=${GUNICORN_TIMEOUT:-300}

# Start Ollama service if available
if command -v ollama &> /dev/null; then
    echo "Starting Ollama service..."
    # Start Ollama and ensure it's properly bound to 0.0.0.0 so it's accessible
    # Also redirect output to logs for debugging
    ollama serve > /var/log/ollama.log 2>&1 &
    OLLAMA_PID=$!
    
    echo "Waiting for Ollama service to initialize..."
    # Wait longer to ensure Ollama is fully started
    sleep 10
    
    # Verify Ollama is running and responsive
    echo "Checking Ollama service status..."
    if curl -s http://0.0.0.0:11434/api/version > /dev/null; then
        echo "✓ Ollama service is running"
        
        echo "Ensuring model is pulled and cached..."
        ollama pull llama3.1:8b
        
        # Run a quick test to warm up the model
        echo "Testing model with warm-up query..."
        echo "Hello" | ollama run llama3.1:8b --verbose=false
        
        echo "Ollama setup complete!"
    else
        echo "✗ Ollama service failed to start. Check /var/log/ollama.log for details."
    fi
else
    echo "Ollama command not found. Skipping Ollama setup."
fi

echo 'Starting application'
# Start Gunicorn with increased timeout
exec gunicorn --bind 0.0.0.0:8080 --workers 4 --timeout $TIMEOUT wsgi:application