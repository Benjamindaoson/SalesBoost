#!/bin/bash
# Deploy DeepSeek-OCR-2 with vLLM

set -e

echo "========================================="
echo "DeepSeek-OCR-2 vLLM Deployment Script"
echo "========================================="

# Configuration
MODEL_NAME="deepseek-ai/deepseek-ocr-2"
VLLM_PORT=8000
GPU_MEMORY_UTILIZATION=0.9
MAX_MODEL_LEN=4096

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "Error: Docker is not installed"
    exit 1
fi

# Check if NVIDIA Docker runtime is available
if ! docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi &> /dev/null; then
    echo "Warning: NVIDIA Docker runtime not available. CPU mode will be used (slow)."
    USE_GPU=false
else
    echo "NVIDIA GPU detected"
    USE_GPU=true
fi

# Pull vLLM Docker image
echo "Pulling vLLM Docker image..."
docker pull vllm/vllm-openai:latest

# Stop existing container if running
if docker ps -a | grep -q deepseek-ocr-vllm; then
    echo "Stopping existing container..."
    docker stop deepseek-ocr-vllm || true
    docker rm deepseek-ocr-vllm || true
fi

# Start vLLM server
echo "Starting vLLM server..."

if [ "$USE_GPU" = true ]; then
    # GPU mode
    docker run -d \
        --name deepseek-ocr-vllm \
        --gpus all \
        -p ${VLLM_PORT}:8000 \
        -v ~/.cache/huggingface:/root/.cache/huggingface \
        --ipc=host \
        vllm/vllm-openai:latest \
        --model ${MODEL_NAME} \
        --gpu-memory-utilization ${GPU_MEMORY_UTILIZATION} \
        --max-model-len ${MAX_MODEL_LEN} \
        --trust-remote-code
else
    # CPU mode (fallback)
    echo "Warning: Running in CPU mode. This will be very slow."
    docker run -d \
        --name deepseek-ocr-vllm \
        -p ${VLLM_PORT}:8000 \
        -v ~/.cache/huggingface:/root/.cache/huggingface \
        --ipc=host \
        vllm/vllm-openai:latest \
        --model ${MODEL_NAME} \
        --max-model-len ${MAX_MODEL_LEN} \
        --trust-remote-code
fi

echo ""
echo "vLLM server starting..."
echo "Container name: deepseek-ocr-vllm"
echo "Port: ${VLLM_PORT}"
echo ""
echo "Waiting for server to be ready (this may take a few minutes)..."

# Wait for server to be ready
MAX_WAIT=300  # 5 minutes
WAIT_TIME=0
while [ $WAIT_TIME -lt $MAX_WAIT ]; do
    if curl -s http://localhost:${VLLM_PORT}/health > /dev/null 2>&1; then
        echo ""
        echo "✓ vLLM server is ready!"
        echo ""
        echo "Server URL: http://localhost:${VLLM_PORT}"
        echo "Model: ${MODEL_NAME}"
        echo ""
        echo "Test with:"
        echo "  curl http://localhost:${VLLM_PORT}/v1/models"
        echo ""
        echo "View logs:"
        echo "  docker logs -f deepseek-ocr-vllm"
        echo ""
        exit 0
    fi

    sleep 5
    WAIT_TIME=$((WAIT_TIME + 5))
    echo -n "."
done

echo ""
echo "Error: Server did not start within ${MAX_WAIT} seconds"
echo "Check logs with: docker logs deepseek-ocr-vllm"
exit 1
