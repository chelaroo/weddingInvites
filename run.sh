#!/bin/bash
set -e

source venv/bin/activate
gunicorn -b localhost:8888 -w 2 app:app
