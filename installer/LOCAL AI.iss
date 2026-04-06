#define AppName "Local AI(UI)"
#define AppExeName "LOCAL AI.exe"
#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif
#define AppPublisher "Ashmith Babu P S"
#define AppURL "https://github.com/ashser004"

[Setup]
AppId=LocalAIUI
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={localappdata}\Programs\Local AI(UI)
DefaultGroupName=Local AI(UI)
DisableProgramGroupPage=yes
AllowNoIcons=yes
UninstallDisplayIcon={app}\{#AppExeName}
OutputDir=..\build\installer
OutputBaseFilename=LOCAL AI Setup
SetupIconFile=..\build\installer\LOCAL AI.ico
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64
LicenseFile=..\LICENSE
VersionInfoVersion={#AppVersion}.0
VersionInfoTextVersion={#AppVersion}

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\LOCAL AI.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\LOCAL AI"; Filename: "{app}\{#AppExeName}"
Name: "{group}\Uninstall LOCAL AI"; Filename: "{uninstallexe}"
Name: "{commondesktop}\LOCAL AI"; Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Launch LOCAL AI"; Flags: nowait postinstall skipifsilent