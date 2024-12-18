# NVIDIA Container Toolkit Installation Guide for Linux

## Prerequisites
- Docker installed and properly configured
- NVIDIA GPU drivers installed
- Ubuntu/Debian-based Linux distribution
- Sudo privileges

## Installation Steps
1. Verify Current Installation
```bash
dpkg -l | grep nvidia-container-toolkit
```
2. Set Up NVIDIA Container Toolkit Repository
```bash
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg

curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list
```
3. Update Package Listing
```bash
sudo apt-get update
```
4. Install NVIDIA Container Toolkit
```bash
sudo apt-get install -y nvidia-container-toolkit
```
5. Configure Docker Runtime
```bash
sudo nvidia-ctk runtime configure --runtime=docker
```
6. Restart Docker Service
```bash
sudo systemctl restart docker
```

## Verification
Run a base CUDA container to verify the setup:
```bash
docker run --rm --gpus all nvidia/cuda:11.0.3-base-ubuntu20.04 nvidia-smi
```
This should display your GPU information through nvidia-smi.


