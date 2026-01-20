#!/bin/bash
# Build script for Render deployment

set -o errexit

cd config
python manage.py migrate
python manage.py collectstatic --no-input
