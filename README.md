## ComfyUI Service

Virtual ComfyUI service that can be imported and run inside a python process. This project consists of two parts: a Docker-based ComfyUI service and a Python miner script that interacts with a task server.

> **Note:** If you're unable to use Docker or prefer a non-Docker setup, please checkout the `feature/non-docker-runtime` branch:
> ```bash
> git checkout feature/non-docker-runtime
> ```
> and follow the instructions in that branch's README.

### Prerequisites
- `Docker` or `Docker Compose` installed ([Installation Guide](docs/README_Docker.md))
- `Nvidia Container Toolkit` installed ([Installation Guide](docs/README_Container_Toolkit.md))
- NVIDIA GPU with appropriate drivers

## Method 1: Docker Compose (Recommended)
1. Clone the repository:
```bash
git clone https://github.com/heurist-network/comfyui-miner-release.git
cd comfyui-miner-release
```
2. Create a .env file in the project root with your configuration:
```bash
# Common settings
WORKFLOW_NAMES=hunyuan-fp8

# GPU 0 settings
GPU0_DEVICE_ID=0
GPU0_PORT=8188
GPU0_ADDRESS=your-erc20-address

# GPU 1 settings (optional)
GPU1_DEVICE_ID=1
GPU1_PORT=8189
GPU1_ADDRESS=your-erc20-address
```
3. Pull all required images:
```bash
./start.sh pull (# Note: ComfyUI image is ~13GB, initial download may take some time)
```
4. Initial setup:
```bash
./start.sh setup
```
5. Start and manage services:
```bash
# Start services
./start.sh 0 up          # Start on GPU 0
./start.sh "0,1" up      # Start on multiple GPUs

# Monitor services
./start.sh 0 logs        # View all logs for GPU 0
./start.sh 1 logs miner  # View miner logs for GPU 1

# Manage services
./start.sh 1 restart     # Restart services on GPU 1
./start.sh "0,1" down    # Stop all services
```

### Configuration Options:
- Per-GPU settings using GPU{N}_DEVICE_ID, GPU{N}_PORT, and GPU{N}_ADDRESS
- WORKFLOW_NAMES: Comma-separated list of workflows (default: hunyuan-fp8)
- All GPU instances share the same models and custom nodes
- Each GPU instance runs independently with its own port

## Method 2: Manual Installation

1. Clone the repository:
```
git clone https://github.com/your-repo/comfyui-miner-release.git
cd comfyui-miner-release
```
2. Create a .env file in the project root with your configuration:
```
GPU_DEVICE_ID=0
COMFYUI_PORT=8189
ERC20_ADDRESS=your-erc20-address
WORKFLOW_NAMES=hunyuan-fp8,txt2vid-fp8
```
3. Set up Python environment:
```
conda create -n comfyui python=3.10
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements-miner.txt
```
4. Install ComfyUI and models:
```
python comfyui_service/install.py
```
Note: If you encounter permission issues, run:
```
sudo chown -R $(whoami) ./
```
5. Pull the Docker image:
```
docker pull heuristai/comfyui-service:latest
```
6. Run the ComfyUI container:
```
docker run -d \
  --gpus '"device=0"' \
  --network host \
  -v $(pwd)/ComfyUI:/app \
  -v /tmp:/tmp \
  --env-file .env \
  --name comfyui-container \
  heuristai/comfyui-service:latest
```
7. Running the Miner
```
python comfyui-miner.py
```
## Troubleshooting

If you encounter any issues, please check the following:
- Ensure the Docker container for ComfyUI is running correctly.
- Verify that the port specified in the miner script matches the one used by the ComfyUI service.
- Check that the GPU ID is valid and the GPU is available.