#!/usr/bin/env bash
# Exit immediately if a command exits with a non-zero status (fails).
set -o errexit

# Install system dependencies (like pdftotext)
apt-get update -y
apt-get install -y poppler-utils

# Install Python dependencies from our shopping list (requirements.txt)
pip install -r requirements.txt

# Gather all static files (CSS, JS, images) into the 'staticfiles' folder
# --no-input means it won't ask us questions during this process
python manage.py collectstatic --no-input

# Apply any changes to the database (like creating tables for your models)
python manage.py migrate