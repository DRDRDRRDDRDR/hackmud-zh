# -*- coding: utf-8 -*-
"""ci_selftest.py — 反向自检：证明 verify_package.py 的判据不是"永远绿"的。

做法：把发布包复制到临时目录，逐项人为破坏，再以子进程调用 verify_package.py，
断言它**必须失败**。同时先跑一次未破坏的，断言它必须通过。

任一项行为不符（破坏后仍通过 / 未破坏却失败）即整体失败。
用法: python ci_selftest.py
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VERIFIER = os.path.join(HERE, "verify_package.py")


def run_verifier(target):
    """返回 (returncode, stdout)。"""
    p = subprocess.run([sys.executable, VERIFIER, target],
                       capture_output=True, text=True,
                       encoding="utf-8", errors="replace")
    return p.returncode, (p.stdout or "") + (p.stderr or "")


def copy_package():
    tmp = tempfile.mkdtemp(prefix="hz-selftest-")
        # 只复制包内容，跳过版本库与 CI 配置
    def ignore(d, names):
        return [n for n in names if n in (".git", ".github", "__pycache__")]
    dest = os.path.join(tmp, "pkg")
    shutil.copytree(HERE, dest, ignore=ignore)
    return tmp, dest


# ---- 各破坏手法 ----

def tamper_payload(d):
    p = os.path.join(d, "Managed", "Core.dll")
    b = bytearray(open(p, "rb").read())
    b[len(b) // 2] ^= 0xFF
    open(p, "wb").write(bytes(b))
    return "翻转 Managed/Core.dll 中间一个字节"


def tamper_ps1_constant(d):
    p = os.path.join(d, "install_zh.ps1")
    s = open(p, encoding="utf-8-sig").read()
    # 表格格式：Patch = "<64位十六进制>"；把第一处改成全 0
    s2, n = re.subn(r'(Patch\s*=\s*")[0-9A-Fa-f]{64}',
                    lambda m: m.group(1) + "0" * 64, s, count=1)
    assert n == 1 and s2 != s, "替换未发生"
    open(p, "w", encoding="utf-8-sig").write(s2)
    return "把 install_zh.ps1 表格里第一个 Patch 哈希改成全 0"


def strip_bom(d):
    p = os.path.join(d, "install_zh.ps1")
    b = open(p, "rb").read()
    assert b[:3] == b"\xef\xbb\xbf", "预期有 BOM"
    open(p, "wb").write(b[3:])
    return "去掉 install_zh.ps1 的 UTF-8 BOM"


def tamper_sums(d):
    p = os.path.join(d, "SHA256SUMS.txt")
    lines = open(p, encoding="utf-8").read().splitlines()
    out = []
    for ln in lines:
        m = re.match(r"^([0-9A-Fa-f]{64})(\s+.*)$", ln)
        out.append(("0" * 64 + m.group(2)) if m else ln)
    open(p, "w", encoding="utf-8").write("\n".join(out) + "\n")
    return "篡改 SHA256SUMS.txt 里的声明哈希"


def drop_required(d):
    os.remove(os.path.join(d, "NOTICE.md"))
    return "删除必备文件 NOTICE.md"


def revert_asset_text(d):
    """把 level0 里一条已汉化的串改回英文 —— 模拟「资产被从原版重建，中文被冲掉」。"""
    p = os.path.join(d, "level0")
    b = open(p, "rb").read()
    zh = "-正在运行自检-".encode("utf-8")
    en = "-running self diagnostics-".encode("utf-8")
    assert zh in b, "预期 level0 已含该中文串"
    zhpad = zh + b" " * (len(en) - len(zh))
    assert zhpad in b, "预期中文串带尾部空格补齐"
    b2 = b.replace(zhpad, en)
    assert b2 != b, "替换未发生"
    assert len(b2) == len(b), "长度应保持不变"
    open(p, "wb").write(b2)
    return "把 level0 的『正在运行自检』改回英文（模拟资产回退）"


NEGATIVES = [tamper_payload, tamper_ps1_constant, strip_bom, tamper_sums,
             drop_required, revert_asset_text]


def main():
    problems = 0

    # --- 正向：未破坏必须通过 ---
    print("[positive] 未破坏的包必须通过")
    rc, out = run_verifier(HERE)
    if rc == 0:
        print("  ok    verify_package.py 返回 0")
    else:
        problems += 1
        print("  FAIL  未破坏的包竟然校验失败（rc=%d）" % rc)
        print("        " + "\n        ".join(out.strip().splitlines()[-8:]))

    # --- 反向：每种破坏都必须被检出 ---
    print("\n[negative] 每种人为破坏都必须被检出")
    for fn in NEGATIVES:
        tmp, dest = copy_package()
        try:
            what = fn(dest)
            rc, out = run_verifier(dest)
            if rc != 0:
                print("  ok    已检出: %s (rc=%d)" % (what, rc))
            else:
                problems += 1
                print("  FAIL  未被检出: %s —— 判据是空的" % what)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)

    print("\n== ci_selftest 结果: %d 项不符合预期 ==" % problems)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
