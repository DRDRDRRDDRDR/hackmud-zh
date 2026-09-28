# -*- coding: utf-8 -*-
"""audit_protocol.py — 断言：没有任何"已翻译的字面量"流进网络/协议 API。

这条闸门的由来（真实事故，2026-09-28）：
    客户端执行  www.SetRequestHeader("Authorization", "Token token=\\"" + token + "\\"")
    我们把 "Token token=\\"" 译成了中文。Unity 的 SetRequestHeader 拒绝含非 ASCII 的
    header 值，抛 InvalidOperationException: Header value contains invalid characters，
    所有鉴权请求失败 —— 症状是终端一直"命令执行超时。请重试。"、登录进不去。

教训：判断一个字符串能否翻译，**不能看它是否被 Concat 拼接**（拼接也可能是在拼协议串），
必须看它的**消费方 API**。本脚本按消费方扫描，是这条判据的自动化守卫。

注意：本脚本自带 #US 堆解析（不依赖 dnfile 的 UserStringHeap API，那套在这里不好用），
并配有反向自检 —— 见 ci_selftest.py 的 protocol-neg 用例，确保闸门不是空的。

依赖: pip install dnfile dncil
用法: python audit_protocol.py [Core.dll 路径]
"""
import os
import re
import struct
import sys

try:
    import dnfile
    from dncil.cil.body import CilMethodBody
    from dncil.cil.body.reader import CilMethodBodyReaderBase
except ImportError:
    print("SKIP: 需要 dnfile / dncil（pip install dnfile dncil）")
    sys.exit(0)

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT = os.path.join(HERE, "Managed", "Core.dll")

# 网络/协议消费方：owner 或 member 命中即视为"协议上下文"
NET = re.compile(
    r"UnityEngine\.Networking|UnityEngine\.WWW|System\.Net|WebSocket|Socket|"
    r"HttpWebRequest|WebClient|SetRequestHeader|set_url|get_url|SendWebRequest|"
    r"UploadHandler|DownloadHandler", re.I)

BACK, FWD = 8, 3          # 在调用点前后多少条指令内找 ldstr


# ---------------- PE / #US 堆解析（自实现，已验证） ----------------
def parse_pe(path):
    data = open(path, "rb").read()
    e = struct.unpack_from("<I", data, 0x3C)[0]
    coff = e + 4
    nsec = struct.unpack_from("<H", data, coff + 2)[0]
    optsz = struct.unpack_from("<H", data, coff + 16)[0]
    opt = coff + 20
    plus = struct.unpack_from("<H", data, opt)[0] == 0x20B
    ddoff = opt + (112 if plus else 96)
    cli_rva = struct.unpack_from("<II", data, ddoff + 14 * 8)[0]
    secs = []
    base = opt + optsz
    for i in range(nsec):
        b = base + i * 40
        vsz, vaddr, rsz, raddr = struct.unpack_from("<IIII", data, b + 8)
        secs.append((vaddr, vsz, raddr, rsz))
    return data, secs, cli_rva


def rva2off(secs, rva):
    for vaddr, vsz, raddr, rsz in secs:
        if vaddr <= rva < vaddr + max(vsz, rsz):
            return raddr + (rva - vaddr)
    return None


def read_cblob(data, off):
    b0 = data[off]
    if b0 & 0x80 == 0:
        return b0, off + 1
    if b0 & 0xC0 == 0x80:
        return ((b0 & 0x3F) << 8) | data[off + 1], off + 2
    return (((b0 & 0x1F) << 24) | (data[off + 1] << 16) |
            (data[off + 2] << 8) | data[off + 3]), off + 4


