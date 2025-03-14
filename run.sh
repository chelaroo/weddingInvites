#!/bin/bash
set -e

gunicorn -b localhost:8888 -w 2 app:app
