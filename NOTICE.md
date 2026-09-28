# NOTICE — 权利归属与许可范围

## 1. 本仓库原创部分（MIT）

以下内容由本仓库作者创作，按 [LICENSE](LICENSE) 的 MIT 条款授权：

- `install_zh.ps1` — 安装 / 回滚 / 校验脚本
- `build_release.py` — 发布包构建脚本
- `README.md`、`docs/` 下的说明与决策文档
- `SHA256SUMS.txt`

## 2. 不属于本仓库的部分（游戏原始内容）

以下文件是 **hackmud 游戏本体文件的修改版本**，其著作权归 hackmud 开发者所有：

| 文件 | 说明 |
|---|---|
| `Managed/Core.dll` | 游戏主程序集（在 `#US` 字符串堆上做了等长文本替换） |
| `resources.assets` | 游戏字体资产（替换为合并了中文字形的字体） |

- 本仓库**不主张**对这些文件及其原始内容的任何权利。
- 这些文件仅出于**汉化技术交流**目的分发，供已经**合法拥有**该游戏的用户使用。
- **本补丁不包含、也不替代游戏本体**；用户必须自行通过 Steam 购买并安装 hackmud。
- 若权利人（hackmud 开发者或其它权利方）提出要求，本仓库将**立即移除**相关文件乃至整个仓库。

## 3. 使用风险（重要）

hackmud 官方规则（<https://www.hackmud.com/forums/general_discussion/rules>）明确写着：

> Adding files to the directory hierarchy of the game is currently permitted.
> **Modifying any existing files is not permitted.**
> **client file modification** … is considered a 'custom client'
> **Any detected custom client activity will result in bans.**

本补丁修改了游戏的既有文件，属于上述**被禁止的行为**，**存在账号被封禁的风险**。
请在使用前自行评估，**风险由使用者自行承担**。

## 4. 免责声明

本补丁按「现状」提供，不附带任何明示或默示的担保。因使用本补丁造成的任何直接或间接
后果（包括但不限于游戏无法运行、存档损坏、账号封禁、Steam 账号受影响），
作者不承担任何责任。

## 5. 与官方无关

本项目为个人兴趣作品，与 hackmud 官方无任何关联，未获其授权、认可或赞助。
"hackmud" 及相关名称、标识的权利归其各自所有者。
