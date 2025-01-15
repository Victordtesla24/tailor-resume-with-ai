"""UI Components for the Resume Tailoring Application"""
from typing import Dict, Any


def create_app_components() -> Dict[str, Any]:
    """Create and return UI components configuration."""
    return {
        'form': {
            'resume_input': {
                'id': 'resume-input',
                'label': 'Upload Resume',
                'type': 'file',
                'accept': '.txt,.doc,.docx',
                'required': True
            },
            'job_description': {
                'id': 'job-description',
                'label': 'Job Description',
                'type': 'textarea',
                'placeholder': 'Paste job description here...',
                'required': True
            },
            'model_selector': {
                'id': 'model-selector',
                'label': 'Select AI Model',
                'type': 'select',
                'options': [
                    {'value': 'gpt-4', 'label': 'GPT-4 (Best Quality)'},
                    {'value': 'gpt-3.5-turbo', 'label': 'GPT-3.5 (Faster)'},
                    {'value': 'claude-2', 'label': 'Claude 2 (Alternative)'}
                ],
                'default': 'gpt-4'
            }
        },
        'buttons': {
            'submit': {
                'id': 'submit-button',
                'label': 'Tailor Resume',
                'type': 'submit',
                'class': 'primary'
            },
            'reset': {
                'id': 'reset-button',
                'label': 'Reset',
                'type': 'reset',
                'class': 'secondary'
            }
        },
        'results': {
            'container': {
                'id': 'results-container',
                'class': 'results-section'
            },
            'download': {
                'id': 'download-button',
                'label': 'Download Tailored Resume',
                'class': 'download-button'
            }
        }
    }
