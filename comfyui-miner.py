# comfyui-miner.py
import os
import time
import json
import requests
import argparse
import threading
from web3 import Web3
from loguru import logger
from dotenv import load_dotenv
from requests import Session
from typing import Dict, Any, Optional
from multiprocessing import current_process
from comfyui_service.comfyui import ComfyUI
from utils.config_utils import load_config, setup_logging
from utils.workflow_utils import WorkflowConfig
from utils.task_utils import TaskProcessor

class MinerService:
    """MinerService class for handling mining tasks and submitting results."""
    def __init__(self, base_url: str, erc20_address: str, comfyui_instance: ComfyUI, s3_bucket: str, workflow_names: str):
        self.base_url = base_url
        self.erc20_address = erc20_address
        self.comfyui_instance = comfyui_instance
        self.s3_bucket = s3_bucket
        self.workflow_names = workflow_names

        self.session = Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.supported_workflow_ids = WorkflowConfig.get_valid_workflow_ids(workflow_names)

        logger.info(f"MinerService ready with {len(self.supported_workflow_ids)} workflows for miner {self.erc20_address} "
                   f"(workflows: {', '.join(workflow_names)})")

    def send_miner_request(self, timeout: int = 10) -> Optional[Dict[str, Any]]:
        """Send mining request to the server and return task data if available"""
        max_retries = 3
        base_wait = 2  # Start with 2 seconds wait

        for attempt in range(max_retries):
            try:
                with Session() as session:
                    session.headers.update({'Content-Type': 'application/json'})
                    response = session.post(
                        f"{self.base_url}/miner_request",
                        json={
                            'erc20_address': self.erc20_address,
                            'workflow_ids': self.supported_workflow_ids,  # Send all supported workflow IDs
                        },
                        timeout=timeout
                    )

                    if response.status_code == 200:
                        task_data = response.json()
                        logger.debug(f"Received response: {task_data}")
                        return task_data
                    else:
                        wait_time = base_wait * (2 ** attempt)  # Exponential backoff
                        logger.warning(f"Request failed with status {response.status_code}, retrying in {wait_time}s...")
                        time.sleep(wait_time)

            except (requests.Timeout, requests.ConnectionError) as e:
                wait_time = base_wait * (2 ** attempt)
                logger.warning(f"Connection error: {str(e)}, retrying in {wait_time}s...")
                time.sleep(wait_time)
            except Exception as e:
                logger.exception(f"Request error: {e}")
                return None

        logger.error("Max retries reached, giving up")
        return None

    def handle_task(self, task_id: str, task_data: Dict[str, Any]) -> None:
        """Process a task through three stages"""
        with logger.contextualize(task_id=task_id):
            logger.info(f"Starting task processing in process {current_process().pid}")

        logger.info(f"Task data: {task_data}")
        try:
            # 1. Task Setup
            task_type = task_data.get("task_type")
            workflow_id = task_data.get("workflow_id")
            
            if not workflow_id:
                logger.error("Missing workflow_id")
                self.submit_result(task_id, "", 0, 0, False, "Missing workflow_id")
                return

            if not WorkflowConfig.is_valid_task_type(workflow_id, task_type):
                logger.error(f"Invalid task type {task_type} for workflow {workflow_id}")
                self.submit_result(task_id, "", 0, 0, False, "Invalid task type for workflow")
                return

            workflow_config = WorkflowConfig.get_config(workflow_id)
            if not workflow_config:
                logger.error(f"Failed to get workflow config for workflow {workflow_id}")
                self.submit_result(task_id, "", 0, 0, False, "Invalid workflow configuration")
                return

            # Extract parameters from task data
            parameters = TaskProcessor.extract_parameters(task_data)
            if not parameters:
                logger.error("Missing or invalid task parameters")
                self.submit_result(task_id, "", 0, 0, False, "Failed to extract parameters")
                return

            # 2. Task Execution
            output_data, inference_latency = TaskProcessor.execute_workflow(
                self.comfyui_instance,
                workflow_config.workflow,
                workflow_config.endpoint,
                parameters
            )

            if "error" in output_data:
                logger.error(f"Task execution failed: {output_data['error']}")
                self.submit_result(task_id, "", 0, 0, False, output_data["error"])
                return

            # 3. Result Handling
            credentials = {
                "access_key_id": task_data.get("access_key_id"),
                "secret_access_key": task_data.get("secret_access_key"),
                "session_token": task_data.get("session_token"),
                "miner_address": self.erc20_address
            }
            
            s3_key, upload_latency = TaskProcessor.handle_output(
                task_id,
                task_type,
                output_data,
                credentials,
                workflow_id,
                self.s3_bucket
            )

            if not upload_latency:
                logger.error("Failed to upload result")
                self.submit_result(task_id, "", inference_latency, 0, False, "Upload failed")
                return

            self.submit_result(
                task_id=task_id,
                s3_key=s3_key,
                inference_latency=inference_latency,
                upload_latency=upload_latency,
                success=True
            )

        except Exception as e:
            logger.exception(f"Task processing failed: {e}")
            self.submit_result(task_id, "", 0, 0, False, str(e))

    def submit_result(self, task_id: str, s3_key: str,
                     inference_latency: float, upload_latency: float,
                     success: bool, msg: str = "") -> None:
        """Submit task results back to the server"""
        with logger.contextualize(task_id=task_id):
            try:
                result = {
                    "success": success,
                    "task_id": task_id,
                    "miner_id": self.erc20_address,
                    "result": s3_key,
                    "inference_latency": inference_latency,
                    "upload_latency": upload_latency,
                    "msg": msg,
                }

                logger.debug(f"Submitting result: {result}")
                with Session() as session:
                    session.headers.update({'Content-Type': 'application/json'})
                    response = session.post(
                        f"{self.base_url}/miner_submit",
                        json=result,
                        timeout=10
                    )

                    if response.status_code == 200:
                        logger.success(f"Result submitted successfully")
                    else:
                        logger.error(f"Submit failed with status code: {response.status_code}")

            except requests.Timeout:
                logger.error("Request timed out while submitting result")
            except Exception as e:
                logger.exception(f"Failed to submit result: {e}")

    def start_service(self, interval: int = 2) -> None:
        """Start the mining service loop"""
        logger.info("Starting mining service")
        while True:
            try:
                task_data = self.send_miner_request()
                if task_data and task_data.get("task_id") and "running" not in task_data.get("msg", ""):
                    logger.info(f"Starting new task: {task_data['task_id']}")
                    threading.Thread(
                        target=self.handle_task,
                        args=(task_data["task_id"], task_data)
                    ).start()
            except Exception as e:
                logger.exception(f"Service loop error: {e}")
            
            time.sleep(interval)

