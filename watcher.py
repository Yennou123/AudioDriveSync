# watcher.py
import time
import os
import json
import threading
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from uploader import upload_file
from logger_utils import setup_logger
from paths import get_config_file, get_base_dir

# --- Initialisation logging robuste ---
watcher_logger = setup_logger("watcher", "watcher.log")
watcher_logger.info("=== Watcher logger initialisé ===")

AUDIO_EXTENSIONS = ['.mp3', '.wav', '.ogg', '.flac', '.m4a', '.aac']
APP_NAME = "AudioDriveSync"
CONFIG_DIR = get_base_dir()
CONFIG_FILE = get_config_file()
# --- variables globales ---
observer = None
stop_flag = threading.Event()


class AudioHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.local_folder = config['local_folder']
        self.drive_folder = config['drive_folder']
        self.processing_files = set()  # Éviter les doublons

    def on_created(self, event):
        if event.is_directory:
            return
        filepath = event.src_path
        _, ext = os.path.splitext(filepath)
        if ext.lower() in AUDIO_EXTENSIONS:
            if filepath in self.processing_files:
                watcher_logger.info(f"Fichier déjà en cours de traitement : {filepath}")
                return
            self.processing_files.add(filepath)
            try:
                # Attendre que le fichier soit complètement écrit
                time.sleep(2)
                # Vérifier que le fichier existe toujours
                if not os.path.exists(filepath):
                    watcher_logger.warning(f"Fichier supprimé pendant le traitement : {filepath}")
                    return
                # Vérifier la taille du fichier
                file_size = os.path.getsize(filepath)
                if file_size == 0:
                    watcher_logger.warning(f"Fichier vide détecté : {filepath}")
                    return
                watcher_logger.info(f"Nouveau fichier détecté : {filepath} ({file_size} bytes)")
                upload_file(filepath, self.drive_folder)
            except Exception as e:
                watcher_logger.error(f"Erreur lors du traitement du fichier {filepath}: {e}")
            finally:
                self.processing_files.discard(filepath)

    def on_moved(self, event):
        if not event.is_directory:
            filepath = event.dest_path
            _, ext = os.path.splitext(filepath)
            if ext.lower() in AUDIO_EXTENSIONS:
                watcher_logger.info(f"Fichier déplacé détecté : {filepath}")
                time.sleep(1)
                upload_file(filepath, self.drive_folder)


def start_watcher():
    global observer
    try:
        watcher_logger.info("=== DÉMARRAGE WATCHER ===")
        if not os.path.exists(CONFIG_FILE):
            watcher_logger.error(f"Fichier de configuration introuvable : {CONFIG_FILE}")
            return

        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            config = json.load(f)

        path = config['local_folder']
        if not os.path.exists(path):
            watcher_logger.error(f"Dossier local introuvable : {path}")
            return

        watcher_logger.info(f"Configuration chargée - Dossier: {path}")
        watcher_logger.info(f"Configuration chargée - Drive: {config['drive_folder']}")

        event_handler = AudioHandler(config)
        observer = Observer()
        observer.schedule(event_handler, path=path, recursive=False)

        # 🔧 Démarrage stable dans un thread séparé
        threading.Thread(target=observer.start, daemon=True).start()
        time.sleep(0.5)  # Laisser le temps au thread d’initier

        watcher_logger.info(f"Observer démarré, surveillance active pour : {path}")

        while not stop_flag.is_set():
            if observer is None or not observer.is_alive():
                watcher_logger.error("Observer s'est arrêté de manière inattendue")
                break
            time.sleep(1)

        watcher_logger.info("Signal d'arrêt reçu, arrêt du watcher...")

    except Exception as e:
        watcher_logger.error(f"Erreur inattendue dans le watcher : {e}", exc_info=True)
    finally:
        cleanup_observer()



def cleanup_observer():
    """Nettoyage propre de l'observer"""
    global observer
    if observer:
        try:
            watcher_logger.info("Arrêt de l'observer...")
            observer.stop()
            observer.join(timeout=5)
            if observer.is_alive():
                watcher_logger.warning("L'observer n'a pas pu s'arrêter proprement dans les temps")
            else:
                watcher_logger.info("Observer arrêté proprement")
        except Exception as e:
            watcher_logger.warning(f"Erreur lors de l'arrêt de l'observer : {e}")
        finally:
            observer = None


def stop_watcher():
    """Appelée par le service Windows pour arrêter proprement"""
    watcher_logger.info("Demande d'arrêt du watcher reçue")
    stop_flag.set()


def is_watcher_running():
    """Vérifie si le watcher est en cours d'exécution"""
    global observer
    return observer is not None and observer.is_alive() and not stop_flag.is_set()


if __name__ == '__main__':
    try:
        start_watcher()
    except KeyboardInterrupt:
        watcher_logger.info("Interruption clavier détectée")
    finally:
        cleanup_observer()
