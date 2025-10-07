# gui_config.py
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import json
import os
import subprocess
import shutil
from drive_auth import authenticate_drive
from logger_utils import setup_logger
from paths import get_config_file, get_base_dir

gui_logger = setup_logger("gui", "gui.log")
gui_logger.info("=== GUI logger initialisé ===")

CONFIG_DIR = get_base_dir()
os.makedirs(CONFIG_DIR, exist_ok=True)
CONFIG_FILE = get_config_file()


def validate_folder_path(path):
    """Valide qu'un chemin de dossier existe et est accessible"""
    if not path:
        return False, "Le chemin ne peut pas être vide"
    if not os.path.exists(path):
        return False, "Le dossier n'existe pas"
    if not os.path.isdir(path):
        return False, "Le chemin ne correspond pas à un dossier"
    if not os.access(path, os.R_OK | os.W_OK):
        return False, "Pas d'accès en lecture/écriture au dossier"
    return True, "OK"


def uninstall_service():
    confirm = messagebox.askyesno(
        "Confirmation",
        "Voulez-vous vraiment désinstaller le service ?\n"
        "Cette action arrêtera la synchronisation automatique."
    )
    if not confirm:
        return
    try:
        gui_logger.info("Début de la désinstallation du service")

        # Arrêter le service
        try:
            subprocess.run(['python', 'install_service.py', 'stop'], check=True, capture_output=True, timeout=30)
            gui_logger.info("Service arrêté avec succès")
        except subprocess.TimeoutExpired:
            gui_logger.warning("Timeout lors de l'arrêt du service")
        except subprocess.CalledProcessError as e:
            gui_logger.warning(f"Erreur lors de l'arrêt du service : {e}")

        # Supprimer le service
        try:
            subprocess.run(['python', 'install_service.py', 'remove'], check=True, capture_output=True, timeout=30)
            gui_logger.info("Service supprimé avec succès")
        except subprocess.TimeoutExpired:
            gui_logger.warning("Timeout lors de la suppression du service")
        except subprocess.CalledProcessError as e:
            gui_logger.warning(f"Erreur lors de la suppression du service : {e}")

        # Supprimer les fichiers de configuration
        if os.path.exists(CONFIG_DIR):
            shutil.rmtree(CONFIG_DIR)
            gui_logger.info("Dossier de configuration supprimé")

        messagebox.showinfo("Désinstallation", "Le service a été désinstallé avec succès.\n"
                            "L'application va se fermer.")
        gui_logger.info("Désinstallation terminée avec succès")
        os._exit(0)
    except Exception as e:
        gui_logger.error(f"Erreur lors de la désinstallation : {e}")
        messagebox.showerror("Erreur", f"Erreur lors de la désinstallation : {e}")


def save_config(local_folder, drive_folder):
    try:
        # Validation des chemins
        local_valid, local_msg = validate_folder_path(local_folder)
        if not local_valid:
            messagebox.showerror("Erreur", f"Dossier local invalide : {local_msg}")
            return False

        if not drive_folder.strip():
            messagebox.showerror("Erreur", "Le dossier Google Drive ne peut pas être vide")
            return False

        config = {
            'local_folder': local_folder,
            'drive_folder': drive_folder
        }

        path = get_config_file()
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2)

        gui_logger.info("Configuration sauvegardée avec succès")
        messagebox.showinfo("Succès", "Configuration enregistrée avec succès.")
        return True
    except Exception as e:
        gui_logger.error(f"Erreur lors de la sauvegarde de la configuration : {e}")
        messagebox.showerror("Erreur", f"Erreur lors de la sauvegarde : {e}")
        return False


def load_config():
    try:
        if os.path.exists(CONFIG_FILE):
            with open(CONFIG_FILE, 'r') as f:
                config = json.load(f)
            gui_logger.info("Configuration chargée avec succès")
            return config
    except (json.JSONDecodeError, IOError) as e:
        gui_logger.error(f"Erreur lors du chargement de la configuration : {e}")
    return {'local_folder': '', 'drive_folder': ''}


def launch_config_interface():
    config = load_config()
    root = tk.Tk()
    root.title("AudioDriveSync - Configuration")
    root.geometry("600x400")
    root.resizable(False, False)

    # Style moderne
    style = ttk.Style()
    style.theme_use('clam')

    # Frame principal
    main_frame = ttk.Frame(root, padding="20")
    main_frame.pack(fill=tk.BOTH, expand=True)

    # Titre
    title_label = ttk.Label(main_frame, text="Configuration AudioDriveSync", font=('Arial', 16, 'bold'))
    title_label.pack(pady=(0, 20))

    result = {'cancelled': True}

    # Répertoire local
    local_frame = ttk.LabelFrame(main_frame, text="Dossier local à surveiller", padding="10")
    local_frame.pack(fill=tk.X, pady=(0, 15))

    local_entry = ttk.Entry(local_frame, width=60)
    local_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    local_entry.insert(0, config.get('local_folder', ''))

    def browse_local():
        folder = filedialog.askdirectory(title="Sélectionner le dossier à surveiller")
        if folder:
            local_entry.delete(0, tk.END)
            local_entry.insert(0, folder)

    ttk.Button(local_frame, text="Parcourir", command=browse_local).pack(side=tk.RIGHT)

    # Dossier Drive
    drive_frame = ttk.LabelFrame(main_frame, text="Dossier Google Drive", padding="10")
    drive_frame.pack(fill=tk.X, pady=(0, 15))

    drive_entry = ttk.Entry(drive_frame, width=60)
    drive_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
    drive_entry.insert(0, config.get('drive_folder', ''))

    def browse_drive():
        # Pour l'instant, on ne peut pas parcourir Drive directement
        messagebox.showinfo("Info", "Entrez le nom du dossier ou collez un lien Google Drive")

    ttk.Button(drive_frame, text="Aide", command=browse_drive).pack(side=tk.RIGHT)

    # Boutons d'action
    button_frame = ttk.Frame(main_frame)
    button_frame.pack(fill=tk.X, pady=(20, 0))

    # Connexion Google Drive
    def connect_drive():
        try:
            gui_logger.info("Test de connexion Google Drive...")
            service = authenticate_drive()
            messagebox.showinfo("Succès", "Connexion Google Drive réussie.")
            gui_logger.info("Connexion Google Drive réussie")
        except Exception as e:
            gui_logger.error(f"Erreur de connexion Google Drive : {e}")
            messagebox.showerror("Erreur", f"Erreur de connexion : {e}")

    ttk.Button(button_frame, text="Tester la connexion Google Drive", command=connect_drive).pack(side=tk.LEFT, padx=(0, 10))

    # Sauvegarder la configuration
    def save_all():
        local_folder = local_entry.get().strip()
        drive_folder = drive_entry.get().strip()

        if not local_folder or not drive_folder:
            messagebox.showerror("Erreur", "Veuillez remplir les deux champs.")
            return

        if save_config(local_folder, drive_folder):
            result['cancelled'] = False
            root.destroy()

    ttk.Button(button_frame, text="Sauvegarder", command=save_all).pack(side=tk.RIGHT)

    # Bouton de désinstallation
    ttk.Button(main_frame, text="Désinstaller le service", command=uninstall_service, style='Danger.TButton').pack(pady=(20, 0))

    # Style pour le bouton de danger
    style.configure('Danger.TButton', foreground='red')

    root.mainloop()
    return not result['cancelled']


if __name__ == "__main__":
    launch_config_interface()
