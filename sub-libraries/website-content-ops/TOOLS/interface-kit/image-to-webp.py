#!/usr/bin/env python3
"""本地图片转 WebP（image-to-webp.py，ISS-143/144）—— 上传前把 PNG/JPG 压成 WebP。

为什么需要：平台原样接受 WebP（实测 ISS-143），而 WebP 通常比 JPG/PNG 小 60–90%，
直接决定页面加载速度。本工具在**本地**完成转换，上传路径不依赖 sharp。

用法：
    python3 image-to-webp.py <file-or-dir>...              # 转换到 <dir>/webp/
    python3 image-to-webp.py --quality 82 <file-or-dir>... # 指定质量（默认 82）
    python3 image-to-webp.py --max-kb 500 <dir>            # 超限自动降质/缩宽
    python3 image-to-webp.py --in-place <dir>              # 输出到源目录同名 .webp

后端优先级（自动探测，缺失不报错）：
    1) cwebp  —— 零 Python 依赖，质量最高，优先
    2) Pillow —— pip 装过即可用，纯 Python 兜底
    3) sharp  —— node 环境（子库 adapter 依赖里已有 0.35.3），最后兜底

退出码：0 全部成功；1 有失败项（逐条打印原因）；2 参数错误。
"""
import os
import shutil
import struct
import subprocess
import sys

DEFAULT_QUALITY = 82
DEFAULT_MAX_KB = 500
INPUT_EXTS = (".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp")


def _which(name):
    return shutil.which(name)


def _backend():
    if _which("cwebp"):
        return "cwebp"
    try:
        import PIL  # noqa: F401
        return "pillow"
    except Exception:
        pass
    if _which("node"):
        try:
            out = subprocess.run(
                [_which("node"), "-e", "import('sharp').then(()=>console.log('ok')).catch(()=>process.exit(1))"],
                capture_output=True, text=True, timeout=30,
            )
            if out.returncode == 0 and "ok" in out.stdout:
                return "sharp"
        except Exception:
            pass
    return None


def convert_cwebp(src, dst, quality, width=None):
    # M7：EXIF 方向必须与 Pillow/sharp 一致——若源带方向标记且 Pillow 可用，
    # 先旋正到临时 PNG 再交给 cwebp；否则回退保留原 EXIF（至少不丢信息）。
    src_for_cwebp = src
    try:
        from PIL import Image, ImageOps
        with Image.open(src) as im:
            if im.getexif().get(274):
                rotated = ImageOps.exif_transpose(im)
                if rotated is not None:
                    tmp_src = f"{src}.exifrot.png"
                    rotated.convert("RGB").save(tmp_src, "PNG")
                    src_for_cwebp = tmp_src
    except Exception:
        pass
    cmd = [_which("cwebp"), "-q", str(quality), "-m", "4", "-quiet"]
    if src_for_cwebp == src:
        cmd += ["-metadata", "all"]
    if width:
        cmd += ["-resize", str(width), "0"]
    cmd += [src_for_cwebp, "-o", dst]
    try:
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            raise RuntimeError((r.stderr or r.stdout or "cwebp failed").strip()[:200])
    finally:
        if src_for_cwebp != src and os.path.exists(src_for_cwebp):
            os.remove(src_for_cwebp)


def convert_pillow(src, dst, quality, width=None):
    from PIL import Image, ImageOps
    with Image.open(src) as im:
        if getattr(im, "is_animated", False) and getattr(im, "n_frames", 1) > 1:
            raise RuntimeError(f"动画 WebP 不受支持（{im.n_frames} 帧），会被压成单帧；请保留原文件")
        # exif_transpose：按 EXIF 方向旋正，与 sharp 的 .rotate() 行为对齐（M7）
        im = ImageOps.exif_transpose(im) or im
        im = im.convert("RGBA" if im.mode in ("RGBA", "LA", "P") else "RGB")
        if width and im.width > width:
            im = im.resize((width, max(1, round(im.height * width / im.width))), Image.LANCZOS)
        im.save(dst, "WEBP", quality=quality, method=4)


