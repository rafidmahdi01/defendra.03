; ==============================================================================
; Defendra.AI - Commercial-Grade Enterprise EDR Distribution Package
; Inno Setup Compiler Script
; ==============================================================================

#define MyAppName "Defendra.AI Agent"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Defendra.AI"
#define MyAppURL "https://defendra.ai"
#define MyAppExeName "DefendraAgent.exe"
#define MyServiceName "DefendraAgent"
#define MyServiceDisplayName "Defendra.AI Endpoint Protection Agent"
#define MyServiceDescription "Defendra.AI Next-Gen Autonomous Endpoint Detection and Response (EDR) Service."

[Setup]
AppId={{8B84B29E-34FE-485D-A08D-74A82FDF5D1A}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}/support
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\Defendra
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=.
OutputBaseFilename=DefendraAgentSetup
SetupIconFile={#SourcePath}\defendra_logo.ico
UninstallDisplayIcon={app}\defendra_logo.ico
UninstallDisplayName={#MyServiceDisplayName}
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
PrivilegesRequiredOverridesAllowed=commandline
ArchitecturesInstallIn64BitMode=x64compatible
CloseApplications=no
RestartApplications=no
AlwaysRestart=no
MinVersion=6.1sp1

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"
Name: "startupicon"; Description: "Launch Defendra.AI automatically on Windows startup"; GroupDescription: "Startup Settings:"

[Dirs]
Name: "{app}"; Permissions: system-full admins-full users-readexec
Name: "{app}\logs"; Permissions: system-full admins-full users-full
Name: "{app}\quarantine"; Permissions: system-full admins-full users-full
Name: "{commonappdata}\Defendra"; Permissions: system-full admins-full users-full
Name: "{commonappdata}\Defendra\logs"; Permissions: system-full admins-full users-full
Name: "{commonappdata}\Defendra\quarantine"; Permissions: system-full admins-full users-full

[Files]
Source: "{#SourcePath}\DefendraAgent.exe"; DestDir: "{app}"; Flags: ignoreversion restartreplace uninsrestartdelete
Source: "{#SourcePath}\defendra_logo.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\defendra_logo.ico"; Comment: "{#MyServiceDescription}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\defendra_logo.ico"; Tasks: desktopicon; Comment: "{#MyServiceDescription}"
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; IconFilename: "{app}\defendra_logo.ico"; Tasks: startupicon; Comment: "{#MyServiceDescription}"

[Run]
Filename: "{app}\{#MyAppExeName}"; WorkingDir: "{app}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent

[Code]
var
  TokenPage: TInputQueryWizardPage;
  EnrollmentToken: string;
  BackendUrl: string;

function GetCmdParam(ParamName: string; DefaultValue: string): string;
var
  i: Integer;
  Param, PrefixEq1, PrefixEq2, PrefixCol1, PrefixCol2: string;
begin
  Result := DefaultValue;
  PrefixEq1 := '/' + UpperCase(ParamName) + '=';
  PrefixEq2 := '-' + UpperCase(ParamName) + '=';
  PrefixCol1 := '/' + UpperCase(ParamName) + ':';
  PrefixCol2 := '-' + UpperCase(ParamName) + ':';

  for i := 1 to ParamCount do
  begin
    Param := ParamStr(i);
    if (Pos(PrefixEq1, UpperCase(Param)) = 1) then
    begin
      Result := Copy(Param, Length(PrefixEq1) + 1, Length(Param) - Length(PrefixEq1));
      if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
        Result := Copy(Result, 2, Length(Result) - 2);
      Exit;
    end
    else if (Pos(PrefixEq2, UpperCase(Param)) = 1) then
    begin
      Result := Copy(Param, Length(PrefixEq2) + 1, Length(Param) - Length(PrefixEq2));
      if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
        Result := Copy(Result, 2, Length(Result) - 2);
      Exit;
    end
    else if (Pos(PrefixCol1, UpperCase(Param)) = 1) then
    begin
      Result := Copy(Param, Length(PrefixCol1) + 1, Length(Param) - Length(PrefixCol1));
      if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
        Result := Copy(Result, 2, Length(Result) - 2);
      Exit;
    end
    else if (Pos(PrefixCol2, UpperCase(Param)) = 1) then
    begin
      Result := Copy(Param, Length(PrefixCol2) + 1, Length(Param) - Length(PrefixCol2));
      if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
        Result := Copy(Result, 2, Length(Result) - 2);
      Exit;
    end;
  end;
  
  Param := ExpandConstant('{param:' + ParamName + '}');
  if (Param <> '') then
  begin
    Result := Param;
    if (Length(Result) >= 2) and (Result[1] = '"') and (Result[Length(Result)] = '"') then
      Result := Copy(Result, 2, Length(Result) - 2);
  end;
end;

procedure WriteConfigurationFiles(TargetToken: string; TargetBackend: string);
var
  JsonContent, EnvContent, JsonFileApp, JsonFileData, JsonFileUser, EnvFileApp, EnvFileData, EnvFileUser, Timestamp: string;
begin
  Timestamp := GetDateTimeString('yyyy-mm-dd hh:nn:ss', #0, #0);
  
  StringChangeEx(TargetToken, '\', '\\', True);
  StringChangeEx(TargetBackend, '\', '\\', True);

  JsonContent := 
    '{' + #13#10 +
    '  "agent_token": "' + TargetToken + '",' + #13#10 +
    '  "backend_url": "' + TargetBackend + '",' + #13#10 +
    '  "installed_at": "' + Timestamp + '",' + #13#10 +
    '  "version": "' + '{#MyAppVersion}' + '"' + #13#10 +
    '}';

  EnvContent :=
    'MARIA_API_URL=' + TargetBackend + #13#10 +
    'MARIA_API_TOKEN=' + TargetToken + #13#10 +
    'BACKEND_URL=' + TargetBackend + #13#10 +
    'ENROLLMENT_TOKEN=' + TargetToken + #13#10;

  JsonFileApp := ExpandConstant('{app}\config.json');
  JsonFileData := ExpandConstant('{commonappdata}\Defendra\config.json');
  JsonFileUser := ExpandConstant('{userappdata}\Defendra\config.json');
  EnvFileApp := ExpandConstant('{app}\.env');
  EnvFileData := ExpandConstant('{commonappdata}\Defendra\.env');
  EnvFileUser := ExpandConstant('{userappdata}\Defendra\.env');

  SaveStringToFile(JsonFileApp, JsonContent, False);
  SaveStringToFile(JsonFileData, JsonContent, False);
  SaveStringToFile(JsonFileUser, JsonContent, False);
  SaveStringToFile(EnvFileApp, EnvContent, False);
  SaveStringToFile(EnvFileData, EnvContent, False);
  SaveStringToFile(EnvFileUser, EnvContent, False);
end;

procedure ApplyAntiTamperSecurity();
var
  ResultCode: Integer;
  AppDir, DataDir: string;
begin
  AppDir := ExpandConstant('{app}');
  DataDir := ExpandConstant('{commonappdata}\Defendra');

  Exec('icacls.exe', '"' + AppDir + '" /grant "BUILTIN\Users":(OI)(CI)RX', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('icacls.exe', '"' + AppDir + '\logs" /grant "BUILTIN\Users":(OI)(CI)M', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('icacls.exe', '"' + AppDir + '\quarantine" /grant "BUILTIN\Users":(OI)(CI)M', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('icacls.exe', '"' + DataDir + '" /grant "BUILTIN\Users":(OI)(CI)M', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('icacls.exe', '"' + AppDir + '\config.json" /grant "BUILTIN\Users":R', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('icacls.exe', '"' + DataDir + '\config.json" /grant "BUILTIN\Users":R', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
end;

procedure ConfigureAgentStartup();
var
  ResultCode: Integer;
  ExePath: string;
begin
  ExePath := ExpandConstant('{app}\{#MyAppExeName}');

  Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Sleep(500);

  Exec('sc.exe', 'stop {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('sc.exe', 'delete {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  Exec('schtasks.exe', '/Delete /TN "DefendraAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

  if WizardIsTaskSelected('startupicon') then
  begin
    RegWriteStringValue(HKEY_LOCAL_MACHINE, 'Software\Microsoft\Windows\CurrentVersion\Run', '{#MyAppName}', '"' + ExePath + '"');
  end;
end;

procedure InitializeWizard();
begin
  EnrollmentToken := GetCmdParam('ENROLLMENT_TOKEN', '');
  BackendUrl := GetCmdParam('BACKEND_URL', 'https://api.defendra.ai');

  TokenPage := CreateInputQueryPage(
    wpSelectDir,
    'Defendra.AI Enterprise Enrollment',
    'Specify backend connection parameters for this endpoint.',
    'Enter the Defendra.AI Enrollment Token and Backend URL provided by your security administrator:'
  );
  
  TokenPage.Add('Enrollment Token:', False);
  TokenPage.Add('Backend URL:', False);

  TokenPage.Values[0] := EnrollmentToken;
  TokenPage.Values[1] := BackendUrl;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  FinalToken: string;
  FinalBackend: string;
begin
  if CurStep = ssPostInstall then
  begin
    if WizardSilent then
    begin
      FinalToken := GetCmdParam('ENROLLMENT_TOKEN', '');
      FinalBackend := GetCmdParam('BACKEND_URL', 'https://api.defendra.ai');
    end
    else
    begin
      FinalToken := TokenPage.Values[0];
      FinalBackend := TokenPage.Values[1];
      if FinalToken = '' then
        FinalToken := GetCmdParam('ENROLLMENT_TOKEN', '');
      if FinalBackend = '' then
        FinalBackend := GetCmdParam('BACKEND_URL', 'https://api.defendra.ai');
    end;

    WriteConfigurationFiles(FinalToken, FinalBackend);
    ApplyAntiTamperSecurity();
    ConfigureAgentStartup();
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  ResultCode: Integer;
begin
  if CurUninstallStep = usUninstall then
  begin
    Exec('taskkill.exe', '/F /IM {#MyAppExeName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Sleep(1000);

    RegDeleteValue(HKEY_LOCAL_MACHINE, 'Software\Microsoft\Windows\CurrentVersion\Run', '{#MyAppName}');

    Exec('sc.exe', 'stop {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('sc.exe', 'delete {#MyServiceName}', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
    Exec('schtasks.exe', '/Delete /TN "DefendraAgent" /F', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);

    DelTree(ExpandConstant('{commonappdata}\Defendra'), True, True, True);
  end;
end;
