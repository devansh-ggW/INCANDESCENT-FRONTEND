#define AppName "INCANDESCENT"
#define AppVersion "0.1.0"
#define AppPublisher "INCANDESCENT"

[Setup]
AppId={{9D75B71B-C59E-4A46-A1D4-76FB814B0A51}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher={#AppPublisher}
AppComments=Local AI desktop application
DefaultDirName={localappdata}\Programs\INCANDESCENT
DefaultGroupName=INCANDESCENT
UninstallDisplayIcon={app}\INCANDESCENT.exe
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
MinVersion=10.0
OutputDir=..\dist\installer
OutputBaseFilename=INCANDESCENT-Setup
SetupIconFile=..\incandescent.ico
WizardStyle=modern
Compression=lzma2
SolidCompression=yes
CloseApplications=yes
RestartIfNeededByRun=no
Uninstallable=yes
SetupLogging=yes

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Files]
Source: "..\dist\INCANDESCENT.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\INCANDESCENT"; Filename: "{app}\INCANDESCENT.exe"
Name: "{autodesktop}\INCANDESCENT"; Filename: "{app}\INCANDESCENT.exe"; Tasks: desktopicon
Name: "{autoprograms}\Prepare INCANDESCENT Model"; Filename: "{app}\INCANDESCENT.exe"; Parameters: "--setup-model"

[Run]
Filename: "{app}\INCANDESCENT.exe"; Parameters: "--setup-model"; StatusMsg: "Checking Ollama and preparing Qwen 3.5 2B..."; Flags: waituntilterminated skipifsilent
Filename: "{app}\INCANDESCENT.exe"; Description: "Launch INCANDESCENT"; Flags: postinstall nowait skipifsilent

[Code]
function InitializeSetup(): Boolean;
begin
  Result := True;
  if not IsWin64 then
  begin
    MsgBox(
      'This INCANDESCENT local-AI release requires 64-bit Windows. ' +
      'A 32-bit Windows build is not offered because the supported Ollama runtime is not available for x86 in this release.',
      mbError, MB_OK);
    Result := False;
    Exit;
  end;

  if (GetWindowsVersion shr 24) < 10 then
  begin
    MsgBox(
      'This release requires Windows 10 or newer. Windows 7, 8, and 8.1 are not supported by this installer.',
      mbError, MB_OK);
    Result := False;
  end;
end;
