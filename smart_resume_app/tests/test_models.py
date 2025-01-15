"""Tests for AI model integration."""
import pytest
from unittest.mock import Mock, patch
from src.models import OpenAIModel, AnthropicModel, AIModelManager
from src.config import Config


@pytest.fixture
def mock_config():
    """Create mock configuration."""
    config = Mock(spec=Config)
    config.get.side_effect = {
        'OPENAI_API_KEY': 'test-openai-key',
        'ANTHROPIC_API_KEY': 'test-anthropic-key'
    }.get
    return config


@pytest.fixture
def model_manager(mock_config):
    """Create AIModelManager instance with mock config."""
    return AIModelManager(mock_config)


def test_model_switching(model_manager):
    """Test model switching functionality."""
    # Test switching to valid model
    model_manager.switch_model('gpt-4')
    assert model_manager.current_model is not None
    assert isinstance(model_manager.current_model, OpenAIModel)
    
    # Test switching to invalid model
    with pytest.raises(ValueError):
        model_manager.switch_model('invalid-model')


@patch('openai.OpenAI')
def test_openai_model_processing(mock_openai, mock_config):
    """Test OpenAI model resume processing."""
    # Setup mock response
    mock_response = Mock()
    mock_response.choices = [
        Mock(message=Mock(content="Tailored resume content"))
    ]
    mock_openai.return_value.chat.completions.create.return_value = (
        mock_response
    )
    
    model = OpenAIModel(mock_config.get('OPENAI_API_KEY'))
    result = model.process_resume(
        "Original resume",
        "Job description",
        ["summary", "experience"]
    )
    
    assert result == "Tailored resume content"
    mock_openai.return_value.chat.completions.create.assert_called_once()


@patch('anthropic.Anthropic')
def test_anthropic_model_processing(mock_anthropic, mock_config):
    """Test Anthropic model resume processing."""
    # Setup mock response
    mock_response = Mock()
    mock_response.content = [Mock(text="Tailored resume content")]
    mock_anthropic.return_value.messages.create.return_value = mock_response
    
    model = AnthropicModel(mock_config.get('ANTHROPIC_API_KEY'))
    result = model.process_resume(
        "Original resume",
        "Job description",
        ["summary", "experience"]
    )
    
    assert result == "Tailored resume content"
    mock_anthropic.return_value.messages.create.assert_called_once()


def test_model_error_handling(model_manager):
    """Test error handling in model processing."""
    # Test processing without selected model
    with pytest.raises(RuntimeError):
        model_manager.process_resume(
            "Original resume",
            "Job description",
            ["summary"]
        )
    
    # Test with invalid model name
    with pytest.raises(ValueError):
        model_manager.switch_model("nonexistent-model")


def test_available_models(model_manager):
    """Test listing available models."""
    models = model_manager.list_available_models()
    assert "gpt-4" in models
    assert "gpt-3.5-turbo" in models
    assert "claude-2" in models


def test_model_initialization(mock_config):
    """Test model initialization with API keys."""
    manager = AIModelManager(mock_config)
    
    # Verify OpenAI models are initialized
    assert 'gpt-4' in manager.models
    assert 'gpt-3.5-turbo' in manager.models
    
    # Verify Anthropic model is initialized
    assert 'claude-2' in manager.models
