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

# Create a superuser if environment variables are set
# --noinput means it won't prompt for username/email/password
# || true allows the script to continue even if createsuperuser fails (e.g., user already exists)
if [[ -n "$DJANGO_SUPERUSER_USERNAME" && -n "$DJANGO_SUPERUSER_PASSWORD" ]]; then
    python manage.py createsuperuser --noinput \
        --username "$DJANGO_SUPERUSER_USERNAME" \
        --email "${DJANGO_SUPERUSER_EMAIL:-atiqahawal285@gmail.com}" || true
fi