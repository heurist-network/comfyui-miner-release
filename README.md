## ComfyUI Service

Virtual ComfyUI service that can be imported and run inside a python process. This project consists of two parts: a Docker-based ComfyUI service and a Python miner script that interacts with a task server.

### Prerequisites
- `Docker` or `Docker Compose` installed
- `Nvidia Container Toolkit` installed (for GPU support)
- NVIDIA GPU with appropriate drivers

## Method 1: Docker Compose (Recommended)
1. Clone the repository:
```bash
git clone https://github.com/heurist-network/comfyui-miner-release.git
cd comfyui-miner-release
```
2. Start the service:
```bash
docker-compose pull
docker-compose up -d
```
3. Monitor Processes:
```bash
docker-compose logs -f comfyui
docker-compose logs -f miner
```
4. Configuration Options
You can configure the service using environment variables:

- `GPU_DEVICE_ID`: GPU device to use (default: 0)
- `COMFYUI_PORT`: Port for ComfyUI service (default: 8188)
- `ERC20_ADDRESS`: Your ERC20 address for mining

Example with parameters:
```bash
ERC20_ADDRESS=0x123... COMFYUI_PORT=8188 GPU_DEVICE_ID=0 docker-compose up -d
```

## Method 2: Manual Installation

### Starting the ComfyUI Service
1. Clone the repository:
```
git clone https://github.com/your-repo/comfyui-miner.git
cd comfyui-miner
```

2. Set up Python environment:
```
conda activate -n comfyui python=3.10
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r requirements.txt
```

3. Install ComfyUI and models:
```
python comfyui_service/install.py
```
Note: If you encounter permission issues, run:
```
sudo chown -R $(whoami) ./
```

4. Pull the Docker image:
```
docker pull heuristai/comfyui-service:latest
```

5. Run the ComfyUI container:
```
docker run -d \
  --gpus '"device=0"' \
  --network host \
  -v $(pwd)/ComfyUI:/app \
  -v /tmp:/tmp \
  -e COMFYUI_PORT=8188 \
  --name comfyui-container \
  heuristai/comfyui:latest
```
6. Running the Miner
```
python comfyui-miner-v0.0.1.py --port <comfyui-service-port>
```
Replace `<comfyui-service-port>` with the port you specified for the ComfyUI service.

### Configuration

The miner uses a configuration file (`config.toml`) for various settings. Ensure this file is properly set up before running the miner.

## Troubleshooting

If you encounter any issues, please check the following:
- Ensure the Docker container for ComfyUI is running correctly.
- Verify that the port specified in the miner script matches the one used by the ComfyUI service.
- Check that the GPU ID is valid and the GPU is available.