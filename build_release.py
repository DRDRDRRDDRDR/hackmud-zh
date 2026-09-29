# -*- coding: utf-8 -*-
"""build_release.py — 可复现地组装公开仓库内容（hackmud-zh/release/）并打出分发包。

为什么需要它：发布目录里的安装脚本内嵌了载荷的 SHA256 常量。只要载荷变一次，
就必须同步更新该常量 + SHA256SUMS.txt + zip，三者任一漏改，用户装完就会看到"校验失败"。
本脚本把这一步固化成一条命令，避免手工漏改。

真源（recon/）：
    Core_zh.dll              汉化后的主程序集
    resources_zh.assets      含中文字形的字体资产
    sharedassets0_zh.assets  含中文开场自检文字的资产
模板：
    recon/install_zh.ps1      安装脚本模板（__HASH_n__ / __ORIG_n__ 占位符会被回填）
    recon/decision_status_vs_sec.md -> docs/术语保留决策.md

用法:
    python build_release.py            # 组装 release/ 并重建 dist/hackmud-zh-vX.zip
    python build_release.py --check    # 只校验，不写盘
"""
import os, re, sys, hashlib, shutil, zipfile

ROOT = r"C:\Users\DR\Downloads\DSH\hackmud-zh"
RECON = os.path.join(ROOT, "recon")
REL = os.path.join(ROOT, "release")
DIST = os.path.join(ROOT, "dist")
TEMPLATE_PS1 = os.path.join(RECON, "install_zh.ps1")

VERSION = "1.1.0"
ZIP = os.path.join(DIST, "hackmud-zh-v%s.zip" % VERSION)

# 载荷清单：顺序必须与 install_zh.ps1 的 $Files 表一致
# (release 内相对路径, recon 真源文件名, 原版 SHA256)
PAYLOADS = [
    ("Managed/Core.dll",      "Core_zh.dll",
     "D424EAB9372946946B5FFD9DC49B17D9C5060B3CEC638A5952E7EAD99CD696E6"),
    ("resources.assets",      "resources_zh.assets",
     "E2E661C96397F9C444936B9767F7F723B5FDAF64FC4ECB04B52E7D5B678C0003"),
    ("sharedassets0.assets",  "sharedassets0_zh.assets",
     "E07F027F18A41DB03E387DF729DB77D933AC1B0593826640A4E91FE6E7709D9B"),
]

# 其余需要随包分发的文件（不改内容，原样复制）
EXTRA = [
    (os.path.join(RECON, "decision_status_vs_sec.md"), "docs/术语保留决策.md"),
    (os.path.join(DIST, "hackmud_zh_patch", "install_notes.md"), "docs/install_notes.md"),
    (TEMPLATE_PS1, "install_zh.ps1"),
]


def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest().upper()


def payload_hashes():
    return [(rel, sha256(os.path.join(RECON, src)), orig) for rel, src, orig in PAYLOADS]


def patch_ps1(text):
    """按实际载荷回填 __HASH_n__ / __ORIG_n__ 占位符；有剩余占位符即报错。"""
    for i, (rel, h, orig) in enumerate(payload_hashes()):
        for token, val in (("__HASH_%d__" % i, h), ("__ORIG_%d__" % i, orig)):
            text, n = re.subn(re.escape(token), val, text)
            if n != 1:
                raise SystemExit("!! install_zh.ps1 中 %s 出现 %d 次（应为 1）" % (token, n))
    left = re.findall(r"__(?:HASH|ORIG)_\d+__", text)
    if left:
        raise SystemExit("!! 仍有未回填的占位符: %s" % left)
    return text


