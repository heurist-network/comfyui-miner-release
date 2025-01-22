#!/bin/bash

# Usage: ./start.sh <gpu_numbers> <action> [service]
# Examples:
# ./start.sh setup           # Run initial setup
# ./start.sh 4 up           # Start services on GPU 4
# ./start.sh "4,5" up       # Start services on GPU 4 and 5
# ./start.sh 4 down         # Stop and remove services on GPU 4
# ./start.sh 4 logs         # Show logs for both services on GPU 4
# ./start.sh 4 logs miner   # Show logs for just miner on GPU 4

# Check for pull command
if [ "$1" = "pull" ]; then
    echo "Pulling all required images..."
    docker-compose -f docker-compose.setup.yml pull
    docker-compose pull
    exit $?
fi

# Check for setup command
if [ "$1" = "setup" ]; then
    echo "Running initial setup..."
    docker-compose -f docker-compose.setup.yml run --rm setup
    exit $?
fi

# Check if at least two arguments are provided
if [ $# -lt 2 ]; then
    echo "Usage: $0 <gpu_numbers> <action> [service]"
    exit 1
fi

gpu_nums=${1}       # Can be single number or comma-separated list
action=${2}         # Required action
service=${3}        # Optional specific service

# Function to check if GPU config exists in .env
check_gpu_config() {
    local gpu_num=$1
    if ! grep -q "GPU${gpu_num}_DEVICE_ID" .env; then
        echo "Error: GPU${gpu_num}_DEVICE_ID not found in .env"
        return 1
    fi
    if ! grep -q "GPU${gpu_num}_PORT" .env; then
        echo "Error: GPU${gpu_num}_PORT not found in .env"
        return 1
    fi
    if ! grep -q "GPU${gpu_num}_ADDRESS" .env; then
        echo "Error: GPU${gpu_num}_ADDRESS not found in .env"
        return 1
    fi
    return 0
}

# Function to manage services for a single GPU
manage_gpu_services() {
    local gpu_num=$1
    local action=$2
    local service=$3

    # Check if GPU config exists first
    if ! check_gpu_config $gpu_num; then
        return 1
    fi

    # Load GPU-specific settings
    GPU_DEVICE_ID=$(grep "GPU${gpu_num}_DEVICE_ID" .env | cut -d '=' -f2)
    COMFYUI_PORT=$(grep "GPU${gpu_num}_PORT" .env | cut -d '=' -f2)
    ERC20_ADDRESS=$(grep "GPU${gpu_num}_ADDRESS" .env | cut -d '=' -f2)

    echo "Managing GPU $gpu_num services (Port: $COMFYUI_PORT)"

    # Set environment variables and use project namespace
    export GPU_DEVICE_ID=$GPU_DEVICE_ID
    export COMFYUI_PORT=$COMFYUI_PORT
    export ERC20_ADDRESS=$ERC20_ADDRESS

    case $action in
        up)
            COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose up -d comfyui miner
            ;;
        down)
            COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose down
            ;;
        logs)
            if [ "$service" = "comfyui" ] || [ "$service" = "miner" ]; then
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose logs -f $service
            else
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose logs -f
            fi
            ;;
        stop)
            if [ "$service" = "comfyui" ] || [ "$service" = "miner" ]; then
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose stop $service
            else
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose stop
            fi
            ;;
        restart)
            if [ "$service" = "comfyui" ] || [ "$service" = "miner" ]; then
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose restart $service
            else
                COMPOSE_PROJECT_NAME="gpu${gpu_num}" docker-compose restart
            fi
            ;;
        *)
            echo "Unknown action: $action"
            return 1
            ;;
    esac
}

# For all cases, process each GPU number
IFS=',' read -ra GPU_ARRAY <<< "$gpu_nums"
for gpu_num in "${GPU_ARRAY[@]}"; do
    manage_gpu_services $gpu_num "$action" "$service"
    if [ $? -ne 0 ]; then
        echo "Failed to manage services for GPU $gpu_num"
        exit 1
    fi
done