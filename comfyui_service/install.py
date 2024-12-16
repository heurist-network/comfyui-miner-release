import os
import sys
import json
import time
import toml
import httpx
import shutil
import subprocess
from tqdm import tqdm
from pathlib import Path
from git import Repo, GitCommandError

def get_example_path():
    """Get the absolute path to the example directory"""
    root_dir = Path(__file__).resolve().parents[1]  # Go up two levels from install.py
    return root_dir / "example"

def load_config():
    """Load configuration from root directory"""
    root_dir = Path(__file__).resolve().parents[1]
    config_path = root_dir / "config.toml"
    
    with open(config_path, 'r') as f:
        return toml.load(f)

def get_remote_file_size(url):
    try:
        response = httpx.head(url, follow_redirects=True)
        return int(response.headers.get('Content-Length', 0))
    except Exception as e:
        print(f"Error getting remote file size for {url}: {e}")
        return 0

def download_models(downloads, comfyui_home, size_threshold=1024):
    for file_path, url in downloads.items():
        local_filepath = Path(comfyui_home, file_path)
        local_filepath.parent.mkdir(parents=True, exist_ok=True)

        remote_size = get_remote_file_size(url)
        
        if os.path.exists(local_filepath):
            local_size = os.path.getsize(local_filepath)
            if abs(local_size - remote_size) <= size_threshold:
                print(f"Skipping {url} as {file_path} already exists")
                continue
            print(f"Size mismatch for {file_path}. Proceeding with download.")
        else:
            print(f"Downloading {file_path}")

        with httpx.stream("GET", url, follow_redirects=True) as stream:
            total = int(stream.headers.get("Content-Length", 0))
            with open(local_filepath, "wb") as f, tqdm(
                total=total, unit_scale=True, unit_divisor=1024, unit="B"
            ) as progress:
                num_bytes_downloaded = stream.num_bytes_downloaded
                for data in stream.iter_bytes():
                    f.write(data)
                    progress.update(
                        stream.num_bytes_downloaded - num_bytes_downloaded
                    )
                    num_bytes_downloaded = stream.num_bytes_downloaded

def clone_and_install(repo_url, hash, clone_to="repo_dir", retries=5):
    print(f"\n===== Installing {repo_url}")
    for t in range(retries):        
        try:
            if os.path.exists(clone_to):
                shutil.rmtree(clone_to)
            repo = Repo.clone_from(repo_url, clone_to)
            repo.submodule_update(recursive=True)    
            try:
                repo.git.checkout(hash)
            except Exception as e:
                print(f"Error checking out hash: {e}")
            break
        except GitCommandError as e:
            print(f"Error cloning repo: {e}, retrying...")
            if t == retries - 1:
                raise e
            time.sleep(5)

    for root, dirs, files in os.walk(clone_to):
        for file in files:
            if file.startswith("requirements") and file.endswith((".txt", ".pip")):
                try:
                    requirements_path = os.path.join(root, file)
                    subprocess.run(["pip", "install", "-r", requirements_path], check=True)
                except subprocess.CalledProcessError as e:
                    print(f"Error installing requirements: {e.stderr}")

def setup_comfyui(snapshot_path, comfyui_home):
    if not os.path.exists(snapshot_path):
        print(f"Error: Snapshot file {snapshot_path} does not exist")
        return

    # Load and validate snapshot
    with open(snapshot_path, 'r') as f:
        snapshot = json.load(f)
    
    # Setup ComfyUI
    comfyui_repo = "https://github.com/comfyanonymous/ComfyUI"
    if not os.path.exists(comfyui_home):
        print(f"Cloning ComfyUI repository to {comfyui_home}")
        os.makedirs(comfyui_home)
        repo = Repo.init(comfyui_home)
        origin = repo.create_remote("origin", comfyui_repo)
        origin.fetch()
        repo.git.checkout(snapshot["comfyui"])
    
        # Install requirements only after repository is cloned
        requirements_path = os.path.join(comfyui_home, "requirements.txt")
        if os.path.exists(requirements_path):
            print("Installing ComfyUI requirements...")
            try:
                subprocess.run(["pip", "install", "xformers!=0.0.18", "-r", requirements_path, 
                            "--extra-index-url", "https://download.pytorch.org/whl/cu121"], check=True)
            except subprocess.CalledProcessError as e:
                print(f"Error installing requirements: {e}")
                return
        else:
            print(f"Warning: Requirements file not found at {requirements_path}")

    # Install custom nodes
    print("Installing custom nodes...")
    for url, node in snapshot["git_custom_nodes"].items():
        hash = node["hash"]
        repo_name = url.split("/")[-1].replace(".git", "")
        repo_dir = f"{comfyui_home}/custom_nodes/{repo_name}"
        clone_and_install(url, hash, clone_to=repo_dir)

    # Download models
    if extra_downloads := snapshot.get("downloads"):
        print("Downloading models...")
        download_models(extra_downloads, comfyui_home)

    # Run post-install commands
    if post_install_commands := snapshot.get("post_install_commands"):
        print("Running post-install commands...")
        for command in post_install_commands:
            print(f"Running: {command}")
            os.system(command)

def main():
    try:
        # Load configuration
        config = load_config()
        installation_config = config.get('installation', {})
        
        # Get paths
        example_path = get_example_path()
        workflow_name = installation_config.get('workflow_name')
        comfyui_home = installation_config.get('comfyui_home')

        if not workflow_name:
            raise ValueError("workflow_name not found in config")
        if not comfyui_home:
            raise ValueError("comfyui_home not found in config")

        # Append .json if not present
        workflow_filename = f"{workflow_name}.json" if not workflow_name.endswith('.json') else workflow_name

        # Construct full paths
        snapshot_path = example_path / "snapshots" / workflow_filename
        workflow_path = example_path / "workflows" / workflow_filename

        if not snapshot_path.exists():
            raise FileNotFoundError(f"Snapshot file not found: {snapshot_path}")

        sys.path.append(comfyui_home)
        setup_comfyui(str(snapshot_path), comfyui_home)
        print(f"Installation completed for {workflow_path}")

    except Exception as e:
        print(f"Installation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()