import os
import yaml
import json
import toml
from typing import Dict, Optional, List, Union
from dataclasses import dataclass
from loguru import logger
from pathlib import Path

@dataclass
class TaskConfig:
    """Configuration for different task types and their workflows"""
    workflow: str
    endpoint: str

class WorkflowConfig:
    """Workflow configuration management"""
    
    BASE_PATH = "example"
    _config = None
    _snapshots = {}  # Cache for loaded snapshots

    # Core configuration loading methods
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
    def _get_comfyui_path(cls) -> str:
        """Determine correct ComfyUI path based on environment"""
        config_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'config.toml')
        with open(config_path, 'r') as f:
            config = toml.load(f)
        
        if os.path.exists('/.dockerenv'):
            return config['installation']['docker_comfyui_home']
        return config['installation']['comfyui_home']

    @classmethod
    def _load_snapshot(cls, workflow_id: str) -> Optional[Dict]:
        """Load snapshot file for a workflow"""
        if workflow_id in cls._snapshots:
            return cls._snapshots[workflow_id]

        config = cls.get_workflow_config(workflow_id)
        if not config:
            return None

        snapshot_path = os.path.join(cls.BASE_PATH, "snapshots", config['workflow'].split('/')[-1])
        try:
            with open(snapshot_path, 'r') as f:
                snapshot = json.load(f)
                cls._snapshots[workflow_id] = snapshot
                return snapshot
        except Exception as e:
            logger.error(f"Failed to load snapshot for workflow {workflow_id}: {e}")
            return None

    # Configuration retrieval methods
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

    # Validation methods
    @classmethod
    def is_valid_task_type(cls, workflow_id: str, task_type: str) -> bool:
        """Check if the task type matches the workflow"""
        config = cls.get_workflow_config(workflow_id)
        if not config:
            return False
        return config["task_type"] == task_type

    @classmethod
    def validate(cls, workflows: Optional[Union[str, List[str]]] = None) -> Dict[str, Dict]:
        """Validate one or more workflows and their required components."""
        cls.load_config()
        results = {}
        
        # Normalize input to list
        workflows = ([workflows] if isinstance(workflows, str) 
                    else workflows or list(cls._config["workflow_name_mappings"].keys()))

        for workflow in workflows:
            # Map workflow name/id to result key and workflow ids
            workflow_ids = (cls.get_supported_workflow_ids(workflow) 
                        if workflow in cls._config["workflow_name_mappings"] 
                        else [workflow])
            key = workflow if workflow in cls._config["workflow_name_mappings"] else next(
                (name for name, ids in cls._config["workflow_name_mappings"].items() 
                if workflow in ids), workflow)

            result = {"valid": True, "missing_components": [], "workflow_ids": workflow_ids}

            for workflow_id in workflow_ids:
                # Validate snapshot existence and structure
                snapshot = cls._load_snapshot(workflow_id)
                if not snapshot:
                    result.update({
                        "valid": False,
                        "missing_components": [f"Missing or invalid snapshot for workflow ID: {workflow_id}"]
                    })
                    continue

                # Validate required snapshot fields
                missing_fields = {"comfyui", "git_custom_nodes", "downloads"} - set(snapshot.keys())
                if missing_fields:
                    result.update({
                        "valid": False,
                        "missing_components": [f"Snapshot missing required fields: {', '.join(missing_fields)}"]
                    })
                    continue

                # Validate component existence in ComfyUI installation
                comfyui_path = cls._get_comfyui_path()
                custom_nodes_path = os.path.join(comfyui_path, "custom_nodes")

                # Check git nodes, file nodes, and model files
                missing = []
                for repo_url, _ in snapshot["git_custom_nodes"].items():
                    node_path = os.path.join(custom_nodes_path, repo_url.split("/")[-1].replace(".git", ""))
                    if not os.path.exists(node_path):
                        missing.append(f"Missing custom node: {repo_url.split('/')[-1].replace('.git', '')}")

                for node in snapshot.get("file_custom_nodes", []):
                    if not node.get("disabled") and not os.path.exists(os.path.join(custom_nodes_path, node["filename"])):
                        missing.append(f"Missing custom node file: {node['filename']}")

                for model_path in snapshot["downloads"].keys():
                    if not os.path.exists(os.path.join(comfyui_path, model_path)):
                        missing.append(f"Missing model: {model_path}")

                if missing:
                    result.update({"valid": False, "missing_components": missing})

            results[key] = result
            
        logger.info(f"Workflow validation results: {results}")
        return results

    @classmethod
    def get_valid_workflow_ids(cls, workflow_names: List[str]) -> List[str]:
        """Validate workflows and return supported workflow IDs if all valid. Raises ValueError with details if any workflow is invalid."""
        validation_results = cls.validate(workflow_names)
        invalid_workflows = [name for name, result in validation_results.items() if not result["valid"]]
        
        if invalid_workflows:
            for name in invalid_workflows:
                logger.error(f"Missing components for {name}:")
                for missing in validation_results[name]["missing_components"]:
                    logger.error(f"  - {missing}")
            raise ValueError("Some workflows are not properly installed. Please run setup first.")

        return list(set().union(*(
            cls.get_supported_workflow_ids(name) for name in workflow_names
        )))