# task_utils.py
import json
import time
import boto3
import base64
import requests
from typing import Dict, Optional, Any, Tuple
from loguru import logger
from PIL import Image

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
        """Upload file to S3 and return upload latency"""
        try:
            # If it's a video file (webp), use the upload endpoint
            if s3_key.endswith('.webp'):
                with open(file_path, 'rb') as file:
                    video_content = base64.b64encode(file.read()).decode('utf-8')
                
                start_time = time.time()
                response = requests.post(
                    'https://1ukui6ppcf.execute-api.us-east-1.amazonaws.com/dev/upload-video',
                    json={
                        'video': video_content,
                        'filename': s3_key
                    }
                )
                upload_latency = time.time() - start_time

                if response.status_code != 200:
                    logger.error(f"Failed to upload video via endpoint: {response.text}")
                    return None

                logger.debug(f"Video uploaded successfully with key {s3_key}")
                return upload_latency

            # For other files, use direct S3 upload
            else:
                s3_client = boto3.client(
                    's3',
                    aws_access_key_id=credentials["access_key_id"],
                    aws_secret_access_key=credentials["secret_access_key"],
                    aws_session_token=credentials["session_token"]
                )

                with open(file_path, 'rb') as file:
                    start_time = time.time()
                    s3_client.put_object(Body=file, Bucket=bucket, Key=s3_key)
                    upload_latency = time.time() - start_time

                logger.debug(f"File uploaded to S3 bucket {bucket} with key {s3_key}")
                return upload_latency

        except Exception as e:
            logger.error(f"Failed to upload file to S3: {e}")
            return None

    @classmethod
    def handle_output(cls, 
                     task_id: str,
                     task_type: str,
                     output_path: str,
                     credentials: Dict[str, str],
                     bucket: str = "prod-heurist") -> Tuple[str, Optional[float]]:
        """Process and upload task output, returns (s3_key, upload_latency)"""
        try:
            # Convert output to appropriate format
            processed_path = cls._convert_output(output_path, task_type)
            
            # Generate S3 key with different patterns for video vs image
            if task_type == 'txt2vid':
                s3_key = f"test-video/mochi-fp8-{credentials['miner_address']}-{task_id}.webp"
            else:
                s3_key = f"{task_id}.jpg"
            
            # Upload to S3
            upload_latency = cls._upload_to_s3(credentials, processed_path, bucket, s3_key)
            if not upload_latency:
                logger.error("Failed to upload result")
                return s3_key, None
                
            return s3_key, upload_latency
        except Exception as e:
            logger.exception(f"Failed to handle task output: {e}")
            return "", None