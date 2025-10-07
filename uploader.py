# uploader.py
import os
import hashlib
import json
import logging
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError
from drive_auth import authenticate_drive
from logger_utils import setup_logger
from paths import get_uploaded_db

# --- Initialisation logging robuste ---
uploader_logger = setup_logger("uploader", "uploader.log")
uploader_logger.info("=== uploader logger initialisé, fichier ===")

APP_NAME = "AudioDriveSync"
UPLOAD_DB = get_uploaded_db()


def load_uploaded_db():
    try:
        if os.path.exists(UPLOAD_DB):
            with open(UPLOAD_DB, 'r') as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        uploader_logger.error(f"Erreur lors du chargement de la base de données : {e}")
    return {}


def save_uploaded_db(data):
    try:
        with open(UPLOAD_DB, 'w') as f:
            json.dump(data, f, indent=2)
    except IOError as e:
        uploader_logger.error(f"Erreur lors de la sauvegarde de la base de données : {e}")


def get_file_hash(file_path):
    try:
        hasher = hashlib.md5()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hasher.update(chunk)
        return hasher.hexdigest()
    except IOError as e:
        uploader_logger.error(f"Erreur lors du calcul du hash du fichier {file_path}: {e}")
        return None


def parse_audio_filename(filename):
    """ Ex: lumiere_2024_06_EPEPP.mp3 → ("lumiere", "2024", "06", "EPEPP") """
    name = os.path.splitext(filename)[0]
    parts = name.split('_')
    if len(parts) >= 4:
        tabernacle, year, month, category = parts[:4]
        return tabernacle.capitalize(), year, month, category.lower()
    return None, None, None, None


def ensure_drive_path(service, root_folder_id, path_parts):
    parent_id = root_folder_id
    for part in path_parts:
        results = service.files().list(
            q=f"'{parent_id}' in parents and name='{part}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
            spaces='drive',
            fields='files(id, name)'
        ).execute()
        files = results.get('files', [])
        if files:
            parent_id = files[0]['id']
        else:
            file_metadata = {
                'name': part,
                'mimeType': 'application/vnd.google-apps.folder',
                'parents': [parent_id]
            }
            folder = service.files().create(body=file_metadata, fields='id').execute()
            parent_id = folder['id']
    return parent_id


def upload_file(file_path, drive_root_name_or_url):
    try:
        service = authenticate_drive()
        uploaded = load_uploaded_db()
        file_hash = get_file_hash(file_path)
        if file_hash is None:
            uploader_logger.error(f"Impossible de calculer le hash pour {file_path}")
            return

        filename = os.path.basename(file_path)
        if file_hash in uploaded:
            try:
                service.files().get(fileId=uploaded[file_hash]['id']).execute()
                uploader_logger.info(f"Déjà sur Drive : {file_path}")
                return
            except HttpError as e:
                if e.resp.status == 404:
                    uploader_logger.info(f"Fichier supprimé du Drive, réimportation...")
                else:
                    uploader_logger.error(f"Erreur lors de la vérification du fichier : {e}")
                    return

        
       # Si un lien Drive est fourni
        if "drive.google.com" in drive_root_name_or_url:
            import re
            match = re.search(r"/folders/([a-zA-Z0-9_-]+)", drive_root_name_or_url)
            if not match:
                uploader_logger.error("Lien Drive invalide.")
                return
            root_folder_id = match.group(1)
        else:
            # Ici on veut chercher/créer un dossier racine nommé comme drive_root_name_or_url
            try:
                # Vérifier si le dossier existe déjà à la racine
                results = service.files().list(
                    q=f"'{ 'root' }' in parents and name='{drive_root_name_or_url}' and mimeType='application/vnd.google-apps.folder' and trashed=false",
                    spaces='drive',
                    fields='files(id, name)'
                ).execute()
                files = results.get('files', [])
                if files:
                    root_folder_id = files[0]['id']
                else:
                    # Créer le dossier racine
                    file_metadata = {
                        'name': drive_root_name_or_url,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': ['root']
                    }
                    folder = service.files().create(body=file_metadata, fields='id').execute()
                    root_folder_id = folder['id']
            except Exception as e:
                uploader_logger.error(f"Erreur lors de la création du dossier racine : {e}")
                return


        # Extraire infos tabernacle, year, month, category
        tabernacle, year, month, category = parse_audio_filename(filename)
        if not all([tabernacle, year, month, category]):
            logging.warning(f"Nom de fichier invalide pour hiérarchie : {filename}")
            return

        path = [tabernacle, year, month, category]
        target_folder_id = ensure_drive_path(service, root_folder_id, path)

        media = MediaFileUpload(file_path, resumable=True)
        file_metadata = {
            'name': filename,
            'parents': [target_folder_id]
        }

        uploaded_file = service.files().create(
            body=file_metadata,
            media_body=media,
            fields='id'
        ).execute()

        uploaded[file_hash] = {'name': filename, 'id': uploaded_file.get('id')}
        save_uploaded_db(uploaded)
        uploader_logger.info(f"Uploadé dans {path} : {filename}")

    except HttpError as e:
        uploader_logger.error(f"Erreur API Google Drive : {e}")
    except Exception as e:
        uploader_logger.error(f"Erreur inattendue lors de l'upload : {e}")
