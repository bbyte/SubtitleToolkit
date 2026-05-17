; Inno Setup script for SubtitleToolkit Windows installer
; This creates a professional Windows installer package

#define MyAppName "SubtitleToolkit"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "SubtitleToolkit"
#define MyAppURL "https://github.com/subtitletoolkit/subtitletoolkit"
#define MyAppExeName "SubtitleToolkit.exe"
#define MyAppId "SubtitleToolkit"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{{#MyAppId}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DisableProgramGroupPage=yes
; Remove the following line to run in administrative install mode (install for all users)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=..\..\..\dist\installers
OutputBaseFilename=SubtitleToolkit-{#MyAppVersion}-Windows-Setup
SetupIconFile=..\..\..\app\resources\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
Source: "..\..\..\dist\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion
Source: "..\..\..\README.md"; DestDir: "{app}"; Flags: ignoreversion; DestName: "README.txt"
Source: "..\..\..\requirements.txt"; DestDir: "{app}"; Flags: ignoreversion
; Add any additional files here

[Registry]
; Register file associations
Root: HKCU; Subkey: "Software\Classes\.srt"; ValueType: string; ValueName: ""; ValueData: "SubtitleToolkit.srt"; Flags: uninsdeletevalue
Root: HKCU; Subkey: "Software\Classes\SubtitleToolkit.srt"; ValueType: string; ValueName: ""; ValueData: "SubRip Subtitle File"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\SubtitleToolkit.srt\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCU; Subkey: "Software\Classes\SubtitleToolkit.srt\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[UninstallDelete]
Type: filesandordirs; Name: "{userappdata}\{#MyAppName}"

[Code]
function IsAppRunning(): Boolean;
var
  FWMIService: Variant;
  FSWbemLocator: Variant;
  FWbemObjectSet: Variant;
begin
  Result := false;
  try
    FSWbemLocator := CreateOleObject('WBEMScripting.SWbemLocator');
    FWMIService := FSWbemLocator.ConnectServer('', 'root\CIMV2', '', '');
    FWbemObjectSet := FWMIService.ExecQuery('SELECT Name FROM Win32_Process WHERE Name="' + '{#MyAppExeName}' + '"');
    Result := (FWbemObjectSet.Count > 0);
  except
    Result := false;
  end;
end;

function InitializeSetup(): Boolean;
begin
  if IsAppRunning() then
  begin
    if MsgBox('SubtitleToolkit is currently running. Please close it before continuing the installation.', mbError, MB_OKCANCEL) = IDCANCEL then
    begin
      Result := False;
    end
    else
    begin
      Result := False;
    end;
  end
  else
  begin
    Result := True;
  end;
end;

function PrepareToInstall(var NeedsRestart: Boolean): String;
begin
  if IsAppRunning() then
  begin
    Result := 'SubtitleToolkit is still running. Please close it before continuing.';
  end
  else
  begin
    Result := '';
  end;
end;