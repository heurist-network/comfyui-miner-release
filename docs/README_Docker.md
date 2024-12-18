# Docker Installation Guide for Linux

## Prerequisites
- A Linux system (Ubuntu/Debian-based distribution)
- Sudo privileges
- Terminal access

## Basic Installation Steps
1. Update System Packages
```bash
sudo apt-get update
```
2. Install Required Dependencies
```bash
sudo apt-get install \
    apt-transport-https \
    ca-certificates \
    curl \
    gnupg \
    lsb-release
```
3. Add Docker's GPG Key
```bash
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
```
4. Set Up Docker Repository
```bash
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
```
5. Install Docker Engine
```bash
sudo apt-get update
sudo apt-get install docker-ce docker-ce-cli containerd.io
```
6. Verify Docker Installation
```bash
sudo docker run hello-world
```

## Installing Docker Compose
1. Download Docker Compose
```bash
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
```
2. Set Executable Permissions
```bash
sudo chmod +x /usr/local/bin/docker-compose
```
3. Verify Installation
```bash
docker-compose --version
```
