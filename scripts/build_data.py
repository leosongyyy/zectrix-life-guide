#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
《高性价比人生指南》 → 墨水屏数据结构化提取

上游：
  原书   eternity4719/HowToLiveBetter（Unlicense，公有领域）
  阅读页 cdyforever/how-to-live-better（单文件 HTML，上游每日自动重建）

本脚本从在线阅读页抓取单文件 HTML，解析出全部条目，输出 data/life_guide.json。
字段：节号/节名/条目号/证据等级/性价比档/标题/说人话/成本/收益/备注/标签/文献数

仓库已随附一份 2026-10-10 生成的 data/life_guide.json，开箱即用；
想同步上游最新内容时再跑本脚本。

用法:
  python3 scripts/build_data.py                     # 联网抓取并解析
  python3 scripts/build_data.py --html /tmp/x.html  # 用已下载的 HTML 解析（离线）
  python3 scripts/build_data.py --out /path/x.json  # 指定输出路径
"""
import os
import re
import sys
import json
import html
import argparse
import datetime
import subprocess
from collections import Counter

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_OUT = os.path.normpath(os.path.join(HERE, "..", "data", "life_guide.json"))

PAGE_URL = "https://cdyforever.github.io/how-to-live-better/"


def fetch_html(url):
    """注意：直连 raw.githubusercontent.com 在部分网络下不通，GitHub Pages 通常可通但较慢。"""
    print("抓取 %s ..." % url, file=sys.stderr)
    r = subprocess.run(["curl", "-sL", "--max-time", "180", url],
                       capture_output=True, timeout=200)
    if r.returncode != 0 or not r.stdout:
        raise SystemExit("抓取失败（curl exit=%s）。"
                         "也可先手动下载 HTML 再用 --html 离线解析。" % r.returncode)
    return r.stdout.decode("utf-8", "ignore")


def strip_tags(s):
    s = re.sub(r"<br\s*/?>", "\n", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    s = s.replace("\u00a0", " ").replace("\u3000", " ")
    s = re.sub(r"[ \t]+", " ", s)
    return s.strip()


def clean_ws(s):
    return re.sub(r"\s+", " ", s).strip()


def parse(h):
    # 章节：目录里的 <div class="gt">1. 不要早死<small>43 条</small></div>
    secs = []
    for m in re.finditer(r'<div class="gt">\s*(\d+)\.\s*([^<]+?)\s*<small>([^<]*)</small>', h):
        secs.append({"no": int(m.group(1)), "title": m.group(2).strip(),
                     "count": m.group(3).strip()})
    sec_by_no = {s["no"]: s for s in secs}

    items = []
    art_re = re.compile(
        r'<article class="card" id="s(\d+)-(\d+)"\s+data-grade="([^"]*)"\s+'
        r'data-ratio="([^"]*)">(.*?)</article>', re.S)
    for m in art_re.finditer(h):
        sec_no, num = int(m.group(1)), int(m.group(2))
        grade, ratio, body = m.group(3), m.group(4), m.group(5)

        t = re.search(r"<h3>(.*?)</h3>", body, re.S)
        title = clean_ws(strip_tags(t.group(1))) if t else ""

        p = re.search(r'<p class="plain">(.*?)</p>', body, re.S)
        plain = clean_ws(strip_tags(p.group(1))) if p else ""

        tags = [clean_ws(strip_tags(x))
                for x in re.findall(r'<span class="tag">(.*?)</span>', body, re.S)]

        def field(label):
            mm = re.search(r'<div class="f(?: note)?"><b>%s</b><div>(.*?)</div></div>' % label,
                           body, re.S)
            return clean_ws(strip_tags(mm.group(1))) if mm else ""

        cost, gain, note = field("成本"), field("收益"), field("备注")

        s = re.search(r"来源（(\d+) 条文献）", body) or re.search(r"来源（([^）]*)）", body)
        src_n = int(s.group(1)) if (s and s.group(1).isdigit()) else 0

        tagmap = {}
        for tg in tags:
            parts = tg.split(" ", 1)
            if len(parts) == 2:
                tagmap[parts[0]] = parts[1]

        sec = sec_by_no.get(sec_no, {})
        items.append({
            "id": "s%d-%d" % (sec_no, num),
            "sec": sec_no,
            "sec_title": sec.get("title", ""),
            "num": num,
            "grade": grade,
            "ratio": ratio,
            "title": title,
            "plain": plain,
            "cost": cost,
            "gain": gain,
            "note": note,
            "tags": tagmap,
            "src_n": src_n,
        })
    return secs, items


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html", help="本地已下载的 HTML 路径（离线解析）")
    ap.add_argument("--out", default=DEFAULT_OUT, help="输出 JSON 路径")
    a = ap.parse_args()

    h = open(a.html, encoding="utf-8").read() if a.html else fetch_html(PAGE_URL)
    secs, items = parse(h)

    if not items:
        raise SystemExit("解析结果为空，上游 HTML 结构可能已变，请检查解析正则")
    if len(items) != len(set(i["id"] for i in items)):
        raise SystemExit("存在重复 id，解析有误")

    data = {
        "generated": datetime.datetime.now().strftime("%Y-%m-%d %H:%M"),
        "source_page": PAGE_URL,
        "upstream": "https://github.com/eternity4719/HowToLiveBetter",
        "license": "Unlicense (公有领域)",
        "sections": secs,
        "item_count": len(items),
        "items": items,
    }

    g = Counter(i["grade"] for i in items)
    r = Counter(i["ratio"] for i in items)
    empty_plain = sum(1 for i in items if not i["plain"])

    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=1)
    print("已写入 %s" % a.out)

    print("\n解析完成：%d 节 / %d 条" % (len(secs), len(items)))
    print("证据等级 A=%d B=%d C=%d" % (g.get("A", 0), g.get("B", 0), g.get("C", 0)))
    print("性价比档 %s" % dict(r))
    print("说人话为空：%d 条" % empty_plain)
    print("平均说人话字数：%d" % (sum(len(i["plain"]) for i in items) / len(items)))
    longest = max(items, key=lambda i: len(i["plain"]))
    print("最长说人话：%d 字（%s）" % (len(longest["plain"]), longest["id"]))
    print("标题长度 %d ~ %d 字" % (min(len(i["title"]) for i in items),
                                 max(len(i["title"]) for i in items)))


if __name__ == "__main__":
    main()
