#!/usr/bin/env bash
# exit on error
set -o errexit

pip install -r requirements.txt

# Collecte les fichiers statiques (CSS, JS)
python manage.py collectstatic --no-input

# Applique les migrations à la base de données PostgreSQL
python manage.py migrate