def main():
    check_only = "--check" in sys.argv

    # ---- 1. 前置检查 ----
    missing = [os.path.join(RECON, s) for _, s, _ in PAYLOADS if not os.path.exists(os.path.join(RECON, s))]
    missing += [s for s, _ in EXTRA if not os.path.exists(s)]
    if missing:
        for m in missing:
            print("!! 真源缺失:", m)
        return 1

    ph = payload_hashes()
    print("payload hashes")
    for rel, h, orig in ph:
        print("  %-24s %s" % (rel, h))

    # ---- 2. --check：只比对现状 ----
    if check_only:
        problems = 0
        for rel, h, orig in ph:
            dst = os.path.join(REL, rel)
            if not os.path.exists(dst):
                print("  MISSING in release/: %s" % rel); problems += 1; continue
            got = sha256(dst)
            print("  %-28s %s" % (rel, "OK" if got == h else "DIFFERS (release %s)" % got[:16]))
            if got != h:
                problems += 1
        sums = os.path.join(REL, "SHA256SUMS.txt")
        if os.path.exists(sums):
            txt = open(sums, encoding="utf-8").read()
            for rel, h, _ in ph:
                if h not in txt:
                    print("  SHA256SUMS.txt 缺少 %s 的哈希" % rel); problems += 1
        else:
            print("  SHA256SUMS.txt 不存在"); problems += 1
        ps1 = os.path.join(REL, "install_zh.ps1")
        if os.path.exists(ps1):
            t = open(ps1, encoding="utf-8-sig").read()
            for rel, h, orig in ph:
                if h not in t:
                    print("  install_zh.ps1 缺少 %s 的补丁哈希常量" % rel); problems += 1
                if orig not in t:
                    print("  install_zh.ps1 缺少 %s 的原版哈希常量" % rel); problems += 1
            if "__HASH_0__" in t or "__ORIG_0__" in t:
                print("  install_zh.ps1 仍有未回填占位符"); problems += 1
        else:
            print("  install_zh.ps1 不存在"); problems += 1
        print("\ncheck: %d problem(s)" % problems)
        return 1 if problems else 0

    # ---- 3. 组装载荷 ----
    for rel, h, orig in ph:
        src = os.path.join(RECON, [s for r, s, o in PAYLOADS if r == rel][0])
        dst = os.path.join(REL, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        shutil.copy2(src, dst)
        print("-> %s" % rel)

    # ---- 4. 其余文件（安装脚本需回填哈希）----
    for src, rel in EXTRA:
        dst = os.path.join(REL, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.basename(dst) == "install_zh.ps1":
            raw = open(src, "rb").read()
            txt = patch_ps1(raw.decode("utf-8-sig"))
            # 与 .gitattributes 的 `*.ps1 text eol=crlf` 保持一致
            txt = txt.replace("\r\n", "\n").replace("\n", "\r\n")
            # Windows PowerShell 5.1 读 UTF-8 无 BOM 会按系统 ANSI(GBK) 解码 -> 中文乱码甚至语法报错。
            # 这里【强制】写 BOM，不依赖模板文件自身是否带 BOM。
            open(dst, "wb").write(b"\xef\xbb\xbf" + txt.encode("utf-8"))
            print("-> install_zh.ps1 (hashes filled, BOM=forced, CRLF)")
        else:
            shutil.copy2(src, dst)
            print("-> %s" % rel)

    # ---- 5. SHA256SUMS.txt ----
    sums = ["%s  %s" % (h, rel.replace("/", "\\")) for rel, h, _ in ph]
    open(os.path.join(REL, "SHA256SUMS.txt"), "w", encoding="utf-8", newline="\n").write(
        "\n".join(sums) + "\n")
    print("-> SHA256SUMS.txt")

    # ---- 6. 打 zip ----
    if os.path.exists(ZIP):
        os.remove(ZIP)
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for root, dirs, files in os.walk(REL):
            dirs[:] = [d for d in dirs if d not in (".git", ".github")]
            for fn in sorted(files):
                p = os.path.join(root, fn)
                z.write(p, os.path.relpath(p, REL))
    print("-> %s (%d B, SHA256 %s)" % (ZIP, os.path.getsize(ZIP), sha256(ZIP)))

    # ---- 7. 自检 ----
    print("\nself-check (re-extract from zip)")
    import tempfile
    tmp = tempfile.mkdtemp()
    try:
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(tmp)
        bad = 0
        for rel, h, _ in ph:
            got = sha256(os.path.join(tmp, rel))
            ok = got == h
            bad += 0 if ok else 1
            print("  %-24s %s" % (rel, "OK" if ok else "MISMATCH %s" % got))
        for must in ("README.md", "LICENSE", "NOTICE.md", ".gitattributes",
                     "install_zh.ps1", "SHA256SUMS.txt",
                     "docs/术语保留决策.md", "docs/install_notes.md"):
            ok = os.path.exists(os.path.join(tmp, must))
            bad += 0 if ok else 1
            print("  %-24s %s" % (must, "present" if ok else "MISSING"))
        print("\nself-check: %d problem(s)" % bad)
        return 1 if bad else 0
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
