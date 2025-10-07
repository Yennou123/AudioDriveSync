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
        service_logger.info("Initialisation du service...")
        win32serviceutil.ServiceFramework.__init__(self, args)
        self.stop_event = win32event.CreateEvent(None, 0, 0, None)
        self.worker_thread = None
        service_logger.info("Service initialisé avec succès")

    def SvcStop(self):
        service_logger.info("Arrêt demandé pour AudioDriveSync")
        self.ReportServiceStatus(win32service.SERVICE_STOP_PENDING)
        try:
            from watcher import stop_watcher
            stop_watcher()
            service_logger.info("Watcher arrêté")
        except ImportError as e:
            service_logger.error(f"Impossible d'importer watcher pour l'arrêt : {e}")
        except Exception as e:
            service_logger.warning(f"Impossible d'arrêter le watcher : {e}")

        # Déclenche l’event d’arrêt
        win32event.SetEvent(self.stop_event)

        # Attendre que le thread finisse
        if self.worker_thread and self.worker_thread.is_alive():
            service_logger.info("Attente de l’arrêt du thread principal...")
            self.worker_thread.join(timeout=10)

        # Log dans l’event viewer Windows
        servicemanager.LogMsg(
            servicemanager.EVENTLOG_INFORMATION_TYPE,
            servicemanager.PYS_SERVICE_STOPPED,
            (self._svc_name_, '')
        )
        service_logger.info("Event d'arrêt signalé → Service arrêté proprement")

    def SvcDoRun(self):
        try:
            self.ReportServiceStatus(win32service.SERVICE_START_PENDING)
            service_logger.info("Statut START_PENDING signalé")

            # Signaler RUNNING immédiatement pour éviter l'erreur 1053
            self.ReportServiceStatus(win32service.SERVICE_RUNNING)
            service_logger.info("Statut RUNNING signalé à Windows")

            servicemanager.LogMsg(
                servicemanager.EVENTLOG_INFORMATION_TYPE,
                servicemanager.PYS_SERVICE_STARTED,
                (self._svc_name_, '')
            )
            service_logger.info("Message événement Windows envoyé")

            # Lancer la logique dans un thread séparé
            self.worker_thread = threading.Thread(target=self.main, daemon=True)
            self.worker_thread.start()

            # Boucle d’attente du stop_event
            win32event.WaitForSingleObject(self.stop_event, win32event.INFINITE)
            service_logger.info("Stop event reçu → sortie de SvcDoRun")

        except Exception as e:
            service_logger.error(f"Erreur critique dans SvcDoRun : {e}", exc_info=True)
            try:
                self.ReportServiceStatus(win32service.SERVICE_STOPPED)
            except:
                pass

    def check_config(self):
        config_file = get_config_file()
        service_logger.info(f"Vérification de la config : {config_file}")

        if not os.path.exists(config_file):
            service_logger.error("Config manquante")
            return False

        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)

            if not config.get('local_folder') or not config.get('drive_folder'):
                service_logger.error("Config invalide : champs manquants")
                return False

            if not os.path.exists(config['local_folder']):
                service_logger.error(f"Dossier local introuvable : {config['local_folder']}")
                return False

            service_logger.info(f"Config OK - Local: {config['local_folder']} | Drive: {config['drive_folder']}")
            return True
        except Exception as e:
            service_logger.error(f"Erreur lecture config : {e}", exc_info=True)
            return False

    def main(self):
        service_logger.info("=== DÉBUT MAIN ===")
        try:
            while True:
                # Vérifier si un arrêt est demandé
                if win32event.WaitForSingleObject(self.stop_event, 0) == win32event.WAIT_OBJECT_0:
                    service_logger.info("Stop event détecté dans main() → sortie")
                    break

                if not self.check_config():
                    service_logger.warning("Config invalide → nouvel essai dans 30s")
                    time.sleep(30)
                    continue

                try:
                    service_logger.info("Démarrage du watcher...")
                    from watcher import start_watcher
                    start_watcher()  # bloque tant que stop_watcher() n’est pas appelé
                except ImportError as e:
                    service_logger.error(f"Erreur import watcher : {e}")
                    time.sleep(30)
                    continue
                except Exception as e:
                    service_logger.error(f"Watcher crashé : {e}", exc_info=True)
                    time.sleep(10)
                    continue

        except Exception as e:
            service_logger.error(f"Erreur dans main : {e}", exc_info=True)

        service_logger.info("=== FIN MAIN ===")


if __name__ == '__main__':
    if len(sys.argv) == 1:
        # Mode service normal
        service_logger.info("Démarrage en mode service")
        servicemanager.Initialize()
        servicemanager.PrepareToHostSingle(AudioDriveSyncService)
        servicemanager.StartServiceCtrlDispatcher()
    else:
        if 'debug' in sys.argv:
            service_logger.info("Mode DEBUG activé")
            service = AudioDriveSyncService([])
            try:
                service.SvcDoRun()
            except KeyboardInterrupt:
                service_logger.info("Interruption clavier (Ctrl+C)")
                service.SvcStop()
        else:
            win32serviceutil.HandleCommandLine(AudioDriveSyncService)
