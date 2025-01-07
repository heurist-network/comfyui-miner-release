# tests/unit/test_workflow.py
import os
import pytest
from unittest.mock import patch
from utils.workflow_utils import WorkflowConfig

@pytest.fixture
def mock_file_checks():
    """Mock filesystem checks to avoid filesystem dependencies"""
    with patch('os.path.exists') as mock_exists:
        mock_exists.return_value = True
        yield mock_exists

class TestWorkflowConfig:
    """Test suite for WorkflowConfig class"""

    def test_invalid_workflow_config(self):
        """Test handling of invalid workflow configuration"""
        with patch.object(WorkflowConfig, '_config', {"invalid_key": {}}):
            with pytest.raises(KeyError):
                WorkflowConfig.get_workflow_config("any_workflow")

    def test_workflow_config_structure(self, workflow_names):
        """Test basic workflow configuration (no filesystem dependencies)"""
        for workflow in workflow_names:
            workflow_ids = WorkflowConfig.get_supported_workflow_ids(workflow)
            assert isinstance(workflow_ids, list)
            assert len(workflow_ids) > 0

    def test_validation_result_format(self, workflow_names):
        """Test that workflow validation returns the expected response format"""
        for workflow in workflow_names:
            validation_result = WorkflowConfig.validate(workflow)
            
            # Verify response structure
            assert isinstance(validation_result, dict)
            assert workflow in validation_result
            result = validation_result[workflow]
            
            # Verify all required fields exist
            assert "valid" in result
            assert "missing_components" in result
            assert "workflow_ids" in result
            assert isinstance(result["missing_components"], list)
            assert isinstance(result["workflow_ids"], list)

    @pytest.mark.requires_comfyui
    def test_workflow_components_existence(self, workflow_names):
        """Test that all required workflow components exist in ComfyUI installation:"""
        if not os.path.exists('./ComfyUI'):
            pytest.skip("ComfyUI installation not found")
        
        for workflow in workflow_names:
            validation_result = WorkflowConfig.validate(workflow)
            
            # Verify all components are present
            assert validation_result[workflow]["valid"], \
                f"Missing components for {workflow}: {validation_result[workflow]['missing_components']}"
            assert not validation_result[workflow]["missing_components"], \
                f"Component validation failed: {validation_result[workflow]['missing_components']}"