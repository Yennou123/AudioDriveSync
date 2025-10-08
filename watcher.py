# watcher.py
import time
import os
import json
import threading
from watchdog.observers.polling import PollingObserver
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

# --- Variables globales ---
observer = None
stop_flag = threading.Event()


class AudioHandler(FileSystemEventHandler):
    def __init__(self, config):
        self.local_folder = config['local_folder']
        self.drive_folder = config['drive_folder']
        self.processing_files = set()

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
                time.sleep(2)
                if not os.path.exists(filepath):
                    watcher_logger.warning(f"Fichier supprimé pendant le traitement : {filepath}")
                    return
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
    """Démarre le watcher basé sur PollingObserver."""
    global observer
    try:
        watcher_logger.info("=== DÉMARRAGE WATCHER (PollingObserver) ===")

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
        observer = PollingObserver(timeout=3)  # 🟢 plus stable, moins sensible aux threads
        observer.schedule(event_handler, path=path, recursive=False)
        observer.start()

        watcher_logger.info(f"PollingObserver démarré — surveillance active sur : {path}")

        while not stop_flag.is_set():
            time.sleep(1)

        watcher_logger.info("Signal d'arrêt reçu, arrêt du watcher...")

    except Exception as e:
        watcher_logger.error(f"Erreur inattendue dans le watcher : {e}", exc_info=True)
    finally:
        cleanup_observer()


def cleanup_observer():
    """Arrête proprement le PollingObserver."""
    global observer
    if observer:
        try:
            watcher_logger.info("Arrêt du PollingObserver...")
            observer.stop()
            observer.join(timeout=5)
            if observer.is_alive():
                watcher_logger.warning("PollingObserver ne s'est pas arrêté proprement")
            else:
                watcher_logger.info("PollingObserver arrêté correctement")
        except Exception as e:
            watcher_logger.warning(f"Erreur lors de l'arrêt du PollingObserver : {e}")
        finally:
            observer = None


def stop_watcher():
    """Demande d'arrêt propre du watcher."""
    watcher_logger.info("Demande d'arrêt reçue pour le watcher")
    stop_flag.set()


def is_watcher_running():
    """Retourne True si le watcher est actif."""
    global observer
    return observer is not None and observer.is_alive() and not stop_flag.is_set()


if __name__ == '__main__':
    try:
        start_watcher()
    except KeyboardInterrupt:
        watcher_logger.info("Interruption clavier détectée")
    finally:
        cleanup_observer()

