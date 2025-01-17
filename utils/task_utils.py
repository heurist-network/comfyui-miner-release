# task_utils.py
import json
import time
import boto3
import base64
import requests
from PIL import Image
from loguru import logger
from requests_aws4auth import AWS4Auth
from utils.workflow_utils import WorkflowConfig
from typing import Dict, Optional, Any, Tuple

class TaskProcessor:
    """Handles task-related operations including parameter extraction, execution, and result handling"""
    
    @staticmethod
    def extract_parameters(task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Extract and validate task parameters"""
        try:
            info = task_data.get("task_details", {})
            if isinstance(info, str):
                info = json.loads(info)
            return {"prompt": info.get("prompt")} if "prompt" in info else info.get("parameters", {})
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse task parameters: {e}")
            return None
        except Exception as e:
            logger.exception(f"Parameter extraction failed: {e}")
            return None

    @staticmethod
    def execute_workflow(comfyui_instance: Any,
                        workflow_path: str,
                        endpoint_path: str,
                        parameters: Dict[str, Any]) -> Tuple[Dict[str, Any], float]:
        """Execute workflow and measure performance"""
        start_time = time.time()
        output_data = comfyui_instance.run_workflow(
            workflow_path,
            endpoint_path,
            parameters
        )
        inference_latency = time.time() - start_time
        logger.info(f"Workflow executed in {inference_latency:.2f} seconds")
        return output_data, inference_latency

    @staticmethod
    def _convert_output(output_path: str, task_type: str) -> str:
        """Convert output to appropriate format based on task type"""
        if not output_path:
            logger.warning("Empty output path received")
            return output_path
            
        if task_type == "txt2vid":
            logger.info(f"Processing video output: {output_path}")
            return output_path
            
        if output_path.lower().endswith(".png"):
            try:
                with logger.catch(message="Image conversion failed"):
                    img = Image.open(output_path)
                    img = img.convert("RGB")
                    new_image_path = output_path.replace(".png", ".jpg")
                    img.save(new_image_path, "JPEG", quality=98, optimize=True)
                    logger.info(f"Image converted successfully: {new_image_path}")
                    return new_image_path
            except Exception as e:
                logger.exception(f"Failed to convert image: {e}")
                return output_path
                
        return output_path

    @staticmethod
    def _upload_to_s3(credentials: Dict[str, str],
                    file_path: str,
                    bucket: str,
                    s3_key: str) -> Optional[float]:
        """Upload file to S3 via upload-video endpoint and return upload latency"""
        try:
            auth = AWS4Auth(
                credentials["access_key_id"],
                credentials["secret_access_key"],
                'us-east-1',
                'execute-api',
                session_token=credentials["session_token"]
            )

            with open(file_path, 'rb') as file:
                file_content = base64.b64encode(file.read()).decode('utf-8')
            
            start_time = time.time()
            response = requests.post(
                'https://1ukui6ppcf.execute-api.us-east-1.amazonaws.com/dev/upload-video',
                json={
                    'file': file_content,
                    'filename': s3_key
                },
                auth=auth
            )
            upload_latency = time.time() - start_time

            if response.status_code != 200:
                logger.error(f"Failed to upload file via endpoint: {response.text}")
                return None

            logger.debug(f"File uploaded successfully with key {s3_key}")
            return upload_latency

        except Exception as e:
            logger.error(f"Failed to upload file: {e}")
            return None

    @classmethod
    def handle_output(cls, 
                     task_id: str,
                     task_type: str,
                     output_path: str,
                     credentials: Dict[str, str],
                     workflow_id: str,   
                     bucket: str = "prod-heurist") -> Tuple[str, Optional[float]]:
        """Process and upload task output, returns (s3_key, upload_latency)"""
        try:
            # Convert output to appropriate format
            processed_path = cls._convert_output(output_path, task_type)
            
            # Get output configuration from workflow config
            output_config = WorkflowConfig.get_output_config(workflow_id)
            if not output_config:
                logger.error(f"No output configuration found for workflow ID: {workflow_id}")
                return "", None

            # Generate S3 key based on configuration
            if task_type == 'txt2vid':
                s3_key = f"test-video/{output_config['prefix']}-{credentials['miner_address']}-{task_id}.{output_config['format']}"
            elif task_type == 'txt2img':
                s3_key = f"flux-lora/{output_config['prefix']}-{credentials['miner_address']}-{task_id}.{output_config['format']}"
            else:
                logger.error(f"Invalid task type: {task_type}")
                return "", None
            
            # Upload to S3
            upload_latency = cls._upload_to_s3(credentials, processed_path, bucket, s3_key)
            if not upload_latency:
                logger.error("Failed to upload result")
                return s3_key, None
                
            return s3_key, upload_latency
        except Exception as e:
            logger.exception(f"Failed to handle task output: {e}")
            return "", None