# tests/unit/test_miner.py

import pytest
import json
import time
from unittest.mock import patch, Mock, MagicMock, call, ANY
import requests
from botocore.exceptions import ClientError
from comfyui_miner import MinerService

@pytest.fixture
def mock_workflow_validation():
    """Mock workflow validation to avoid filesystem checks"""
    with patch('utils.workflow_utils.WorkflowConfig.validate') as mock_validate:
        mock_validate.return_value = {
            'hunyuan-fp8': {
                'valid': True,
                'missing_components': [],
                'workflow_ids': ['1']
            }
        }
        with patch('utils.workflow_utils.WorkflowConfig.get_valid_workflow_ids') as mock_get_ids:
            mock_get_ids.return_value = ['1']
            yield mock_validate

class TestMinerService:
    """Test suite for MinerService class focusing on critical functionality"""
    
    @pytest.fixture
    def miner_service(self, mock_comfyui, test_config, mock_workflow_validation):
        return MinerService(
            base_url=test_config['service']['base_url'],
            erc20_address=test_config['miner']['address'],
            comfyui_instance=mock_comfyui,
            s3_bucket=test_config['storage']['s3_bucket'],
            workflow_names=test_config['installation']['workflow_names']
        )

    def test_initialization_invalid_address(self, mock_comfyui, test_config, mock_workflow_validation):
        """Test initialization with invalid ERC20 address"""
        test_config['miner']['address'] = 'invalid_address'
        with pytest.raises(ValueError, match="Invalid ERC20 address format"):
            MinerService(
                base_url=test_config['service']['base_url'],
                erc20_address=test_config['miner']['address'],
                comfyui_instance=mock_comfyui,
                s3_bucket=test_config['storage']['s3_bucket'],
                workflow_names=test_config['installation']['workflow_names']
            )

    def test_send_miner_request_success(self, miner_service):
        """Test successful miner request"""
        mock_response = {'task_id': '123', 'task_type': 'txt2vid'}
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.status_code = 200
            mock_post.return_value.json.return_value = mock_response
            
            result = miner_service.send_miner_request()
            assert result == mock_response

    def test_send_miner_request_connection_error(self, miner_service):
        """Test miner request with connection error"""
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError()
            result = miner_service.send_miner_request()
            assert result is None

    def test_check_health(self, miner_service):
        """Test ComfyUI health check"""
        assert miner_service.check_health() is True
        miner_service.comfyui_instance.is_server_running.return_value = False
        assert miner_service.check_health() is False

    def test_handle_task_success(self, miner_service, sample_task_data):
        """Test successful task handling"""
        with patch('utils.task_utils.TaskProcessor.handle_output') as mock_handle_output:
            mock_handle_output.return_value = ('test_key.mp4', 1.0)
            
            with patch.object(miner_service, 'submit_result') as mock_submit:
                miner_service.handle_task('123', sample_task_data)
                
                mock_submit.assert_called_once_with(
                    task_id='123',
                    s3_key='test_key.mp4',
                    inference_latency=ANY,
                    upload_latency=1.0,
                    success=True
                )

    def test_handle_task_invalid_workflow(self, miner_service):
        """Test task handling with invalid workflow"""
        task_data = {
            'task_id': '123',
            'task_type': 'txt2vid',
            'workflow_id': 'invalid'
        }
        
        with patch.object(miner_service, 'submit_result') as mock_submit:
            miner_service.handle_task('123', task_data)
            # Changed to match the actual call with positional arguments
            mock_submit.assert_called_once_with(
                '123',  # task_id
                '',     # s3_key
                0,      # inference_latency
                0,      # upload_latency
                False,  # success
                ANY     # msg
            )
    
    def test_handle_task_s3_upload_failure(self, miner_service, sample_task_data):
        """Test handling of S3 upload failure"""
        with patch('utils.task_utils.TaskProcessor.handle_output') as mock_handle_output:
            # Simulate successful processing but failed upload
            mock_handle_output.side_effect = ClientError(
                error_response={'Error': {'Code': 'ServiceUnavailable'}},
                operation_name='PutObject'
            )
            
            with patch.object(miner_service, 'submit_result') as mock_submit:
                miner_service.handle_task('123', sample_task_data)
                mock_submit.assert_called_once_with(
                    '123', '', 
                    ANY,  # inference_latency could vary
                    0, False, 
                    'An error occurred (ServiceUnavailable) when calling the PutObject operation: Unknown'  # Updated error message
                )

    def test_handle_task_missing_required_parameters(self, miner_service):
        """Test handling of task with missing required parameters"""
        task_data = {
            'task_id': '123',
            'task_type': 'txt2vid',
            'workflow_id': '1'
            # Missing task_details/prompt
        }
        
        with patch.object(miner_service, 'submit_result') as mock_submit:
            miner_service.handle_task('123', task_data)
            mock_submit.assert_called_once_with(
                '123', '', 0, 0, False, 
                'Failed to extract parameters'
            )

    def test_submit_result_success(self, miner_service):
        """Test successful result submission"""
        with patch('requests.Session.post') as mock_post:
            mock_post.return_value.status_code = 200
            miner_service.submit_result(
                task_id='123',
                s3_key='test.mp4',
                inference_latency=1.0,
                upload_latency=0.5,
                success=True
            )
            assert mock_post.call_count == 1

    def test_submit_result_failure(self, miner_service):
        """Test failed result submission"""
        with patch('requests.Session.post') as mock_post:
            mock_post.side_effect = requests.ConnectionError()
            miner_service.submit_result(
                task_id='123',
                s3_key='test.mp4',
                inference_latency=1.0,
                upload_latency=0.5,
                success=True
            )
            assert mock_post.call_count == 1
    