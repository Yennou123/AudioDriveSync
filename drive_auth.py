#drive_auth.py
import os
import pickle
import sys
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google.auth.exceptions import RefreshError
from logger_utils import setup_logger
from paths import get_token_file, get_base_dir

# Créer le dossier AudioDriveSync dans AppData si inexistant
auth_logger = setup_logger("auth", "auth.log")
auth_logger.info("=== Auth logger initialisé ===")

SCOPES = ['https://www.googleapis.com/auth/drive.file']

def resource_path(relative_path):
    """ Permet de récupérer le chemin absolu même dans un EXE PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    # Ajout : vérifier aussi dans le dossier ProgramData\AudioDriveSync
    programdata_dir = get_base_dir()
    install_dir = os.path.dirname(sys.executable)  # emplacement du .exe installé

    # Tester plusieurs chemins
    for path in [programdata_dir, base_path, install_dir]:
        candidate = os.path.join(path, relative_path)
        if os.path.exists(candidate):
            return candidate
    return os.path.join(base_path, relative_path)

def authenticate_drive():
    creds = None
    token_path = get_token_file()
    creds_path = resource_path('credentials.json')

    # Vérifier que le fichier credentials existe
    if not os.path.exists(creds_path):
        auth_logger.error(f"Fichier credentials.json introuvable : {creds_path}")
        raise FileNotFoundError(f"Le fichier credentials.json est requis pour l'authentification Google Drive")

    try:
        # Charger les credentials existants
        if os.path.exists(token_path):
            with open(token_path, 'rb') as f:
                creds = pickle.load(f)
            auth_logger.info("Token d'authentification chargé depuis le cache")

        # Si pas de credentials valides, en créer de nouveaux
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    auth_logger.info("Rafraîchissement du token d'authentification...")
                    creds.refresh(Request())
                    auth_logger.info("Token rafraîchi avec succès")
                except RefreshError as e:
                    auth_logger.warning(f"Impossible de rafraîchir le token : {e}")
                    creds = None
            if not creds:
                auth_logger.info("Démarrage du flux d'authentification OAuth...")
                flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                creds = flow.run_local_server(port=0)
                auth_logger.info("Authentification OAuth réussie")

            # Sauvegarder les credentials
            with open(token_path, 'wb') as f:
                pickle.dump(creds, f)
            auth_logger.info("Token d'authentification sauvegardé")

        # Construire le service Drive
        service = build('drive', 'v3', credentials=creds)
        auth_logger.info("Service Google Drive initialisé avec succès")
        return service

    except Exception as e:
        auth_logger.error(f"Erreur lors de l'authentification Google Drive : {e}")
        raise
