# hackmud 简体中文汉化补丁

[![verify-package](https://github.com/DRDRDRRDDRDR/hackmud-zh/actions/workflows/verify.yml/badge.svg)](https://github.com/DRDRDRRDDRDR/hackmud-zh/actions/workflows/verify.yml)

给 Steam 版 **hackmud**（Unity 6 / Mono）做的简体中文汉化补丁，**等长回写**游戏主程序集，
并替换字体资产以支持中文字形渲染。

- 汉化条目：**256 条**（界面提示、错误信息、帮助文本、终端横幅）
- 字体：把游戏的 Liberation Sans 与思源黑体子集合并，中文字符可正常渲染
- 安装：一键 PowerShell 脚本，自动备份 → 覆盖 → 哈希校验，支持**一键回滚**
- 发布包每次提交都过 CI：载荷哈希、脚本内嵌常量、编码、以及安装/幂等/回滚往返

---

## ⚠️ 请先读这一段

1. **本补丁修改游戏既有文件**（`Core.dll`、`resources.assets`）。hackmud 官方规则明确写着：

   > Adding files to the directory hierarchy of the game is currently permitted.
   > **Modifying any existing files is not permitted.**
   > **client file modification** … is considered a 'custom client'
   > **Any detected custom client activity will result in bans.**

   也就是说，**使用本补丁存在被封号的风险**。请自行判断是否安装，风险自负。
2. 本仓库分发的 `Core.dll` / `resources.assets` 是**修改后的游戏文件**，其版权归 hackmud
   开发者所有；本仓库仅出于汉化交流目的分发。若权利人提出要求，将立即移除。
3. 建议**仅在个人自用环境**使用。介意风险请不要安装。

---

## 快速开始

### 环境要求

- Windows，已安装 Steam 版 hackmud
- 默认游戏目录：`C:\Program Files (x86)\Steam\steamapps\common\hackmud\hackmud_win_Data`
  （装在其它 Steam 库或盘符的，用 `-GameData` 指定，见下文）
- PowerShell 5.1（系统自带）

### 安装

1. **完全退出 Steam 与 hackmud**（任务管理器确认 `hackmud_win.exe` 已结束）
2. 下载本仓库（`Code → Download ZIP`，或 `git clone`），解压
3. 在本目录打开 PowerShell，执行：

   ```powershell
   powershell -ExecutionPolicy Bypass -File install_zh.ps1 install
   ```

   也可以直接右键 `install_zh.ps1` → **使用 PowerShell 运行**。

4. 看到 `✔ 安装校验通过` 后，启动 Steam → 运行 hackmud

游戏装在别处时：

```powershell
powershell -ExecutionPolicy Bypass -File install_zh.ps1 install -GameData "D:\SteamLibrary\steamapps\common\hackmud\hackmud_win_Data"
```

### 回滚 / 校验

| 动作 | 命令 | 说明 |
|---|---|---|
| 安装 | `install_zh.ps1 install` | 备份 + 覆盖 + 校验；幂等（已装则跳过） |
| 回滚 | `install_zh.ps1 rollback` | 从 `.bak` 恢复原版并校验 |
| 校验 | `install_zh.ps1 verify` | 查看当前是「汉化版 / 原版 / 未知」 |

脚本把原文件备份为 `Core.dll.bak` 与 `resources.assets.bak`（**仅首次安装时创建**，不会覆盖已有备份）。
另可用 Steam「验证游戏文件完整性」恢复原版（会重新下载字体资源，约 11 MB）。

---

## 汉化范围

### 已汉化

- 终端横幅与状态行（`-terminal active-` → `-终端已激活-` 等）
- 命令用法、解析错误、参数校验失败等提示
- 帮助文本与常用脚本清单
- 脚本执行结果状态词（`Success` / `Failure` → `成功` / `失败`）

### 刻意保留英文（不译）

| 保留项 | 原因 |
|---|---|
| `FULLSEC` / `MIDSEC` / `HIGHSEC` / `LOWSEC` / `NULLSEC` | 服务器端 `scripts.lib().security_level_names` 的权威取值；客户端用它们做 JSON 键查询与相等比较；且是官方沙盒规则里的**安全边界** |
| 所有命令名与脚本名（`trade`、`#help`、`accts.balance`、`marks.*` …） | 游戏按英文解析玩家输入，且服务端校验 |
| `success`（小写，JSON 协议字段名） | 服务器通信协议的一部分 |

详见 [`docs/术语保留决策.md`](docs/术语保留决策.md)。

---

## 已知限制

- **在线内容无法汉化**：hackmud 是在线多人游戏，服务器下发的文本（其他玩家消息、排行榜、
  公告、marks 教学脚本输出）不经客户端，补丁改不到。
- **终端表格可能错位**：帮助文本的对齐基于等宽英文，中文按 2 倍宽显示，部分表格列会偏（仅显示问题）。
- **历史滚动记录不会变**：游戏会把终端回滚缓冲（`%APPDATA%\hackmud\shell.txt`）在启动时回放，
  补丁前产生的英文历史仍是英文。游戏内输入 `clear`，或安装前备份并清空该文件即可。
- 若字体替换后出现异常，请用 `rollback` 回滚并反馈。

---

## 目录结构

```
.
├── install_zh.ps1          一键安装 / 回滚 / 校验
├── build_release.py        可复现地重建本发布包（同步哈希常量与 zip）
├── verify_package.py       校验包自洽性（CI 与本地共用同一份判据）
├── ci_selftest.py          反向自检：人为破坏必须被检出
├── Managed/Core.dll        汉化后的主程序集
├── resources.assets        含中文字形的字体资产
├── SHA256SUMS.txt          载荷哈希
├── LICENSE                 许可（仅覆盖原创的脚本与文档）
├── NOTICE.md               权利归属、使用风险与免责声明
├── .gitattributes          行尾规范（保证 clone 后内容一致、哈希可比对）
├── .github/workflows/       CI：包完整性 + 反向自检 + 安装脚本往返测试
└── docs/
    ├── install_notes.md        原始安装说明
    └── 术语保留决策.md          哪些刻意不译、依据是什么
```

## 自动化校验

本地跑一遍（和 CI 用的是同一份判据）：

```bash
python verify_package.py     # 载荷哈希 / 脚本内嵌常量 / BOM / 必备文件
python ci_selftest.py        # 反向自检：破坏后必须失败，否则说明闸门是空的
```

CI 三个作业（见 `.github/workflows/verify.yml`）：

| 作业 | 运行环境 | 做什么 |
|---|---|---|
| `integrity` | Linux | 跑 `verify_package.py` |
| `selftest` | Linux | 跑 `ci_selftest.py`：翻转载荷字节 / 改坏脚本常量 / 去掉 BOM / 篡改 `SHA256SUMS.txt` / 删必备文件 —— 五种破坏都必须被检出 |
| `installer` | Windows | 把补丁装进临时「假游戏目录」：`install` → 再 `install`（幂等）→ `verify` → `rollback`，并断言回滚后**逐字节**还原为原文件 |

### 维护者：改完载荷怎么重新发版

载荷（`Core.dll` / `resources.assets`）一变，安装脚本内嵌的 SHA256 常量、`SHA256SUMS.txt`
和分发 zip 三者必须同步，漏一个用户就会看到「校验失败」。所以别手工改，跑脚本：

```
python build_release.py          # 重新组装 + 重建 zip + 自检
python build_release.py --check  # 只校验当前仓库内容是否与真源一致
```

## 校验安装包完整性

```powershell
Get-FileHash Managed\Core.dll -Algorithm SHA256      # 应等于 SHA256SUMS.txt 中对应值
Get-FileHash resources.assets -Algorithm SHA256
```

| 文件 | SHA256 |
|---|---|
| `Managed/Core.dll` | `F6CBF53FC177FE8A04E6384D59C474A78D5120DC81B86C54CADF96C176AD9FD0` |
| `resources.assets` | `5B2345F938D02A4289A76518D3DEA8B604CD3EAEDDE870C3BAE8958CDAB2C6D7` |

原版哈希（回滚校验用）：`Core.dll` = `D424EAB9…696E6`，`resources.assets` = `E2E661C9…C0003`。

---

## 技术说明

- 文本改在 .NET 程序集的 **`#US`（user string）堆**里做**等长替换**：中文 + 空格填充到原
  UTF-16 长度，因此**堆大小、元数据 token、所有偏移全部不变**，不影响其它字符串。
- 字体：把游戏自带的 Liberation Sans 与中文黑体合并为单一 TTF（含 CJK 字形），替换
  `resources.assets` 中的 `Font` 对象 `m_FontData`。Unity 6 的动态字体在运行时用 FreeType
  按 `m_FontData` 重新生成字形，故旧的字形表被忽略。
- 汉化条目与判据（哪些能译、哪些不能）见 `docs/术语保留决策.md`。

## 许可

- 本仓库**原创部分**（安装脚本、构建脚本、文档）按 **MIT** 授权，见 [LICENSE](LICENSE)。
- 分发的**游戏二进制文件**（`Managed/Core.dll`、`resources.assets`）**不在** MIT 范围内，
  权利归 hackmud 开发者所有，仅作汉化交流之用。**本补丁不含游戏本体**，使用前请自行
  通过 Steam 购买并安装 hackmud。
- 权利归属、使用风险与免责声明的完整说明见 [NOTICE.md](NOTICE.md)。

## 致谢与声明

- hackmud 版权归其开发者（Sean Stoves 等）所有，本项目与官方无关。
- 本补丁为个人汉化作品，仅供学习与交流；请勿用于商业用途。
- 因使用本补丁产生的任何后果（包括但不限于账号封禁），由使用者自行承担。