def us_map(path):
    """返回 {堆内相对偏移: 字符串}"""
    data, secs, cli_rva = parse_pe(path)
    cli = rva2off(secs, cli_rva)
    md_rva = struct.unpack_from("<II", data, cli + 8)[0]
    md = rva2off(secs, md_rva)
    ver_len = struct.unpack_from("<I", data, md + 12)[0]
    p = md + 16 + ver_len + 2
    nstreams = struct.unpack_from("<H", data, p)[0]
    p += 2
    st = {}
    for _ in range(nstreams):
        off, size = struct.unpack_from("<II", data, p)
        p += 8
        end = data.index(b"\x00", p)
        st[data[p:end].decode("ascii")] = (md + off, size)
        p = (end + 1 + 3) & ~3
    heap_off, heap_size = st["#US"]
    out, p, end = {}, heap_off + 1, heap_off + heap_size
    while p < end:
        rel = p - heap_off
        ln, q = read_cblob(data, p)
        if ln == 0:
            p = q
            continue
        blen = ln - 1
        raw = data[q:q + blen]
        out[rel] = (raw.decode("utf-16le", "replace") if blen % 2 == 0
                    else raw[:-1].decode("utf-16le", "replace"))
        p = q + blen
        if p < end and data[p] == 0x01 and blen % 2 == 0:
            p += 1
    return out


class Rd(CilMethodBodyReaderBase):
    def __init__(s, pe, row):
        s.pe = pe
        s.offset = pe.get_offset_from_rva(row.Rva)

    def read(s, n):
        d = s.pe.get_data(s.pe.get_rva_from_offset(s.offset), n)
        s.offset += n
        return d

    def tell(s):
        return s.offset

    def seek(s, o):
        s.offset = o
        return s.offset


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else DEFAULT
    if not os.path.exists(path):
        print("FAIL: 找不到 %s" % path)
        return 1
    print("audit_protocol: %s" % path)

    heap = us_map(path)
    print("  #US 条目: %d" % len(heap))
    if len(heap) < 100:
        # 解析失败时绝不放行 —— 空闸门比没有闸门更危险
        print("  FAIL  #US 解析异常（条目数 %d 过少），拒绝放行" % len(heap))
        return 1

    pe = dnfile.dnPE(path)
    md = pe.net.mdtables

    def resolve(tok):
        try:
            v = int(getattr(tok, "value", tok))
        except Exception:
            return (None, None)
        tbl, rid = v >> 24, v & 0xFFFFFF
        try:
            if tbl == 0x0A:
                r = md.MemberRef.rows[rid - 1]
                row = getattr(r.Class, "row", None)
                o = "%s.%s" % (str(getattr(row, "TypeNamespace", "")),
                               str(getattr(row, "Name", ""))) if row is not None else "?"
                return (o, str(r.Name))
            if tbl == 0x06:
                return ("(MethodDef)", str(md.MethodDef.rows[rid - 1].Name))
        except Exception:
            pass
        return (None, None)

    sites = 0
    literals_checked = 0
    bad = []
    for i, row in enumerate(md.MethodDef.rows):
        if not row or getattr(row, "Rva", 0) == 0:
            continue
        try:
            ins = CilMethodBody(Rd(pe, row)).instructions
        except Exception:
            continue
        for j, it in enumerate(ins):
            if getattr(it.opcode, "name", "") not in ("call", "callvirt", "newobj"):
                continue
            o, m = resolve(it.operand)
            if not m or not NET.search((o or "") + "::" + m):
                continue
            sites += 1
            for k in ins[max(0, j - BACK):min(len(ins), j + FWD + 1)]:
                if getattr(k.opcode, "name", "") != "ldstr":
                    continue
                try:
                    off = int(getattr(k.operand, "value", k.operand)) & 0xFFFFFF
                except Exception:
                    continue
                s = heap.get(off)
                if s is None:
                    continue
                literals_checked += 1
                if s and any(ord(c) > 127 for c in s):
                    bad.append((i, str(row.Name), o, m, s))

    print("  网络/协议调用点: %d" % sites)
    print("  检视字面量: %d" % literals_checked)
    if sites == 0 or literals_checked == 0:
        print("\n  FAIL  没有检视到任何字面量 —— 闸门是空的，拒绝放行")
        return 1

    if bad:
        print("\n  FAIL  以下字面量含非 ASCII，却流进了网络/协议 API：")
        seen = set()
        for (mi, mn, o, m, s) in bad:
            key = (s, o, m)
            if key in seen:
                continue
            seen.add(key)
            print("    method#%-6d %-20s  %s::%s" % (mi, mn[:20], o, m))
            print("        字面量: %r" % s)
        print("\n  修法：把该字符串加入禁译清单、保持英文（recon/protocol_denylist.json）")
        return 1

    print("\n  ok    没有非 ASCII 字面量流入网络/协议 API")
    return 0


if __name__ == "__main__":
    sys.exit(main())
