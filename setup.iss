; Inno Setup script for DeletedViewer
; 1. Установи Inno Setup 6: https://jrsoftware.org/isinfo.php
; 2. Открой этот файл в Inno Setup и нажми Build -> Compile
; 3. Получишь Setup_TrashSpy.exe в папке Output

#define MyAppName "TrashSpy"
#define MyAppVersion "1.0"
#define MyAppPublisher "TrashSpy"

[Setup]
AppId={{A1B2C3D4-0000-4000-8000-000000000001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=Setup_TrashSpy
SetupIconFile=icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"
Name: "ukrainian"; MessagesFile: "compiler:Languages\\Ukrainian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать значок на рабочем столе"; GroupDescription: "Дополнительно:"

[Files]
Source: "dist\\TrashSpy.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\TrashSpy.exe"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\TrashSpy.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\TrashSpy.exe"; Description: "Запустить программу"; Flags: nowait postinstall skipifsilent
