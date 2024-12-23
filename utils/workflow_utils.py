import yaml
from typing import Dict, Optional
from dataclasses import dataclass
from loguru import logger
import os

@dataclass
class TaskConfig:
    """Configuration for different task types and their workflows"""
    workflow: str
    endpoint: str

class WorkflowConfig:
    """Workflow configuration management"""
    
    BASE_PATH = "example"
    _config = None

    @classmethod
    def load_config(cls):
        """Load workflow configurations from YAML file"""
        if cls._config is None:
            config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'workflows.yml')
            try:
                with open(config_path, 'r') as f:
                    cls._config = yaml.safe_load(f)
                logger.info(f"Loaded workflow configurations from {config_path}")
            except Exception as e:
                logger.error(f"Failed to load workflow configurations: {e}")
                cls._config = {"workflow_configs": {}, "workflow_name_mappings": {}}

    @classmethod
    def get_workflow_config(cls, workflow_id: str) -> Optional[Dict]:
        """Get raw workflow configuration"""
        cls.load_config()
        return cls._config["workflow_configs"].get(workflow_id)

    @classmethod
    def get_config(cls, workflow_id: str) -> Optional[TaskConfig]:
        """Retrieve configuration based on workflow_id"""
        config = cls.get_workflow_config(workflow_id)
        if not config:
            logger.error(f"Unknown workflow ID: {workflow_id}")
            return None
            
        return TaskConfig(
            workflow=f"{cls.BASE_PATH}/{config['workflow']}",
            endpoint=f"{cls.BASE_PATH}/{config['endpoint']}"
        )

    @classmethod
    def is_valid_task_type(cls, workflow_id: str, task_type: str) -> bool:
        """Check if the task type matches the workflow"""
        config = cls.get_workflow_config(workflow_id)
        if not config:
            return False
        return config["task_type"] == task_type

    @classmethod
    def get_output_config(cls, workflow_id: str) -> Optional[Dict[str, str]]:
        """Get output configuration for a workflow"""
        config = cls.get_workflow_config(workflow_id)
        if not config:
            return None
        return config.get("output")

    @classmethod
    def get_supported_workflow_ids(cls, workflow_name: str) -> list[str]:
        """Get the workflow IDs supported by this workflow setup"""
        cls.load_config()
        return cls._config["workflow_name_mappings"].get(workflow_name, [])