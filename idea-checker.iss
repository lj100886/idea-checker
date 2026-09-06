; idea-checker 安装脚本（集成随缘打赏页）
; 用 Inno Setup 6 编译：ISCC.exe idea-checker.iss

#define MyAppName "idea-checker"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "三修先生"
#define MyAppURL "https://github.com/lj100886/idea-checker"

[Setup]
AppId={{B7A4F3E2-1A2B-4C3D-9E5F-6A7B8C9D0E1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\idea-checker
DefaultGroupName=idea-checker
DisableProgramGroupPage=yes
OutputDir=dist_installer
OutputBaseFilename=idea-checker_setup_v{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
DisableFinishedPage=yes
UninstallDisplayIcon={app}\idea-checker.exe

[Languages]
Name: "chinesesimp"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"; Flags: unchecked

[Files]
; 主程序
Source: "dist\idea-checker.exe"; DestDir: "{app}"; Flags: ignoreversion
; 打赏收款码（只临时释放，不装进程序目录）
Source: "assets\donation\wx.bmp"; Flags: dontcopy nocompression
Source: "assets\donation\zfb.bmp"; Flags: dontcopy nocompression

[Icons]
Name: "{group}\idea-checker"; Filename: "{app}\idea-checker.exe"; Parameters: "--pet"
Name: "{group}\卸载 idea-checker"; Filename: "{uninstallexe}"
Name: "{autodesktop}\idea-checker"; Filename: "{app}\idea-checker.exe"; Parameters: "--pet"; Tasks: desktopicon

[Run]
Filename: "{app}\idea-checker.exe"; Parameters: "--pet"; Description: "立即启动 idea-checker 桌面宠物"; Flags: nowait postinstall skipifsilent

[Code]
// 引入随缘打赏页模块
#include "assets\donation\donate_page.iss"

procedure InitializeWizard;
begin
  DonateInit;
end;

function ShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := DonateShouldSkipPage(PageID);
end;

procedure CurPageChanged(CurPageID: Integer);
begin
  DonateOnPageChanged(CurPageID);
end;