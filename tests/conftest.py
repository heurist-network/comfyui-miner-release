# tests/conftest.py
import pytest
from unittest.mock import Mock
import json
import os
from dotenv import load_dotenv
from utils.config_utils import load_config

@pytest.fixture
def mock_comfyui():
    """Provide a mock ComfyUI instance"""
    mock = Mock()
    mock.is_server_running.return_value = True
    mock.run_workflow.return_value = "/tmp/test_output.mp4"
    return mock

@pytest.fixture
def workflow_names():
    """Get workflow names from .env or config.toml"""
    load_dotenv()
    
    # Try to get workflows from .env first
    env_workflows = [
        w.strip() 
        for w in os.environ.get('WORKFLOW_NAMES', '').split(',') 
        if w.strip()
    ]
    
    if env_workflows:
        return env_workflows
    
    # Fallback to config.toml
    config = load_config()
    return config['installation']['workflow_names']

@pytest.fixture
def test_config(workflow_names):
    """Provide test configuration"""
    comfyui_port = os.environ.get('COMFYUI_PORT') or '8188'  # default to 8188
    return {
        'service': {
            'base_url': 'https://sequencer-v2.heurist.xyz',
            'port': comfyui_port
        },
        'miner': {
            'address': '0x0000000000000000000000000000000000000000'
        },
        'storage': {
            's3_bucket': 'test-bucket'
        },
        'installation': {
            'comfyui_home': './ComfyUI',
            'workflow_names': workflow_names
        }
    }

@pytest.fixture
def sample_task_data():
    """Provide sample task data"""
    return {
        "task_id": "test-123",
        "task_type": "txt2vid",
        "workflow_id": "1",
        "task_details": json.dumps({
            "prompt": "test video generation"
        }),
        "access_key_id": "test-key",
        "secret_access_key": "test-secret",
        "session_token": "test-token"
    }