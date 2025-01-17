#!/bin/bash

# Exit on error
set -e

echo "Setting up Smart Resume Tailor..."

# Create virtual environment if it doesn't exist
if [ ! -d "resume_app_env" ]; then
    echo "Creating virtual environment..."
    python3 -m venv resume_app_env
fi

# Activate virtual environment
echo "Activating virtual environment..."
source resume_app_env/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit .env file with your API keys before running the application."
    exit 1
fi

# Run the application
echo "Starting the application..."
python app.py
