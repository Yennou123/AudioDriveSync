[Setup]
AppName=AudioDriveSync
AppVersion=1.0
DefaultDirName={pf}\AudioDriveSync
DefaultGroupName=AudioDriveSync
OutputDir=dist\installer
OutputBaseFilename=AudioDriveSyncSetup
Compression=lzma
SolidCompression=yes
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=dialog
SetupIconFile=AudioDriveSync.ico

[Files]
; === Application principale (GUI + installe le service) ===
Source: "dist\setup.exe"; DestDir: "{app}"; Flags: ignoreversion

; === Icône ===
Source: "AudioDriveSync.ico"; DestDir: "{app}"; Flags: ignoreversion

; === Fichiers nécessaires pour Google Drive ===
Source: "credentials.json"; DestDir: "{commonappdata}\AudioDriveSync"; Flags: ignoreversion

[Dirs]
; Crée les répertoires pour le service
Name: "{commonappdata}\AudioDriveSync"
Name: "{commonappdata}\AudioDriveSync\logs"

[Icons]
Name: "{group}\AudioDriveSync"; Filename: "{app}\setup.exe"; IconFilename: "{app}\AudioDriveSync.ico"
Name: "{commondesktop}\AudioDriveSync"; Filename: "{app}\setup.exe"; Tasks: desktopicon; IconFilename: "{app}\AudioDriveSync.ico"

[Tasks]
Name: "desktopicon"; Description: "Créer une icône sur le bureau"; GroupDescription: "Icônes supplémentaires :"

[Run]
; Lance ton setup.exe (il installera et enregistrera le service)
Filename: "{app}\setup.exe"; Description: "Lancer AudioDriveSync"; Flags: nowait postinstall skipifsilent