def convert_sharp(src, dst, quality, width=None):
    code = (
        "import sharp from 'sharp';"
        "let p=sharp(process.argv[1]).rotate();"
        "if(process.argv[4]&&process.argv[4]!=='0')p=p.resize({width:Number(process.argv[4]),withoutEnlargement:true});"
        "await p.webp({quality:Number(process.argv[3]),effort:4}).toFile(process.argv[2]);"
    )
    r = subprocess.run([_which("node"), "--input-type=module", "-e", code, src, dst,
                        str(quality), str(width or 0)],
                       capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or "sharp failed").strip()[:200])


CONVERTERS = {"cwebp": convert_cwebp, "pillow": convert_pillow, "sharp": convert_sharp}


def _image_width(src, backend):
    """取源图宽度（M3：零依赖头部解析优先，Pillow 兜底——任一后端可用即可缩宽）。

    cwebp 没有 -get 子命令（实测 Unknown option），故按文件头解析 PNG/JPEG/WebP。
    """
    try:
        with open(src, "rb") as f:
            data = f.read(65536)
        if data[:8] == b"\x89PNG\r\n\x1a\n":
            return struct.unpack(">I", data[16:20])[0]
        if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
            fmt = data[12:16]
            if fmt == b"VP8X":
                return int.from_bytes(data[24:27], "little") + 1
            if fmt == b"VP8 ":
                return int.from_bytes(data[26:28], "little") & 0x3FFF
            if fmt == b"VP8L":
                bits = int.from_bytes(data[21:25], "little")
                return (bits & 0x3FFF) + 1
        if data[:2] == b"\xff\xd8":
            i, n = 2, len(data)
            while i < n - 9:
                if data[i] != 0xFF:
                    i += 1
                    continue
                marker = data[i + 1]
                if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                    i += 2
                    continue
                if i + 4 > n:
                    break
                seglen = struct.unpack(">H", data[i + 2:i + 4])[0]
                if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                    h, w = struct.unpack(">HH", data[i + 5:i + 9])
                    return w
                i += 2 + seglen
    except Exception:
        pass
    try:
        from PIL import Image as _Img
        with _Img.open(src) as im:
            return im.width
    except Exception:
        return None


def collect(paths):
    """递归收集（M1：嵌套素材目录不能静默漏转）。已存在 webp/ 输出目录会被跳过，避免自我递归。"""
    out = []
    for p in paths:
        if os.path.isdir(p):
            for root, dirs, names in os.walk(p):
                dirs[:] = [d for d in dirs if d not in ("webp", "__pycache__")]
                for name in sorted(names):
                    if name.lower().endswith(INPUT_EXTS):
                        out.append(os.path.join(root, name))
        elif os.path.isfile(p):
            out.append(p)
    return out


