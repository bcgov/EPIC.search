# Use the Ollama base image
FROM ollama/ollama:0.6.1

# Build arguments
ARG MODEL_NAME
ARG MODEL_VERSION

# Install curl
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

# Start the Ollama service, pull the model, and stop the service
RUN ollama serve > /var/log/ollama.log 2>&1 & \
    OLLAMA_PID=$! && \
    sleep 10 && \
    ollama pull ${MODEL_NAME}:${MODEL_VERSION} && \
    kill $OLLAMA_PID

# Create the entrypoint script
RUN echo '#!/bin/bash\n\
echo "Starting Ollama service..."\n\
ollama serve > /var/log/ollama.log 2>&1 &\n\
OLLAMA_PID=$!\n\
\n\
echo "Waiting for Ollama service to initialize..."\n\
sleep 10\n\
\n\
echo "Checking Ollama service status..."\n\
if curl -s http://localhost:11434/api/version > /dev/null; then\n\
    echo "✓ Ollama service is running"\n\
    \n\
    echo "Testing model with warm-up query..."\n\
    echo "Hello" | ollama run $MODEL_NAME:$MODEL_VERSION --verbose=false\n\
    \n\
    echo "Ollama setup complete!"\n\
else\n\
    echo "✗ Ollama service failed to start."\n\
fi\n\
\n\
echo "Keeping Ollama running..."\n\
tail -f /var/log/ollama.log\n\
' > /usr/local/bin/docker-entrypoint.sh

# Make the entrypoint script executable
RUN chmod +x /usr/local/bin/docker-entrypoint.sh

# Environment variables for the model
ENV MODEL_NAME=${MODEL_NAME}
ENV MODEL_VERSION=${MODEL_VERSION}

# Expose the Ollama API port
EXPOSE 11434

# Set the entrypoint to the script
ENTRYPOINT ["/usr/local/bin/docker-entrypoint.sh"]
