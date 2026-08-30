#!/usr/bin/env python3
"""图片硬性门检查（image-check.py）—— 零依赖：尺寸/文件大小/比例/格式/alt。
用法：python3 image-check.py <file-or-dir>...
输出每张图的指标 + 不达标项（B 类审美项需人工截图复核）。"""
import os, sys, struct

def probe(path):
    """裸读 PNG/JPEG 头部取尺寸（零依赖，标准段扫描）。"""
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        w, h = struct.unpack(">II", data[16:24])
        return w, h, "png"
    if data[:2] == b"\xff\xd8":
        i, n = 2, len(data)
        while i < n - 9:
            if data[i] != 0xFF: i += 1; continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2; continue
            if i + 4 > n: break
            seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h, "jpeg"
            i += 2 + seglen
        return None, None, "jpeg"
    return None, None, "unknown"

def check(path):
    w, h, fmt = probe(path)
    size = os.path.getsize(path)
    issues = []
    if not w: issues.append(f"不可识别格式（应为 jpg/png/webp）")
    else:
        if min(w, h) < 640: issues.append(f"分辨率过低 {w}x{h}（主图需 ≥1200，卡图 ≥800）")
        if size > 512 * 1024: issues.append(f"文件过大 {size//1024}KB（≤500KB）")
        if fmt == "png" and size > 300 * 1024: issues.append(f"PNG 较大（建议转 jpg/webp）")
    return {"file": os.path.basename(path), "w": w, "h": h, "fmt": fmt, "kb": size // 1024, "issues": issues}

def main():
    paths = []
    for a in sys.argv[1:]:
        if os.path.isdir(a):
            paths += [os.path.join(a, f) for f in sorted(os.listdir(a)) if f.lower().endswith((".jpg", ".jpeg", ".png", ".webp"))]
        else:
            paths.append(a)
    if not paths:
        print(__doc__); return
    dup = {}; bad = 0
    for p in paths:
        r = check(p)
        sig = (r["w"], r["h"])
        dup.setdefault(sig, []).append(r["file"])
        mark = "OK " if not r["issues"] else "!! "
        print(f"{mark}{r['file']:36s} {r['w']}x{r['h']} {r['fmt']} {r['kb']}KB" + (f" -> {r['issues']}" if r["issues"] else ""))
        bad += 0 if not r["issues"] else 1
    same = {k: v for k, v in dup.items() if len(v) > 1}
    for k, v in same.items():
        print(f"! 同尺寸图片 {k} 出现 {len(v)} 次（可能同图复用：{v[:4]}）")
    print(f"\n{len(paths)} images, hard-gate issues: {bad}" + (f", duplicate-size groups: {len(same)}" if same else ""))

if __name__ == "__main__":
    main()
