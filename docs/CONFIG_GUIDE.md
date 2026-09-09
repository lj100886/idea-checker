# 免费配置引导：零成本跑通 idea-checker

idea-checker 需要两样东西才能工作：一个 **LLM API**（生成分析报告，必配）+ 若干**搜索源 key**（提高搜索质量，可选但推荐）。全部免费可搞。

## 一、LLM API（必配）——推荐智谱，永久免费

1. 打开 https://bigmodel.cn/ 用手机号注册（免信用卡）
2. 进入控制台 → **API Keys** → 创建新 Key → 复制（格式类似 `xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx.xxxx`）
3. 编辑本机配置文件 `~/.idea-checker/config.json`（Windows 为 `C:\Users\你的用户名\.idea-checker\config.json`）：

```json
{
  "llm": {
    "mode": "api",
    "api": {
      "base_url": "https://open.bigmodel.cn/api/paas/v4/",
      "api_key": "你的智谱API Key",
      "model": "glm-4-flash"
    }
  }
}
```

可选模型：`glm-4-flash`（128K 上下文）/ `glm-4.7-flash`（200K，更新更快），均为永久免费。

> 其他 OpenAI 兼容平台（硅基流动、火山方舟、DeepSeek 等）同样可用：把 `base_url`、`api_key`、`model` 换成对应平台的即可。

## 二、Tavily 搜索源（推荐，免费网页搜索）

1. 打开 https://tavily.com/ 注册，在控制台获取 API Key（免费额度：每月 1000 次搜索）
2. 在 `config.json` 中加入：

```json
{
  "search": {
    "sources": ["github", "aihot", "tavily"],
    "tavily": {
      "api_key": "你的Tavily API Key",
      "max_results": 10
    }
  }
}
```

Tavily 作为网页搜索源，在 GitHub 限速或 aihot 不可用时自动兜底，AI 类查询默认优先走它。

## 三、GitHub Token（可选但强烈推荐）

1. GitHub → **Settings** → **Developer settings** → **Personal access tokens** → **Generate new token**（权限勾选 `repo` 即可）
2. 在 `config.json` 中加入：

```json
{
  "search": {
    "github": {
      "token": "你的GitHub Token"
    }
  }
}
```

作用：仓库搜索 + 候选精读的限额从 **60 次/小时**提升到 **5000 次/小时**（不配也能用，但多轮审查容易撞限速）。

## 四、完整 config.json 示例（全部为占位符，勿填真实值提交）

```json
{
  "llm": {
    "mode": "api",
    "api": {
      "base_url": "https://open.bigmodel.cn/api/paas/v4/",
      "api_key": "YOUR_ZHIPU_API_KEY",
      "model": "glm-4-flash",
      "timeout": 60,
      "max_retries": 2
    }
  },
  "search": {
    "sources": ["github", "aihot", "tavily"],
    "github": { "token": "", "max_results": 10 },
    "aihot": { "endpoint": "https://aihot.virxact.com/api/mcp?aihot_actor=YOUR_AIHOT_ACTOR_TOKEN", "max_results": 10 },
    "tavily": { "api_key": "YOUR_TAVILY_API_KEY", "max_results": 10 }
  }
}
```

## 五、安全须知

- **API Key 只存本机 `~/.idea-checker/config.json`**，该文件已被仓库 `.gitignore` 忽略，**不要提交到任何仓库、不要截图分享、不要发给别人**
- 如果怀疑 key 泄露，去对应平台控制台**立即吊销并重新生成**
- aihot 搜索源为可选：如不需要，把 `sources` 里的 `"aihot"` 删掉即可
