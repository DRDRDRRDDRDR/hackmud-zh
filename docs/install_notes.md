# hackmud 简体中文汉化补丁 — 安装说明

## 补丁内容
- `Managed/Core.dll` — 主程序集,256 条界面/帮助文本简体中文化(等长回写,结构不变)
- `resources.assets` — 字体资产替换:合并字体(Liberation Sans + 思源黑体子集,含 CJK 字形),中文字符可正常渲染
- `install_zh.ps1` — 一键安装/回滚/校验脚本(推荐)

## 适用版本
- hackmud Steam 版(Unity 6 / Mono),数据目录 `hackmud_win_Data`
- 已测试文件版本:Core.dll 541,184 B / resources.assets 498,972 B(未压缩)

## ★ 一键安装(推荐)
1. 完全退出 Steam 与 hackmud(任务管理器确认 `hackmud_win.exe` 已结束)
2. 右键 `install_zh.ps1` → 「使用 PowerShell 运行」,或手动执行:
   ```
   powershell -ExecutionPolicy Bypass -File install_zh.ps1 install
   ```
3. 脚本自动:备份原文件(.bak) → 复制汉化文件 → 校验哈希
4. 看到「✔ 安装校验通过」后,启动 Steam → 运行 hackmud

脚本支持三个动作:
| 动作 | 命令 | 说明 |
|---|---|---|
| 安装 | `install_zh.ps1 install` | 备份+替换+校验(幂等,已汉化时自动跳过) |
| 回滚 | `install_zh.ps1 rollback` | 从 .bak 恢复原版并校验 |
| 校验 | `install_zh.ps1 verify` | 检查当前状态(汉化版/原版/未知) |

## 手动安装(备选)
1. 完全退出 Steam 与 hackmud
2. 备份原文件(必须!):
   - `steamapps\common\hackmud\hackmud_win_Data\Managed\Core.dll`
   - `steamapps\common\hackmud\hackmud_win_Data\resources.assets`
   建议复制到补丁目录的 `backup/` 下,或改名加 `.bak`
3. 用本补丁目录内同名文件覆盖:
   - `Managed\Core.dll` → `hackmud_win_Data\Managed\Core.dll`
   - `resources.assets` → `hackmud_win_Data\resources.assets`
4. 启动 Steam → 运行 hackmud

## 回滚方法
- 方法 A(推荐):`powershell -ExecutionPolicy Bypass -File install_zh.ps1 rollback`
- 方法 B:把手动备份的原文件复制回去
- 方法 C:Steam 库 → 右键 hackmud → 属性 → 本地文件 → 验证游戏文件完整性
  (会恢复被替换的文件,但需重新下载字体资源约 11MB)

## 校验(可选)
- 一键:`powershell -ExecutionPolicy Bypass -File install_zh.ps1 verify`
- 手动对比 SHA256SUMS.txt:
  ```
  # PowerShell(在补丁目录)
  Get-FileHash Managed\Core.dll -Algorithm SHA256
  Get-FileHash resources.assets -Algorithm SHA256
  ```
  两个哈希应与 SHA256SUMS.txt 一致。

## 术语保留说明(刻意不译)
以下字符串**保持英文**,因为它们参与游戏逻辑或属服务器协议,翻译会破坏功能:
- `FULLSEC` / `MIDSEC` / `HIGHSEC`(以及 `LOWSEC` / `NULLSEC`)—— 服务器端安全等级权威表
  的取值,客户端会用它们做 JSON 键查询与相等比较;玩家在 marks 教程中需按英文原样键入
- `success`(小写) —— 服务器 JSON 的协议字段名
- 所有命令名与标识符(`trade` / `#help` / `accts.balance` 等)

## 已知说明
- 游戏为在线多人;服务器下发的文本(其他玩家消息、排行、公告)无法本地汉化
- 帮助/界面中的终端对齐基于等宽英文,中文按 2 倍宽显示,部分表格列可能错位(仅显示问题,不影响功能)
- 命令名保持英文(游戏按英文解析玩家输入),如 `trade`/`#help`/`accts.balance` 等
- 若字体替换后出现崩溃或异常,请用备份回滚并反馈

## 文件哈希
ff84c309ff511d6c23d4952477a58ff17d913f8417371cd52b54d9925dc7a4ad  Managed\Core.dll
5b2345f938d02a4289a76518d3dea8b604cd3eaedde870c3bae8958cdab2c6d7  resources.assets
