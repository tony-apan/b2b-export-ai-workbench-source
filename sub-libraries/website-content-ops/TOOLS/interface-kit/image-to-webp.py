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
    cmd = [_which("cwebp"), "-q", str(quality), "-m", "4", "-quiet"]
    if width:
        cmd += ["-resize", str(width), "0"]
    cmd += [src, "-o", dst]
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError((r.stderr or r.stdout or "cwebp failed").strip()[:200])


def convert_pillow(src, dst, quality, width=None):
    from PIL import Image
    with Image.open(src) as im:
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


def collect(paths):
    out = []
    for p in paths:
        if os.path.isdir(p):
            for name in sorted(os.listdir(p)):
                if name.lower().endswith(INPUT_EXTS):
                    out.append(os.path.join(p, name))
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
        if a == "--quality":
            quality = int(args[i + 1]); i += 2; continue
        if a == "--max-kb":
            max_kb = int(args[i + 1]); i += 2; continue
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
    seen = {}
    for src in files:
        stem = os.path.splitext(os.path.basename(src))[0]
        out_dir = os.path.dirname(src) if in_place else os.path.join(os.path.dirname(src), "webp")
        os.makedirs(out_dir, exist_ok=True)
        # 同名不同扩展名（photo.png + photo.jpg）会互相覆盖：后者追加源扩展名区分
        key = os.path.join(out_dir, stem)
        if key in seen:
            stem = f"{stem}-{os.path.splitext(os.path.basename(src))[1].lstrip('.')}"
        seen[key] = True
        dst = os.path.join(out_dir, stem + ".webp")
        before = os.path.getsize(src)
        if src.lower().endswith(".webp") and before <= max_kb * 1024:
            if os.path.abspath(src) != os.path.abspath(dst):
                shutil.copy2(src, dst)
            print(f"  SKIP  {os.path.basename(src)}  已是 webp 且 {before // 1024}KB ≤ {max_kb}KB")
            continue
        q = quality
        try:
            CONVERTERS[backend](src, dst, q)
            # 超限先降质（每次 -8，下限 40），仍超再缩宽（最多 3 档，对齐 sharp 双轴策略）
            while os.path.getsize(dst) > max_kb * 1024 and q > 40:
                q -= 8
                CONVERTERS[backend](src, dst, q)
            if os.path.getsize(dst) > max_kb * 1024:
                from PIL import Image as _Img
                with _Img.open(src) as _im:
                    w0 = _im.width
                for w in (2400, 2000, 1600, 1280):
                    if w >= w0:
                        continue
                    CONVERTERS[backend](src, dst, q, width=w)
                    if os.path.getsize(dst) <= max_kb * 1024:
                        break
            after = os.path.getsize(dst)
            saved = (1 - after / before) * 100 if before else 0
            flag = "" if after <= max_kb * 1024 else f"  ⚠ 仍超 {max_kb}KB（已降到 q={q}）"
            if after > before:
                flag += "  ⚠ 比原图大，建议保留原格式"
            print(f"  OK    {os.path.basename(src)}  {before // 1024}KB → {after // 1024}KB"
                  f"  (-{saved:.0f}%, q={q}){flag}")
        except Exception as e:
            failures += 1
            print(f"  FAIL  {os.path.basename(src)}  {type(e).__name__}: {e}")
    print(f"RESULT: {len(files) - failures}/{len(files)} 成功")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
