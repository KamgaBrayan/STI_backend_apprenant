#!/usr/bin/env bash
# exit on error (arrête le script si une commande échoue)
set -o errexit

# 1. Installation des dépendances
pip install -r requirements.txt

# 2. Collecte des fichiers statiques (CSS/JS pour l'admin)
python manage.py collectstatic --no-input

# 3. Application des migrations (Mise à jour de la structure de la BDD)
python manage.py migrate

# 4. Synchronisation des Cas Cliniques (Seed)
# Note : On utilise '|| true' pour que le déploiement n'échoue pas 
# si l'API externe (DATA_BACKEND_URL) est temporairement indisponible.
echo "🔄 Démarrage de la synchronisation des cas..."
python manage.py sync_validated_cases || echo "⚠️ Attention : La synchronisation a échoué, mais le déploiement continue."