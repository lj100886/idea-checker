# 打赏模块说明

## 随缘打赏页（Inno Setup 可复用模块）

在安装程序末尾插入一页“随缘打赏”，微信+支付宝双收款码，每台电脑只出现一次。

## 文件说明

- `donate_page.iss` — 打赏页核心模块（Inno Setup [Code] 段片段）
- `wx.bmp` — 微信收款码（替换为你的真实收款码）
- `zfb.bmp` — 支付宝收款码（替换为你的真实收款码）
- `README.md` — 本说明

## 接入方法

### 1. 在宿主 .iss 的 [Files] 段声明收款码

```iss
Source: "assets/donation/wx.bmp"; Flags: dontcopy nocompression
Source: "assets/donation/zfb.bmp"; Flags: dontcopy nocompression
```

### 2. 在 [Code] 段第一行引入

```iss
#include "assets/donation/donate_page.iss"
```

### 3. 接线三个向导事件

```iss
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
```

## 可选配置

在 `#include` 之前用 `#define` 覆盖：

```iss
#define DONATE_TITLE "支持作者"
#define DONATE_MAIN_TEXT "如果这个工具对你有帮助，欢迎随缘打赏"
#define DONATE_REG_KEY "Software\YourApp"
```

## 特点

- 每台电脑只显示一次（HKCU 注册表标记）
- 双收款码并排，自适应缩放
- 可直接跳过，不强制
- 与宿主逻辑完全解耦
