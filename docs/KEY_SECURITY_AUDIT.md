# KEY_SECURITY_AUDIT · idea-checker 密钥安全审计报告

> 审计日期：2026-09-09（2026-09-10 更新收款码描述）
> 审计对象：GitHub 公开仓库 `lj100886/idea-checker`（main 分支 + v1.0.0 release）
> 审计方式：仓库文件清单核验 + 全部文本文件人工全文核查 + 提交历史逐 commit 核验 + 历史重写工具处置

---

## 一、结论

- **用户私人 LLM API Key 未泄露**：agnes（`sk-5fwq` 前缀）与火山方舟（`ark-22fbfd` 前缀）的 Key 在仓库当前内容与全部提交历史中均未出现。
- **发现并已清除一处敏感值**：`src/config.py` 默认配置中硬编码的 aihot 搜索源 actor token（UUID 格式）此前从第 6 个提交起存在于所有版本及 v1.0.0 附带的 `idea-checker.exe` 中。已通过 git 历史重写从全部历史中移除，并将代码中的值替换为占位符 `YOUR_AIHOT_ACTOR_TOKEN`。

## 二、核查明细

| 检查项 | 结果 |
|---|---|
| 仓库文件清单（根目录 + 全部子目录） | 无 `config.json` / `.env` / `*.key` / `secret*` / `token*` 类文件 |
| 全部文本文件全文核查（.py/.md/.yaml/.json/.iss/.spec/.txt） | 仅发现 aihot actor token 一处真实敏感值；LLM Key、搜索 token 字段均为空或占位符 |
| `README.md` 配置示例 | 占位符「你的key」，无需修改 |
| 收款码文件 | 仓库有 `assets/donation/wx.bmp` / `zfb.bmp`（真实收款码，2026-09-10 替换原占位图）；`wx_b64.txt` / `zfb_b64.txt` 从未入库 |
| 提交历史（20 个 commit） | `config.json` / `.env` / b64 文件从未入库；aihot token 自 `fa1c3c46` 起存在 |
| release v1.0.0 | target = 最新 commit；附带的 `idea-checker.exe`（编译产物）含同一 token |

## 三、处置记录

1. **git 历史重写**：`git filter-repo --replace-text` 将全部历史中出现的 aihot actor token 替换为占位符（20 个 commit 全部重写），随后 `--force` 推送 main 与 v1.0.0 tag。
2. **代码加固**：`src/config.py` 中 `search.aihot.endpoint` 现为 `https://aihot.virxact.com/api/mcp?aihot_actor=YOUR_AIHOT_ACTOR_TOKEN`，真实 token 改由用户级配置 `~/.idea-checker/config.json` 覆盖。
3. **`.gitignore` 补全**：新增 `config*.json`、`.env`、`*.key`、`.idea-checker/` 规则，防止配置类文件再次入库。
4. **README**：配置示例本为占位符，未改动。
5. **打赏收款码**：2026-09-10 将 `assets/donation/` 中两张无关占位图替换为真实微信/支付宝收款码（BMP 格式，与 `idea-checker.iss` 引用一致）。

## 四、完成标准核对

- [x] 仓库文件清单已核对，无 `config.json` / `.env` 类文件
- [x] 所有仓库文件内容无 `sk-5fwq` / `ark-22fbfd` / aihot actor 真实值（当前 + 全部历史）
- [x] 提交历史无敏感文件残留（含 v1.0.0 tag 对应 commit）
- [x] `.gitignore` 已补全并推送
- [x] 历史已清除 + 审计报告存档

## 五、遗留建议（需用户本人操作）

- **轮换 aihot actor token**：该 token 曾长期暴露于公开仓库，理论上可能已被爬虫抓取，建议在 aihot 平台撤销并重建，更新至 `~/.idea-checker/config.json`。
- **重建 v1.0.0 发布物**：已上传的 `idea-checker.exe`（release asset）编译时内嵌了旧 token，历史重写不影响该文件；建议删除旧 release asset，用清理后的代码重新打包上传，或下架该 release。
- 本地 `~/.idea-checker/config.json` 从未进入仓库，不受本次处置影响；其中如有 LLM Key，保持现状即可。

---

*本报告不包含任何 Key 明文。*
