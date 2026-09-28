# -*- coding: utf-8 -*-
"""build_release.py — 可复现地组装公开仓库内容（hackmud-zh/release/）并打出分发包。

为什么需要它：release/ 目录里的安装脚本内嵌了载荷的 SHA256 常量。只要载荷变一次，
就必须同步更新该常量 + SHA256SUMS.txt + zip，三者任一漏改，用户装完就会看到"校验失败"。
本脚本把这一步固化成一条命令，避免手工漏改。

真源（recon/）：
    Core_zh.dll            汉化后的主程序集
    resources_zh.assets    含中文字形的字体资产
模板：
    dist/hackmud_zh_patch/install_zh.ps1   安装脚本模板（哈希常量会被重写）
    recon/decision_status_vs_sec.md        -> docs/术语保留决策.md

用法:
    python build_release.py            # 组装 release/ 并重建 dist/hackmud-zh-vX.zip
    python build_release.py --check    # 只校验当前 release/ 是否与真源一致，不写盘
"""
import os, re, sys, hashlib, shutil, zipfile

ROOT = r"C:\Users\DR\Downloads\DSH\hackmud-zh"
RECON = os.path.join(ROOT, "recon")
REL = os.path.join(ROOT, "release")
DIST = os.path.join(ROOT, "dist")
TEMPLATE_PS1 = os.path.join(DIST, "hackmud_zh_patch", "install_zh.ps1")

VERSION = "1.0.1"
ZIP = os.path.join(DIST, "hackmud-zh-v%s.zip" % VERSION)

# 真源 -> release 内的目标相对路径
PAYLOAD = {
    os.path.join(RECON, "Core_zh.dll"): "Managed/Core.dll",
    os.path.join(RECON, "resources_zh.assets"): "resources.assets",
    os.path.join(RECON, "decision_status_vs_sec.md"): "docs/术语保留决策.md",
    TEMPLATE_PS1: "install_zh.ps1",
    os.path.join(DIST, "hackmud_zh_patch", "install_notes.md"): "docs/install_notes.md",
}

# 原版哈希（回滚校验用），与 install_zh.ps1 内常量对应
ORIG_CORE = "D424EAB9372946946B5FFD9DC49B17D9C5060B3CEC638A5952E7EAD99CD696E6"
ORIG_ASSETS = "E2E661C96397F9C444936B9767F7F723B5FDAF64FC4ECB04B52E7D5B678C0003"


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def patch_ps1(text, core_hash, assets_hash):
    """把安装脚本里的三个哈希常量改写成当前值（保留 BOM 由调用方处理）。"""
    pairs = [("PatchCoreHash", core_hash), ("PatchAssetsHash", assets_hash)]
    for name, val in pairs:
        text, n = re.subn(r'(\$%s\s*=\s*")[0-9A-Fa-f]{64}(")' % name,
                          lambda m: m.group(1) + val + m.group(2), text)
        if n != 1:
            raise SystemExit("!! 无法在 install_zh.ps1 中定位 $%s（找到 %d 处）" % (name, n))
    # 原版哈希也应与常量一致（只校验存在性，不强制等于本机值）
    for name, val in (("OrigCoreHash", ORIG_CORE), ("OrigAssetsHash", ORIG_ASSETS)):
        text, n = re.subn(r'(\$%s\s*=\s*")[0-9A-Fa-f]{64}(")' % name,
                          lambda m: m.group(1) + val + m.group(2), text)
        if n != 1:
            raise SystemExit("!! 无法在 install_zh.ps1 中定位 $%s" % name)
    return text


