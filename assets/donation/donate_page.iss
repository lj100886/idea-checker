// ============================================================================
// 随缘打赏页 · 可复用 Inno Setup 模块（donate_page.iss）
// ----------------------------------------------------------------------------
// 说明：本文件是 Inno Setup 的 [Code] 段片段（不含段头），通过 #include 嵌入
//       宿主安装脚本。功能：在安装流程末尾插入一页“随缘打赏”（微信+支付宝
//       双收款码、自适应缩放、每台电脑只出现一次、可直接跳过），与宿主逻辑
//       完全解耦，可原样复用到任意 Inno Setup 6 安装项目。
//
// 接入三步（详见 README.md）：
//   1) 宿主 .iss 的 [Files] 段声明收款码图片（只临时释放、不装入程序）：
//        Source: "wx.bmp"; Flags: dontcopy nocompression
//        Source: "zfb.bmp"; Flags: dontcopy nocompression
//   2) 宿主 .iss 的 [Code] 段第一行写入：
//        #include "donate\donate_page.iss"
//   3) 宿主 [Code] 段的三个向导事件各接一行：
//        procedure InitializeWizard; begin DonateInit; end;
//        function ShouldSkipPage(PageID: Integer): Boolean;
//        begin Result := DonateShouldSkipPage(PageID); end;
//        procedure CurPageChanged(CurPageID: Integer);
//        begin DonateOnPageChanged(CurPageID); end;
//
// 可选配置（在 #include 之前用 #define 覆盖，均有默认值）：
//   DONATE_IMG_WX       微信收款码文件名    默认 "wx.bmp"
//   DONATE_IMG_ZFB      支付宝收款码文件名   默认 "zfb.bmp"
//   DONATE_REG_KEY      注册表键（HKCU）     默认 "Software\AIVoiceInput"
//   DONATE_REG_VAL      注册表值名（看过标记）默认 "TipShown"
//   DONATE_TITLE        页面标题           默认 "支持作者 · 随缘打赏（本步可直接跳过）"
//   DONATE_MAIN_TEXT    主文案             默认 "如果这个小工具帮你省下了一点时间，欢迎随缘打赏——哪怕 0.01 元，也是对我莫大的支持，非常感谢。"
//   DONATE_ONCE_TEXT    仅出现一次提示      默认 "这两个码只在安装时出现，平时不会再弹～错过这次就没这么方便啦，当然直接点「完成」也完全没问题。"
// ============================================================================

#ifndef DONATE_IMG_WX
  #define DONATE_IMG_WX "wx.bmp"
#endif
#ifndef DONATE_IMG_ZFB
  #define DONATE_IMG_ZFB "zfb.bmp"
#endif
#ifndef DONATE_REG_KEY
  #define DONATE_REG_KEY "Software\AIVoiceInput"
#endif
#ifndef DONATE_REG_VAL
  #define DONATE_REG_VAL "TipShown"
#endif
#ifndef DONATE_TITLE
  #define DONATE_TITLE "支持作者 · 随缘打赏（本步可直接跳过）"
#endif
#ifndef DONATE_MAIN_TEXT
  #define DONATE_MAIN_TEXT "如果这个小工具帮你省下了一点时间，欢迎随缘打赏——哪怕 0.01 元，也是对我莫大的支持，非常感谢。"
#endif
#ifndef DONATE_ONCE_TEXT
  #define DONATE_ONCE_TEXT "这两个码只在安装时出现，平时不会再弹～错过这次就没这么方便啦，当然直接点「完成」也完全没问题。"
#endif

var
  DonateTipPage: TWizardPage;
  DonateImgWX, DonateImgZFB: TBitmapImage;
  DonateLblMain, DonateLblOnce: TNewStaticText;

function DonateMinR(a, b: Extended): Extended;
begin
  if a < b then Result := a else Result := b;
end;

function DonateHasSeenTip: Boolean;
var v: String;
begin
  Result := RegQueryStringValue(HKCU, '{#DONATE_REG_KEY}', '{#DONATE_REG_VAL}', v) and (v = '1');
end;

