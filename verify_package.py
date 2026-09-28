# -*- coding: utf-8 -*-
"""verify_package.py — 校验发布包自洽性（CI 与本地共用同一份判据）。

检查项：
  1. 必备文件齐全
  2. 两个载荷文件的实际 SHA256 与 SHA256SUMS.txt 一致
  3. install_zh.ps1 内嵌的 4 个哈希常量与载荷 / 原版值一致
  4. install_zh.ps1 是 UTF-8 WITH BOM（PS 5.1 无 BOM 会按 GBK 解码，中文乱码）
  5. SHA256SUMS.txt 覆盖的路径确实存在

退出码 0 = 全部通过；1 = 有失败项（逐条打印）。
用法:
    python verify_package.py            # 校验脚本所在目录
    python verify_package.py <dir>      # 校验指定目录
"""
import os
import re
import sys
import hashlib

REQUIRED = [
    "README.md", "LICENSE", "NOTICE.md", ".gitattributes",
    "install_zh.ps1", "build_release.py", "verify_package.py", "ci_selftest.py",
    "SHA256SUMS.txt", "Managed/Core.dll", "resources.assets",
    "docs/install_notes.md", "docs/术语保留决策.md",
    "audit_protocol.py",
]

# 原版哈希（回滚校验用）
ORIG = {
    "Core.dll": "D424EAB9372946946B5FFD9DC49B17D9C5060B3CEC638A5952E7EAD99CD696E6",
    "resources.assets": "E2E661C96397F9C444936B9767F7F723B5FDAF64FC4ECB04B52E7D5B678C0003",
}


def sha256(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest().upper()


def main():
    root = sys.argv[1] if len(sys.argv) > 1 else os.path.dirname(os.path.abspath(__file__))
    fails = []
    notes = []

    def fail(msg):
        fails.append(msg)
        print("  FAIL  %s" % msg)

    def ok(msg):
        print("  ok    %s" % msg)

    print("== verify_package: %s ==" % root)

    # 1. 必备文件
    print("\n[1] 必备文件")
    for rel in REQUIRED:
        if os.path.exists(os.path.join(root, rel)):
            ok(rel)
        else:
            fail("缺少 %s" % rel)

    # 2. 载荷哈希 vs SHA256SUMS.txt
    print("\n[2] 载荷哈希 vs SHA256SUMS.txt")
    sums_path = os.path.join(root, "SHA256SUMS.txt")
    declared = {}
    if os.path.exists(sums_path):
        for line in open(sums_path, encoding="utf-8"):
            m = re.match(r"^([0-9A-Fa-f]{64})\s+(\S.*)$", line.strip())
            if m:
                # 归一化 Windows 反斜杠路径
                declared[m.group(2).replace("\\", "/").strip()] = m.group(1).upper()
        if not declared:
            fail("SHA256SUMS.txt 解析不出任何条目")
    else:
        fail("缺少 SHA256SUMS.txt")

    actual = {}
    for rel in ("Managed/Core.dll", "resources.assets"):
        p = os.path.join(root, rel)
        if not os.path.exists(p):
            continue
        actual[rel] = sha256(p)
        want = declared.get(rel)
        if want is None:
            fail("SHA256SUMS.txt 未覆盖 %s" % rel)
        elif want != actual[rel]:
            fail("%s 哈希不符: 实际 %s / 声明 %s" % (rel, actual[rel], want))
        else:
            ok("%s %s" % (rel, actual[rel][:16] + "..."))

    # 3. install_zh.ps1 内嵌常量
    print("\n[3] install_zh.ps1 内嵌哈希常量")
    ps1_path = os.path.join(root, "install_zh.ps1")
    raw = b""
    if os.path.exists(ps1_path):
        raw = open(ps1_path, "rb").read()
        text = raw.decode("utf-8-sig", errors="replace")
        expect = {
            "PatchCoreHash": actual.get("Managed/Core.dll"),
            "PatchAssetsHash": actual.get("resources.assets"),
            "OrigCoreHash": ORIG["Core.dll"],
            "OrigAssetsHash": ORIG["resources.assets"],
        }
        for name, want in expect.items():
            m = re.search(r"\$%s\s*=\s*\"([0-9A-Fa-f]{64})\"" % name, text)
            if not m:
                fail("找不到 $%s 常量" % name)
                continue
            got = m.group(1).upper()
            if want is None:
                notes.append("$%s 无法交叉验证（载荷缺失）" % name)
                ok("$%s = %s (未交叉验证)" % (name, got[:16] + "..."))
            elif got != want:
                fail("$%s 与载荷不一致: 脚本 %s / 实际 %s" % (name, got, want))
            else:
                ok("$%s = %s" % (name, got[:16] + "..."))
    else:
        fail("缺少 install_zh.ps1")

    # 4. BOM
    print("\n[4] install_zh.ps1 编码")
    if raw:
        if raw[:3] == b"\xef\xbb\xbf":
            ok("UTF-8 BOM 存在")
        else:
            fail("缺少 UTF-8 BOM（PS 5.1 下中文会乱码）")
        try:
            body = raw.decode("utf-8-sig")
            if "\ufffd" in body:
                fail("解码后含 U+FFFD（替换字符），文件可能已损坏")
            else:
                ok("UTF-8 严格解码通过")
        except UnicodeDecodeError as e:
            fail("不是合法 UTF-8: %s" % e)

    # 5. 声明路径存在
    print("\n[5] SHA256SUMS.txt 声明的路径存在")
    for rel in declared:
        if os.path.exists(os.path.join(root, rel)):
            ok(rel)
        else:
            fail("声明了 %s 但文件不存在" % rel)

    print("\n== 结果: %d 项失败 ==" % len(fails))
    for n in notes:
        print("  note  %s" % n)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