def main():
    check_only = "--check" in sys.argv

    # ---- 1. 前置检查 ----
    missing = [s for s in PAYLOAD if not os.path.exists(s)]
    if missing:
        for m in missing:
            print("!! 真源缺失:", m)
        return 1

    core_hash = sha256(os.path.join(RECON, "Core_zh.dll"))
    assets_hash = sha256(os.path.join(RECON, "resources_zh.assets"))
    print("payload hashes")
    print("  Managed/Core.dll  %s" % core_hash)
    print("  resources.assets  %s" % assets_hash)

    # ---- 2. --check：只比对现状 ----
    if check_only:
        problems = 0
        for src, rel in PAYLOAD.items():
            dst = os.path.join(REL, rel)
            if not os.path.exists(dst):
                print("  MISSING in release/: %s" % rel); problems += 1; continue
            if rel in ("Managed/Core.dll", "resources.assets"):
                ok = sha256(dst) == sha256(src)
            else:
                ok = open(dst, "rb").read() == open(src, "rb").read()
            print("  %-28s %s" % (rel, "OK" if ok else "DIFFERS"))
            if not ok:
                problems += 1
        sums = os.path.join(REL, "SHA256SUMS.txt")
        if os.path.exists(sums):
            txt = open(sums, encoding="utf-8").read()
            for want in (core_hash, assets_hash):
                if want not in txt:
                    print("  SHA256SUMS.txt 缺少 %s" % want[:16]); problems += 1
        ps1 = os.path.join(REL, "install_zh.ps1")
        if os.path.exists(ps1):
            t = open(ps1, encoding="utf-8-sig").read()
            for want in (core_hash, assets_hash):
                if want not in t:
                    print("  install_zh.ps1 缺少哈希常量 %s" % want[:16]); problems += 1
        print("\ncheck: %d problem(s)" % problems)
        return 1 if problems else 0

    # ---- 3. 组装 ----
    for src, rel in PAYLOAD.items():
        dst = os.path.join(REL, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.basename(dst) == "install_zh.ps1":
            raw = open(src, "rb").read()
            bom = raw.startswith(b"\xef\xbb\xbf")
            txt = patch_ps1(raw.decode("utf-8-sig"), core_hash, assets_hash)
            # 与 .gitattributes 的 `*.ps1 text eol=crlf` 保持一致：仓库存储 LF，检出 CRLF。
            # 这里直接写 CRLF，使构建后的工作区与 clone 结果一致（git status 干净）。
            txt = txt.replace("\r\n", "\n").replace("\n", "\r\n")
            open(dst, "wb").write((b"\xef\xbb\xbf" if bom else b"") + txt.encode("utf-8"))
            print("-> install_zh.ps1 (hash constants rewritten, BOM=%s, CRLF)" % bom)
        else:
            shutil.copy2(src, dst)
            print("-> %s" % rel)

    # ---- 4. SHA256SUMS.txt ----
    sums = ["%s  Managed\\Core.dll" % core_hash,
            "%s  resources.assets" % assets_hash]
    open(os.path.join(REL, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(sums) + "\n")
    print("-> SHA256SUMS.txt")

    # ---- 5. 打 zip（排除 .git）----
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(REL):
            # .git 是版本库元数据、.github 是 CI 配置，都不属于给用户的安装包
            dirs[:] = [d for d in dirs if d not in (".git", ".github")]
            for fn in sorted(files):
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, REL))
    print("-> %s (%d B, SHA256 %s)" % (ZIP, os.path.getsize(ZIP), sha256(ZIP)))

    # ---- 6. 自检：解包重算载荷哈希 ----
    print("\nself-check (re-extract from zip)")
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(tmp)
        bad = 0
        for rel, want in (("Managed/Core.dll", core_hash), ("resources.assets", assets_hash)):
            got = sha256(os.path.join(tmp, rel))
            ok = got == want
            bad += 0 if ok else 1
            print("  %-22s %s" % (rel, "OK" if ok else "MISMATCH %s" % got))
        for must in ("README.md", "LICENSE", "NOTICE.md", ".gitattributes",
                     "install_zh.ps1", "SHA256SUMS.txt",
                     "docs/术语保留决策.md", "docs/install_notes.md"):
            ok = os.path.exists(os.path.join(tmp, must))
            bad += 0 if ok else 1
            print("  %-22s %s" % (must, "present" if ok else "MISSING"))
        print("\nself-check: %d problem(s)" % bad)
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
