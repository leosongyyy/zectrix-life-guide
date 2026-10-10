#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成文档用的示例图（不推送、不消耗洗牌袋）。

分别渲染「首条」「最长正文」「最长标题」三个极端样本，用来检查排版边界。

用法:
  python3 scripts/dev_render_samples.py
  python3 scripts/dev_render_samples.py --outdir assets
"""
import os
import sys
import json
import argparse
import datetime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import zectrix_life_push as P  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default=os.path.normpath(os.path.join(HERE, "..", "assets")))
    args = ap.parse_args()

    data, _ = P.load_data()
    items = data["items"]
    total = len(items)

    targets = [
        ("first", items[0]["id"], "首条"),
        ("long-body", max(items, key=lambda i: len(i["plain"]))["id"], "最长正文"),
        ("long-title", max(items, key=lambda i: len(i["title"]))["id"], "最长标题"),
    ]

    os.makedirs(args.outdir, exist_ok=True)
    now = datetime.datetime.now()
    for name, _id, desc in targets:
        item = next(i for i in items if i["id"] == _id)
        out = os.path.join(args.outdir, "sample-%s.png" % name)
        info = P.render(item, total, now, out)
        print("%-12s %-8s %-28s -> %s" % (desc, info["id"], info["title"][:26], out))

    print("\n字体：%s" % (P.FONT_PATH or "(未找到中文字体！)"))


if __name__ == "__main__":
    main()