def main():
    load_dotenv()

    """Main entry point for the ComfyUI mining service"""
    parser = argparse.ArgumentParser(description="Run the ComfyUI Mining Service")
    parser.add_argument('--port', type=int,
                       help='Port for the ComfyUI service (overrides config value)')
    parser.add_argument('--log-level', type=str, default="INFO",
                       choices=["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"],
                       help='Logging level')
    parser.add_argument('--erc20-address', type=str,
                       help='ERC20 address for mining (overrides config value)')
    args = parser.parse_args()

    # Initialize logging
    setup_logging(args.log_level)

    try:
        # Load configuration and initialize services
        config = load_config()
        
        # Use command line port if provided, otherwise use config port
        port = os.environ.get('COMFYUI_PORT') or args.port or config['service']['port']
        erc20_address = os.environ.get('ERC20_ADDRESS') or args.erc20_address or config['miner']['address']
        workflow_names = (
            [w.strip() for w in os.environ.get('WORKFLOW_NAMES', '').split(',') if w.strip()] or
            [w.strip() for w in (args.workflows or '').split(',') if w.strip()] or 
            config['installation']['workflow_names']
        )

        if not Web3.is_address(erc20_address):
            logger.error(f"Invalid ERC20 address: {erc20_address}")
            raise ValueError("Invalid ERC20 address format")
        
        comfyui_instance = ComfyUI(config, server_port=str(port))
        logger.info(f"ComfyUI instance initialized on port {port}")

        # Start mining service
        miner_service = MinerService(
            base_url=config['service']['base_url'],
            erc20_address=erc20_address,
            comfyui_instance=comfyui_instance,
            s3_bucket=config['storage']['s3_bucket'],
            workflow_names=workflow_names
        )

        miner_service.start_service()

    except Exception as e:
        logger.exception(f"Application startup failed: {e}")
        raise

if __name__ == '__main__':
    main()