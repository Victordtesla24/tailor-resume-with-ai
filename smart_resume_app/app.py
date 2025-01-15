#!/usr/bin/env python3
"""Main application module for the Resume Tailoring Application."""
from flask import Flask, request, render_template, jsonify
from src.components import create_app_components
from src.models import ResumeProcessor
from src.config import load_config
from src.utils import setup_logging, validate_input

# Initialize Flask application
app = Flask(__name__)
config = load_config()
logger = setup_logging()

# Initialize components
ui_components = create_app_components()
resume_processor = ResumeProcessor(config)


@app.route('/', methods=['GET'])
def index():
    """Render the main application page."""
    try:
        return render_template('index.html', components=ui_components)
    except Exception as e:
        logger.error(f"Error rendering index page: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500


@app.route('/tailor', methods=['POST'])
def tailor_resume():
    """Process and tailor the resume based on job description."""
    try:
        data = request.get_json()
        if not validate_input(data):
            return jsonify({"error": "Invalid input data"}), 400

        resume_text = data.get('resume')
        job_description = data.get('job_description')
        model_choice = data.get('model', 'gpt-4')

        tailored_resume = resume_processor.process_resume(
            resume_text,
            job_description,
            model_choice
        )

        return jsonify({"tailored_resume": tailored_resume})
    except Exception as e:
        logger.error(f"Error processing resume: {str(e)}")
        return jsonify({"error": str(e)}), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({"status": "healthy"})


if __name__ == '__main__':
    app.run(debug=config.get('DEBUG', False), host='0.0.0.0', port=5000)
