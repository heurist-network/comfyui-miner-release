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
GPU_DEVICE_ID=0
COMFYUI_PORT=8189    
ERC20_ADDRESS=your-erc20-address  
WORKFLOW_NAMES=hunyuan-fp8
```
3. Pull and setup:
```bash
docker-compose pull
docker-compose run --rm setup
```
3. Start services:
```bash
docker-compose up -d comfyui miner
```
4. Monitor Processes:
```bash
docker-compose logs -f comfyui
docker-compose logs -f miner
```
Configuration Options
You can configure the service using environment variables:

- `GPU_DEVICE_ID`: GPU device to use (default: 0)
- `COMFYUI_PORT`: Port for ComfyUI service (default: 8188)
- `ERC20_ADDRESS`: Your ERC20 address for mining
- `WORKFLOW_NAMES`: Comma-separated list of workflows to install and support (default: hunyuan-fp8)

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