#!/usr/bin/env python
"""生成听力题的音频文件。

读 题库/variants.json 里 type=listening 的题，用 edge-tts 读它的 script 字段，
输出到 网站/assets/audio/<id>.mp3（再由 build_site 复制进发布目录）。

用法：python 刷题/make_audio.py [--force]
"""
import argparse
import asyncio
import json
import os

import edge_tts

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
BANK = os.path.join(ROOT, "题库", "variants.json")
OUT = os.path.join(ROOT, "网站", "assets", "audio")

VOICE = "en-US-AriaNeural"
RATE = "-10%"          # 比常速慢一点，五年级听得清


async def synth(text, path):
    for attempt in (1, 2, 3):
        try:
            await edge_tts.Communicate(text, VOICE, rate=RATE).save(path)
            if os.path.exists(path) and os.path.getsize(path) > 600:
                return True
        except Exception:
            if attempt == 3:
                return False
            await asyncio.sleep(1.2)
    return False


async def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--force", action="store_true", help="已有文件也重生成")
    a = ap.parse_args()

    items = [x for x in json.load(open(BANK, encoding="utf-8"))["题目"]
             if x.get("type") == "listening"]
    os.makedirs(OUT, exist_ok=True)

    made = skipped = failed = 0
    for it in items:
        path = os.path.join(OUT, it["id"] + ".mp3")
        if os.path.exists(path) and not a.force:
            skipped += 1
            continue
        ok = await synth(it["script"], path)
        if ok:
            made += 1
            print("  ✓ %s  %-46s %5.0f KB" % (it["id"], it["script"][:44],
                                              os.path.getsize(path) / 1024))
        else:
            failed += 1
            print("  ✗ %s  生成失败" % it["id"])

    print("\n听力音频：新生成 %d，跳过 %d，失败 %d → %s" % (made, skipped, failed, OUT))


if __name__ == "__main__":
    asyncio.run(main())
