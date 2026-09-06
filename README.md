# idea-checker 选题审查员

> 输入一个想法/项目/选题，AI自动联网搜索，判断有没有人做过、做得怎么样、有没有差异化空间，输出带评级的审查报告。

## 特性

- **AI自主审查**：拆解想法→多轮搜索→分析→自主判断停止→生成报告
- **多触发方式**：命令行 / 桌面宠物 / 文件监控 / MCP服务器
- **多LLM后端**：智能体框架优先（主），OpenAI兼容API降级
- **免key搜索**：GitHub + DuckDuckGo + aihot，三个搜索源全部免费
- **自定义人设**：默认/毒舌程序员/猫娘/人工智障，支持扩展
- **触发式监控**：自动监控智能体框架会话目录，新项目自动审查
- **随缘打赏页**：安装程序集成打赏页（微信+支付宝），每台电脑只出现一次

## 快速开始

### 安装

```bash
pip install -r requirements.txt
```

### 配置

编辑 `~/.idea-checker/config.json`，至少配置LLM API：

```json
{
  "llm": {
    "mode": "api",
    "api": {
      "base_url": "https://api.siliconflow.cn/v1",
      "api_key": "你的key",
      "model": "Qwen/Qwen3-8B"
    }
  }
}
```

也可以用环境变量：`IDEA_CHECKER_LLM_API_KEY`

### 使用方式

#### 1. 命令行单次审查

```bash
python main.py "做一个AI猫娘桌面宠物"
python main.py "做一个AI猫娘桌面宠物" -p idiot_ai -f json
```

#### 2. 交互模式

```bash
python main.py
想法> 做一个AI猫娘桌面宠物
```

#### 3. 桌面宠物模式

```bash
python main.py --pet
```

桌面上出现一个摆动的小人，点击弹出审查面板。

#### 4. 文件监控模式

```bash
python main.py --watch
```

自动监控智能体框架（Claude Code/AutoGPT等）的会话目录，检测到新项目自动审查。

#### 5. MCP服务器模式

```bash
python main.py --mcp
```

在Claude Desktop/Cursor等MCP客户端中配置，直接调用 `check_idea` 工具。

## 人设

| 人设 | 说明 |
|------|------|
| `default` | 专业审查员 |
| `toxic_dev` | 毒舌程序员，一针见血 |
| `catgirl` | 猫娘，可爱带喵口癖 |
| `idiot_ai` | 人工智障，一本正经胡说八道但偶尔神级建议 |

## 评级说明

- **S级·蓝海**：几乎没人做，或现有方案都很烂
- **A级·有空间**：有人做，但有明显差异化机会
- **B级·竞争中**：有不少人做，需要很强的差异化
- **C级·红海**：已经有成熟的头部产品，很难突围

## 打包成exe

```bash
pyinstaller idea-checker.spec --clean --noconfirm
```

生成的exe在 `dist/idea-checker.exe`

## 制作带打赏页的安装程序

1. 安装 [Inno Setup 6](https://jrsoftware.org/isinfo.php)
2. 把你的微信/支付宝收款码保存为 `assets/donation/wx.bmp` 和 `assets/donation/zfb.bmp`
3. 运行：`ISCC.exe idea-checker.iss`
4. 生成的安装程序在 `dist_installer/`

打赏页只在安装时出现一次，以后升级/重装都不会再弹。

## 项目结构

```
idea-checker/
├── main.py                    # 入口
├── requirements.txt
├── idea-checker.iss           # Inno Setup安装脚本（含打赏页）
├── idea-checker.spec          # PyInstaller打包配置
├── config/
│   ├── personas/              # 人设库
│   └── prompts/               # 提示词（版本化）
├── src/
│   ├── models.py              # 数据模型
│   ├── config.py              # 配置管理
│   ├── core/                  # 核心逻辑
│   ├── llm/                   # LLM执行层
│   ├── search/                # 搜索源
│   ├── triggers/              # 触发器
│   └── ui/                    # 桌面宠物UI
├── assets/
│   ├── donation/              # 打赏模块（收款码+脚本）
│   └── pets/                  # 宠物形象
└── docs/
    └── architecture.md        # 架构设计文档
```

## 架构

详见 [docs/architecture.md](docs/architecture.md)

核心设计：
- **core纯逻辑**：不关心触发方式和LLM实现
- **触发器可插拔**：CLI/桌面宠物/文件监控/MCP，都调用同一个core
- **LLM双模式**：智能体框架优先，直接API降级