def main():
    args = sys.argv[1:]
    if not args or "-h" in args or "--help" in args:
        print(__doc__)
        return 2

    quality = DEFAULT_QUALITY
    max_kb = DEFAULT_MAX_KB
    in_place = False
    paths = []
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("--quality", "--max-kb"):
            if i + 1 >= len(args):
                print(f"参数错误：{a} 缺少数值"); print(__doc__); return 2
            try:
                val = int(args[i + 1])
            except ValueError:
                print(f"参数错误：{a} 需要整数，得到 {args[i + 1]!r}"); return 2
            if a == "--quality":
                quality = val
            else:
                max_kb = val
            i += 2; continue
        if a == "--in-place":
            in_place = True; i += 1; continue
        paths.append(a); i += 1

    files = collect(paths)
    if not files:
        print("没有找到可转换的图片（支持 png/jpg/jpeg/webp/tif/bmp）")
        return 2

    backend = _backend()
    if not backend:
        print("FAIL: 未找到任何转换后端。安装任一即可：")
        print("  brew install webp           # cwebp（推荐）")
        print("  python3 -m pip install Pillow")
        print("  cd <adapter> && npm install # sharp")
        return 1

    print(f"BACKEND: {backend} | QUALITY: {quality} | MAX: {max_kb}KB | FILES: {len(files)}")
    failures = 0
    used_dst = set()
    for src in files:
        # M8：单条坏输入不能中断整批——所有路径/IO 操作都在 per-file try 内
        try:
            stem = os.path.splitext(os.path.basename(src))[0]
            src_dir = os.path.dirname(src) or "."
            out_dir = src_dir if in_place else os.path.join(src_dir, "webp")
            os.makedirs(out_dir, exist_ok=True)
            before = os.path.getsize(src)

            # 已是达标 webp：直接跳过（M10：不参与消歧，避免 --in-place 二次运行多出副本）
            if src.lower().endswith(".webp") and before <= max_kb * 1024:
                print(f"  SKIP  {os.path.basename(src)}  已是 webp 且 {before // 1024}KB ≤ {max_kb}KB")
                continue

            # M10：--in-place 幂等——同目录已有同名 .webp（上一轮产物）时跳过，
            # 否则消歧逻辑会生成 photo-2.webp 这类副本。
            if in_place:
                sibling = os.path.join(src_dir, stem + ".webp")
                if os.path.exists(sibling) and os.path.abspath(sibling) != os.path.abspath(src):
                    print(f"  SKIP  {os.path.basename(src)}  同目录已有 {os.path.basename(sibling)}（幂等跳过）")
                    continue

            # B1/B2：目标路径分配——循环递增后缀，直到磁盘与本次运行都未占用
            dst = os.path.join(out_dir, stem + ".webp")
            n = 2
            while (os.path.abspath(dst) != os.path.abspath(src)
                   and (dst in used_dst or os.path.exists(dst))):
                dst = os.path.join(out_dir, f"{stem}-{n}.webp")
                n += 1
            if in_place and os.path.abspath(dst) == os.path.abspath(src):
                print(f"  FAIL  {os.path.basename(src)}  --in-place 不能覆盖源文件本身；请去掉 --in-place 或换目录")
                failures += 1
                continue
            used_dst.add(dst)

            # M4：写临时文件，成功且达标后原子替换，失败不留半成品
            tmp = dst + ".tmp"
            q = quality
            try:
                CONVERTERS[backend](src, tmp, q)
                while os.path.getsize(tmp) > max_kb * 1024 and q - 8 >= 40:
                    q -= 8
                    CONVERTERS[backend](src, tmp, q)
                if os.path.getsize(tmp) > max_kb * 1024:
                    w0 = _image_width(src, backend)
                    if w0:
                        for w in (2400, 2000, 1600, 1280,
                                  int(w0 * 0.8), int(w0 * 0.6), 800):
                            if not w or w >= w0:
                                continue
                            CONVERTERS[backend](src, tmp, q, width=w)
                            if os.path.getsize(tmp) <= max_kb * 1024:
                                break
                after = os.path.getsize(tmp)
                if after > before:
                    # M9：转后变大——删掉输出，保留原格式（不再产出更大的 webp）
                    os.remove(tmp)
                    print(f"  SKIP  {os.path.basename(src)}  转 WebP 反而变大（{before // 1024}KB → "
                          f"{after // 1024}KB），保留原格式")
                    continue
                os.replace(tmp, dst)
            except Exception:
                if os.path.exists(tmp):
                    os.remove(tmp)
                raise
            saved = (1 - after / before) * 100 if before else 0
            flag = "" if after <= max_kb * 1024 else f"  ⚠ 仍超 {max_kb}KB（已降到 q={q}）"
            print(f"  OK    {os.path.basename(src)}  {before // 1024}KB → {after // 1024}KB"
                  f"  ({saved:+.0f}%, q={q}){flag}")
        except Exception as e:
            failures += 1
            print(f"  FAIL  {os.path.basename(src)}  {type(e).__name__}: {e}")
    print(f"RESULT: {len(files) - failures}/{len(files)} 成功")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
