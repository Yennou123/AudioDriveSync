# service_core.py
import os
import json
import sys
import win32serviceutil
import win32service
import win32event
import servicemanager
import time
import threading
from logger_utils import setup_logger
from paths import get_config_file

# --- Initialisation logging robuste ---
service_logger = setup_logger("service", "service.log")
SERVICE_NAME = "AudioDriveSyncService"


class AudioDriveSyncService(win32serviceutil.ServiceFramework):
    _svc_name_ = SERVICE_NAME
    _svc_display_name_ = "Audio Drive Sync Service"
    _svc_description_ = "Surveille un dossier local et synchronise automatiquement les fichiers audio vers Google Drive."

    def __init__(self, args):
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker_thread = None
        self._stopping = False
        service_logger.info("Service initialisé")

    def SvcStop(self):
        service_logger.info("Arrêt demandé pour AudioDriveSync")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        self._stopping = True

        try:
            from watcher import stop_watcher, cleanup_observer
            stop_watcher()
            cleanup_observer()
            service_logger.info("Watcher arrêté proprement")
        except Exception as e:
            service_logger.warning(f"Erreur lors de l'arrêt du watcher : {e}")

        win32event.SetEvent(self.stop_event)

        if self.worker_thread and self.worker_thread.is_alive():
            service_logger.info("Attente de l’arrêt du thread principal...")
            self.worker_thread.join(timeout=10)

        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )
        service_logger.info("Service AudioDriveSync arrêté proprement")

    def SvcDoRun(self):
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            service_logger.info("Service en phase de démarrage...")

            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            service_logger.info("Service AudioDriveSync en cours d’exécution")

            self.worker_thread = threading.Thread(target=self.main, daemon=True)
            self.worker_thread.start()

            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            service_logger.info("Signal d’arrêt reçu (SvcDoRun)")

        except Exception as e:
            service_logger.error(f"Erreur critique dans SvcDoRun : {e}", exc_info=True)
            try:
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            except:
                pass

    def check_config(self):
        """Vérifie la validité de la configuration JSON."""
        config_file = get_config_file()
        service_logger.debug(f"Vérification config : {config_file}")

        if not os.path.exists(config_file):
            service_logger.error("Fichier de configuration introuvable.")
            return None

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            local_folder = config.get('local_folder')
            drive_folder = config.get('drive_folder')

            if not local_folder or not drive_folder:
                service_logger.error("Champs manquants dans la configuration.")
                return None

            if not os.path.exists(local_folder):
                service_logger.error(f"Dossier local inexistant : {local_folder}")
                return None

            return config

        except Exception as e:
            service_logger.error(f"Erreur lecture config : {e}", exc_info=True)
            return None

    def main(self):
        """Boucle principale du service."""
        service_logger.info("=== DÉBUT MAIN ===")

        while not self._stopping:
            config = self.check_config()
            if not config:
                service_logger.warning("Configuration invalide — nouvel essai dans 30s.")
                time.sleep(30)
                continue

            try:
                from watcher import start_watcher, cleanup_observer, stop_flag
                service_logger.info("Démarrage du watcher principal...")
                stop_flag.clear()
                start_watcher()  # bloque tant que stop_flag n’est pas défini
            except Exception as e:
                service_logger.error(f"Erreur dans le watcher : {e}", exc_info=True)
                cleanup_observer()
                time.sleep(10)
                continue

            # Attente avant un éventuel redémarrage
            time.sleep(2)

        service_logger.info("=== FIN MAIN ===")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AudioDriveSyncService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        if 'debug' in sys.argv:
            service_logger.info("Mode DEBUG activé")
            s = AudioDriveSyncService([])
            try:
                s.SvcDoRun()
            except KeyboardInterrupt:
                service_logger.info("Interruption clavier (Ctrl+C)")
                s.SvcStop()
        else:
            win32serviceutil.HandleCommandLine(AudioDriveSyncService)
