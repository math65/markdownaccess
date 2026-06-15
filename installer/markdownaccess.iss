; Installeur Inno Setup pour MarkdownAccess.
;
; Compiler :  ISCC.exe installer\markdownaccess.iss
; Pré-requis : avoir lancé  uv run pyinstaller markdownaccess.spec  (dossier
;              dist\MarkdownAccess\).
; Sortie :     dist\MarkdownAccess-Setup.exe  (= asset à publier sur GitHub).
;
; Lancé en /SILENT par l'auto-updateur : Inno affiche SA fenêtre de progression
; sans assistant à cliquer, puis la section [Run] relance l'app.

#define AppName "MarkdownAccess"
#define AppVersion "0.1.0"          ; garder synchro avec app/version.py
#define AppPublisher "math65"
#define AppExe "MarkdownAccess.exe"

[Setup]
; AppId FIXE : identifie l'app pour les mises à jour (ne jamais changer).
AppId={{D1F71A6B-BE50-45E1-BC44-F13112EE18CA}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
; Install par-utilisateur : pas d'UAC → silencieux possible sans admin.
PrivilegesRequired=lowest
DefaultDirName={localappdata}\{#AppName}
DisableProgramGroupPage=yes
OutputDir=..\dist
OutputBaseFilename=MarkdownAccess-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
SetupLogging=yes

[Languages]
Name: "french"; MessagesFile: "compiler:Languages\French.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; Flags: unchecked

[Files]
Source: "..\dist\MarkdownAccess\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Run]
; Relance l'app après l'install. PAS de skipifsilent : indispensable pour que le
; redémarrage marche aussi lors d'une mise à jour silencieuse (/SILENT).
Filename: "{app}\{#AppExe}"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall
