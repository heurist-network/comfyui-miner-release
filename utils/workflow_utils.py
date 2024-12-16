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
    WORKFLOW_MAPPING = {
        "upscaler": TaskConfig(
            workflow="example/workflows/upscaler.json",
            endpoint="example/endpoints/upscaler.yaml"
        ),
        "txt2img": TaskConfig(
            workflow="example/workflows/txt2img.json",
            endpoint="example/endpoints/txt2img.yaml"
        ),
        "flux-lora": TaskConfig(
            workflow="example/workflows/advanced_flux_lora.json",
            endpoint="example/endpoints/advanced_flux_lora.yaml"
        ),
        "txt2vid": TaskConfig(
            workflow="example/workflows/txt2vid-fp8.json",
            endpoint="example/endpoints/txt2vid-fp8.yaml"
        )
    }

    @classmethod
    def get_config(cls, task_type: str) -> Optional[TaskConfig]:
        if task_type not in cls.WORKFLOW_MAPPING:
            logger.error(f"Unknown task type: {task_type}")
            return None
        return cls.WORKFLOW_MAPPING.get(task_type)

    @classmethod
    def is_valid_task_type(cls, task_type: str) -> bool:
        """Check if the given task type is supported"""
        return task_type in cls.WORKFLOW_MAPPING