// 创建打赏页：页面、两行文案、双收款码（从安装包临时释放）
procedure DonateInit;
begin
  DonateTipPage := CreateCustomPage(wpInstalling, '{#DONATE_TITLE}', '');

  DonateLblMain := TNewStaticText.Create(DonateTipPage);
  DonateLblMain.Parent := DonateTipPage.Surface;
  DonateLblMain.AutoSize := False;
  DonateLblMain.WordWrap := True;
  DonateLblMain.Font.Size := 10;
  DonateLblMain.Font.Style := [fsBold];
  DonateLblMain.Caption := '{#DONATE_MAIN_TEXT}';

  DonateLblOnce := TNewStaticText.Create(DonateTipPage);
  DonateLblOnce.Parent := DonateTipPage.Surface;
  DonateLblOnce.AutoSize := False;
  DonateLblOnce.WordWrap := True;
  DonateLblOnce.Font.Size := 9;
  DonateLblOnce.Font.Color := clGrayText;
  DonateLblOnce.Caption := '{#DONATE_ONCE_TEXT}';

  DonateImgWX := TBitmapImage.Create(DonateTipPage);
  DonateImgWX.Parent := DonateTipPage.Surface;
  DonateImgWX.Stretch := True;
  ExtractTemporaryFile('{#DONATE_IMG_WX}');
  DonateImgWX.Bitmap.LoadFromFile(ExpandConstant('{tmp}\{#DONATE_IMG_WX}'));

  DonateImgZFB := TBitmapImage.Create(DonateTipPage);
  DonateImgZFB.Parent := DonateTipPage.Surface;
  DonateImgZFB.Stretch := True;
  ExtractTemporaryFile('{#DONATE_IMG_ZFB}');
  DonateImgZFB.Bitmap.LoadFromFile(ExpandConstant('{tmp}\{#DONATE_IMG_ZFB}'));
end;

// 宿主 ShouldSkipPage 接线：看过一次（HKCU 标记）则以后安装/升级永久跳过
function DonateShouldSkipPage(PageID: Integer): Boolean;
begin
  Result := (PageID = DonateTipPage.ID) and DonateHasSeenTip;
end;

// 按页面实际尺寸自适应：两码等比缩放、并排居中，文字自动换行；随系统 DPI 缩放
procedure DonateLayout;
var
  surfW, surfH, gap, colW, y: Integer;
  dw1, dh1, dw2, dh2, x1, x2, availH: Integer;
  sc: Extended;
begin
  surfW := DonateTipPage.SurfaceWidth;
  surfH := DonateTipPage.SurfaceHeight;
  gap := ScaleX(14);

  DonateLblMain.SetBounds(ScaleX(2), ScaleY(2), surfW - ScaleX(4), ScaleY(40));
  y := DonateLblMain.Top + DonateLblMain.Height + ScaleY(4);
  DonateLblOnce.SetBounds(DonateLblMain.Left, y, surfW - ScaleX(4), ScaleY(36));
  y := DonateLblOnce.Top + DonateLblOnce.Height + ScaleY(8);

  colW := (surfW - gap) div 2;
  availH := surfH - y;

  sc := DonateMinR((colW * 1.0) / DonateImgWX.Bitmap.Width, (availH * 1.0) / DonateImgWX.Bitmap.Height);
  dw1 := Round(DonateImgWX.Bitmap.Width * sc);
  dh1 := Round(DonateImgWX.Bitmap.Height * sc);
  sc := DonateMinR((colW * 1.0) / DonateImgZFB.Bitmap.Width, (availH * 1.0) / DonateImgZFB.Bitmap.Height);
  dw2 := Round(DonateImgZFB.Bitmap.Width * sc);
  dh2 := Round(DonateImgZFB.Bitmap.Height * sc);

  x1 := (colW - dw1) div 2;
  x2 := colW + gap + (colW - dw2) div 2;
  DonateImgWX.SetBounds(x1, y, dw1, dh1);
  DonateImgZFB.SetBounds(x2, y, dw2, dh2);
end;

// 宿主 CurPageChanged 接线：进入打赏页时改“完成”按钮、布局、写看过标记
procedure DonateOnPageChanged(CurPageID: Integer);
begin
  if CurPageID = DonateTipPage.ID then
  begin
    WizardForm.NextButton.Caption := '完成(&F)';
    DonateLayout;
    RegWriteStringValue(HKCU, '{#DONATE_REG_KEY}', '{#DONATE_REG_VAL}', '1');
  end;
end;