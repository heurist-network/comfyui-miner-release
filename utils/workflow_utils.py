# workflow_utils.py
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger

@dataclass
class TaskConfig:
    """Configuration for different task types and their workflows"""
    workflow: str
    endpoint: str

class WorkflowConfig:
    """Workflow configuration management"""
    
    BASE_PATH = "example"
    WORKFLOWS = {
        "upscaler": "workflows/upscaler.json",
        "txt2img": "workflows/txt2img.json",
        "flux-lora": "workflows/advanced_flux_lora.json",
        "txt2vid": "workflows/txt2vid-fp8.json"
    }
    ENDPOINTS = {
        "upscaler": "endpoints/upscaler.yaml",
        "txt2img": "endpoints/txt2img.yaml",
        "flux-lora": "endpoints/advanced_flux_lora.yaml",
        "txt2vid": "endpoints/txt2vid-fp8.yaml"
    }

    WORKFLOW_NAME_MAPPINGS = {
        "txt2vid-fp8": ["1"],      # This workflow setup can handle workflow_id "1"
        "txt2vid-fp16": ["2"],     # This workflow setup can handle workflow_id "2"
    }

    @classmethod
    def get_config(cls, task_type: str) -> Optional[TaskConfig]:
        """Retrieve configuration for a specific task type"""
        if not cls.is_valid_task_type(task_type):
            logger.error(f"Unknown task type: {task_type}")
            return None
        return TaskConfig(
            workflow=f"{cls.BASE_PATH}/{cls.WORKFLOWS[task_type]}",
            endpoint=f"{cls.BASE_PATH}/{cls.ENDPOINTS[task_type]}"
        )

    @classmethod
    def is_valid_task_type(cls, task_type: str) -> bool:
        """Check if the given task type is supported"""
        return task_type in cls.WORKFLOWS

    @classmethod
    def get_supported_workflow_ids(cls, workflow_name: str) -> list[str]:
        """Get the workflow IDs supported by this workflow setup"""
        return cls.WORKFLOW_NAME_MAPPINGS.get(workflow_name, [])
