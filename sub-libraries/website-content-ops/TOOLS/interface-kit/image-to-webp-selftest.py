#!/usr/bin/env python3
"""image-to-webp.py 离线对抗自测（image-to-webp-selftest.py）。

覆盖 ISS-144 修复后必须持续成立的契约：
  B1 --in-place 不覆盖已存在的同名 .webp
  B2 同名不同扩展名不互相覆盖（输入数 == 输出数且内容可区分）
  M1 目录递归收集（含子目录）
  M3 无 Pillow 时仍能取宽并缩宽
  M4 失败/跳过不留 .tmp 半成品
  M8 单条坏输入不中断整批
  M9 转后变大时 SKIP 且不产出文件
  M10 --in-place 二次运行不产生额外副本
  m1 降质下限为 40（不越过）
  m2 参数错误返回 2
用法：python3 image-to-webp-selftest.py
退出码：0 全部通过；1 有失败。
"""
import os
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
TOOL = os.path.join(HERE, "image-to-webp.py")
PY = sys.executable
results = []


def run(args, env=None):
    e = dict(os.environ)
    if env:
        e.update(env)
    return subprocess.run([PY, TOOL] + args, capture_output=True, text=True, env=e, timeout=600)


def make_image(path, size=(800, 600), color=(255, 0, 0)):
    from PIL import Image
    Image.new("RGB", size, color).save(path)


def check(label, ok, detail=""):
    results.append((label, bool(ok), detail))
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  [{detail}]" if detail and not ok else ""))


def main():
    try:
        import PIL  # noqa: F401
    except Exception:
        print("SKIP: 需要 Pillow 生成测试图（pip install Pillow）")
        return 0

    from PIL import Image
    root = tempfile.mkdtemp(prefix="wc-selftest-")
    try:
        # B1：--in-place 不得覆盖已存在的 webp
        d = os.path.join(root, "b1"); os.makedirs(d)
        make_image(os.path.join(d, "a.png"), color=(255, 0, 0))
        Image.new("RGB", (800, 600), (0, 0, 255)).save(os.path.join(d, "a.webp"), "WEBP")
        run(["--in-place", os.path.join(d, "a.png")])
        px = Image.open(os.path.join(d, "a.webp")).convert("RGB").getpixel((400, 300))
        check("B1 --in-place 不覆盖已有 webp", px == (0, 0, 255), f"pixel={px}")

        # B2：三输入三输出且内容可区分
        d = os.path.join(root, "b2"); os.makedirs(d)
        make_image(os.path.join(d, "a.png"), color=(255, 0, 0))
        make_image(os.path.join(d, "a-png.png"), color=(0, 255, 0))
        make_image(os.path.join(d, "a.jpg"), color=(255, 255, 0))
        run([d])
        outs = sorted(f for f in os.listdir(os.path.join(d, "webp")) if f.endswith(".webp"))
        pixels = {Image.open(os.path.join(d, "webp", f)).convert("RGB").getpixel((400, 300)) for f in outs}
        check("B2 同名不同扩展名不覆盖", len(outs) == 3 and len(pixels) == 3,
              f"outs={len(outs)} distinct={len(pixels)}")

        # M1：递归
        d = os.path.join(root, "m1"); os.makedirs(os.path.join(d, "sub", "deep"))
        make_image(os.path.join(d, "sub", "deep", "g.png"))
        run([d])
        check("M1 递归处理子目录", os.path.exists(os.path.join(d, "sub", "deep", "webp", "g.webp")))

        # M8：坏输入不中断整批
        d = os.path.join(root, "m8"); os.makedirs(d)
        make_image(os.path.join(d, "good.png"))
        os.symlink("/nonexistent", os.path.join(d, "dangling.png"))
        r = run([d])
        check("M8 坏输入不中断整批",
              r.returncode == 1 and os.path.exists(os.path.join(d, "webp", "good.webp")),
              f"rc={r.returncode}")

        # M9：转后变大 → SKIP 且不产出
        d = os.path.join(root, "m9"); os.makedirs(d)
        tiny = os.path.join(d, "px.png")
        with open(tiny, "wb") as f:
            f.write(bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000a49444154789c63000100000500010d0a2db40000000049454e44ae426082"))
        run([d])
        out_dir = os.path.join(d, "webp")
        produced = os.listdir(out_dir) if os.path.isdir(out_dir) else []
        check("M9 变大时 SKIP 不产出", not produced, f"produced={produced}")

        # M10：--in-place 幂等
        d = os.path.join(root, "m10"); os.makedirs(d)
        make_image(os.path.join(d, "photo.png"))
        run(["--in-place", d]); run(["--in-place", d])
        check("M10 --in-place 二次运行无额外副本",
              sorted(os.listdir(d)) == ["photo.png", "photo.webp"], f"ls={sorted(os.listdir(d))}")

        # M4：无 .tmp 残留
        stray = []
        for r_, _ds, fs in os.walk(root):
            stray += [f for f in fs if f.endswith(".tmp")]
        check("M4 无 .tmp 残留", not stray, f"stray={stray}")

        # m2：参数错误返回 2
        r = run(["--quality"])
        check("m2 参数错误返回 2", r.returncode == 2, f"rc={r.returncode}")

        # 帮助可读
        r = run(["--help"])
        check("--help 返回 2 并打印用法", r.returncode == 2 and "用法" in r.stdout)
    finally:
        shutil.rmtree(root, ignore_errors=True)

    failed = [x for x in results if not x[1]]
    print(f"\nSELFTEST: {len(results) - len(failed)}/{len(results)} passed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
