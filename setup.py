# setup.py
import subprocess
import sys
import os
import ctypes
import time
from gui_config import launch_config_interface
from drive_auth import authenticate_drive
from logger_utils import setup_logger

SERVICE_NAME = "AudioDriveSyncService"

setup_logger = setup_logger("setup", "setup.log")
setup_logger.info("=== Setup logger initialisé ===")

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        setup_logger.info("Relance avec les privilèges administrateur...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, " ".join(sys.argv), None, 1)
        sys.exit(0)
    return True

def install_windows_service():
    """Création du service Windows en pointant sur l’exécutable du service"""
    try:
        setup_logger.info("Installation du service Windows...")
        base_dir = os.path.dirname(os.path.abspath(sys.executable))
        service_exe = os.path.join(base_dir, "AudioDriveSyncService.exe")
        if not os.path.exists(service_exe):
            setup_logger.error(f"Impossible de trouver {service_exe}")
            return False

        subprocess.run(f'sc delete {SERVICE_NAME}', shell=True, capture_output=True, text=True)
        subprocess.run(
            f'sc create {SERVICE_NAME} binPath= "{service_exe}" start= auto DisplayName= "{SERVICE_NAME}"',
            shell=True, check=True
        )
        time.sleep(5)
        subprocess.run(f'sc start {SERVICE_NAME}', shell=True, check=True)
        setup_logger.info("Service installé et démarré avec succès")
        return True
    except subprocess.CalledProcessError as e:
        setup_logger.error(f"Erreur lors de l'installation du service : {e.stderr.decode() if e.stderr else e}")
        return False

def main():
    setup_logger.info("=== Début de l'installation AudioDriveSync ===")
    if not is_admin():
        setup_logger.info("Privilèges administrateur requis")
        run_as_admin()

    if not launch_config_interface():
        setup_logger.error("Configuration annulée")
        return False

    try:
        authenticate_drive()
        setup_logger.info("Authentification Google Drive réussie")
    except Exception as e:
        setup_logger.error(f"Échec authentification : {e}")
        return False

    if not install_windows_service():
        setup_logger.error("Échec installation service")
        return False

    print("\n[✓] Installation terminée avec succès !")
    print("[✓] Le service démarre automatiquement avec Windows")
    return True

if __name__ == "__main__":
    try:
        success = main()
        if not success:
            input("\n[ERREUR] Échec installation. Voir setup.log. Appuyez sur Entrée...")
            sys.exit(1)
        else:
            input("\n[SUCCÈS] AudioDriveSync installé ! Appuyez sur Entrée pour fermer...")
    except KeyboardInterrupt:
        print("\nInstallation annulée")
        sys.exit(0)
