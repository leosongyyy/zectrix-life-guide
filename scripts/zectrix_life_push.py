#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zectrix 墨水屏 —— 《高性价比人生指南》随机一条

每次运行从 676 条建议里抽一条（洗牌袋，一轮抽完才重复），渲染成 400x300 黑白图
并推送到墨水屏指定页（默认第 2 页）。

排版（400x300 单色）：
  顶部  节名黑底标签 + 「#序号/总数」
  标题  大字号，1–2 行
  主体  「说人话」原文，带左侧黑条与标签页的框
  标签  证据等级（黑底）+ 性价比/钱/时间/毅力/收益
  底部  日期星期 + 文献数

用法:
  python3 scripts/zectrix_life_push.py                  # 抽一条、渲染并推送
  python3 scripts/zectrix_life_push.py --no-push        # 只渲染预览（无需配置，先跑这个）
  python3 scripts/zectrix_life_push.py --id s3-1        # 指定某条（调试排版用，不消耗洗牌袋）
  python3 scripts/zectrix_life_push.py --page 3         # 推到第 3 页
  python3 scripts/zectrix_life_push.py --out /tmp/a.png # 指定输出路径
  python3 scripts/zectrix_life_push.py --stats          # 只看数据概览

环境变量（与命令行参数等价，参数优先）
  ZECTRIX_NO_PUSH=1      只渲染不推送
  ZECTRIX_LIFE_ID=s3-1   指定条目
  ZECTRIX_PAGE=3         推送页码
  ZECTRIX_FONT=/path.ttf 指定字体

数据: data/life_guide.json（由 build_data.py 从上游阅读页生成，已随仓库分发）
配置: ~/.config/zectrix-life-guide/config.json（由 init.py 写入，仓库内不含密钥）
依赖: pillow
"""
import os
import sys
import json
import uuid
import random
import datetime
import argparse
import tempfile
import urllib.request
import urllib.error

from PIL import Image, ImageDraw, ImageFont, ImageOps

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from common import (BASE, load_config, font_or_warn, load_state,  # noqa: E402
                    save_state, repo_data_path)

W, H = 400, 300
M = 14                      # 左右边距
THRESHOLD = 128             # 二值化阈值（墨水屏）
WD_CN = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]

# 不应出现在行首/行尾的标点
NO_LINE_START = set("，。、；：！？）》」』】”’%…·")
NO_LINE_END = set("（《「『【“‘")

FONT_PATH = font_or_warn()


# ---------- 数据 ----------
def load_data():
    p = repo_data_path()
    if not os.path.exists(p):
        raise SystemExit("找不到数据文件 %s，请先运行：python3 scripts/build_data.py" % p)
    with open(p, encoding="utf-8") as f:
        return json.load(f), p


def pick_item(items, forced=None):
    """洗牌袋：一轮抽完所有条目才重新洗牌，保证不重复、不连着抽同一条。"""
    if forced:
        for it in items:
            if it["id"] == forced:
                return it
        raise SystemExit("指定的 id 不存在: %s" % forced)

    st = load_state()
    bag = st.get("bag") or []
    bag = [i for i in bag if 0 <= i < len(items)]
    last = st.get("last_idx")
    if not bag:
        bag = list(range(len(items)))
        random.shuffle(bag)
        # 新一轮的第一条别和上一轮的收尾撞车
        if last is not None and len(bag) > 1 and bag[0] == last:
            bag[0], bag[-1] = bag[-1], bag[0]
    idx = bag.pop(0)
    st["bag"] = bag
    st["last_idx"] = idx
    st["picked_count"] = st.get("picked_count", 0) + 1
    save_state(st)
    return items[idx]


# ---------- 渲染工具 ----------
def F(sz):
    if FONT_PATH:
        return ImageFont.truetype(FONT_PATH, sz)
    return ImageFont.load_default()


# 点阵字体的坑：Pillow 的轮廓度量（getbbox/getmetrics）和内嵌点阵的实际墨迹不一致，
# 直接拿它居中会让中文顶到边。这里真实渲染一次、量出墨迹范围并缓存，居中才准。
_INK_CACHE = {}


def ink_span(text, font):
    key = (text, getattr(font, "size", 0))
    if key in _INK_CACHE:
        return _INK_CACHE[key]
    pad = 20
    w = int(font.getlength(text)) + pad * 2
    h = getattr(font, "size", 20) * 3 + pad * 2
    tmp = Image.new("L", (max(w, 4), max(h, 4)), 255)
    ImageDraw.Draw(tmp).text((pad, pad), text, font=font, fill=0, anchor="la")
    bb = ImageOps.invert(tmp).getbbox()
    span = (0, 0) if bb is None else (bb[1] - pad, bb[3] - pad)
    _INK_CACHE[key] = span
    return span


def tokenize(text):
    """把文本切成排版单元：连续 ASCII 字母数字算一个整体，中文与标点逐字。"""
    out, buf = [], ""
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in "._-%+°/"):
            buf += ch
        else:
            if buf:
                out.append(buf)
                buf = ""
            out.append(ch)
    if buf:
        out.append(buf)
    return out


def wrap(text, font, maxw, draw):
    """按可用宽度折行，尽量避免标点出现在行首。"""
    lines, cur = [], ""
    for tok in tokenize(text):
        trial = cur + tok
        if draw.textlength(trial, font=font) <= maxw or not cur:
            cur = trial
            continue
        if tok in NO_LINE_START:          # 标点跟着上一行走
            cur += tok
        lines.append(cur)
        cur = tok if tok not in NO_LINE_START else ""
    if cur:
        lines.append(cur)
    # 行尾不留开引号
    for i, ln in enumerate(lines):
        if ln and ln[-1] in NO_LINE_END and i + 1 < len(lines):
            lines[i] = ln[:-1]
            lines[i + 1] = ln[-1] + lines[i + 1]
    return [l for l in lines if l]


def ellipsize(lines, max_lines, draw, font):
    """超出行数时截断并加省略号；优先在标点处断，避免半句话被拦腰切开。"""
    if len(lines) <= max_lines:
        return lines
    head = lines[:max_lines]
    # 末行只剩一两个字就整行丢掉，改在上一行收尾，视觉更整齐
    if len(head) > 1 and len(head[-1]) < 4:
        head = head[:-1]
    last = head[-1]
    cut = None
    for i in range(len(last) - 1, 0, -1):
        if last[i - 1] in "，。、；：！？,.;:）)":
            cut = i
            break
        if i < len(last) * 0.6:
            break
    last = (last[:cut] if cut else last[:-1]).rstrip("，。、；：！？,.;:）)")
    head[-1] = last + "…"
    return head


def fit_wrap(text, draw, sizes, maxw, max_lines, leading_ratio=1.34):
    """从大到小选字号，返回 (font, lines, line_height, size)；都不行则用最小字号截断。"""
    for sz in sizes:
        f = F(sz)
        lines = wrap(text, f, maxw, draw)
        lh = max(int(sz * leading_ratio) + 2, int(sz * leading_ratio))
        if len(lines) <= max_lines:
            return f, lines, lh, sz
    sz = sizes[-1]
    f = F(sz)
    lines = ellipsize(wrap(text, f, maxw, draw), max_lines, draw, f)
    return f, lines, int(sz * leading_ratio) + 2, sz


def chip(draw, x, y, text, font, pad=7, height=None, filled=True):
    """画一个小标签。文字按「真实墨迹范围」在标签内垂直居中，避免字形被裁切。"""
    tw = draw.textlength(text, font=font)
    t, b = ink_span(text, font)
    ink_h = b - t
    hh = max(height or (ink_h + 10), ink_h + 6)
    cy = y + hh / 2
    ty = cy - (t + b) / 2
    if filled:
        draw.rectangle([x, y, x + tw + pad * 2, y + hh], fill=0)
        draw.text((x + pad, ty), text, font=font, fill=255, anchor="la")
    else:
        draw.rectangle([x, y, x + tw + pad * 2, y + hh], outline=0, width=1)
        draw.text((x + pad, ty), text, font=font, fill=0, anchor="la")
    return x + tw + pad * 2, y + hh


def text_vcenter(draw, x, cy, text, font, fill=0, right=False):
    """把文字的墨迹垂直居中放在 cy 上（比 anchor='lm' 更准，中文不会偏下）。"""
    t, b = ink_span(text, font)
    draw.text((x, cy - (t + b) / 2), text, font=font, fill=fill,
              anchor=("ra" if right else "la"))


# ---------- 主渲染 ----------
def render(item, total, now, out_path):
    img = Image.new("L", (W, H), 255)
    d = ImageDraw.Draw(img)

    f_chip = F(13)
    f_idx = F(12)
    f_meta = F(12)
    f_label = F(12)

    # ---- 顶部：节名黑底标签（左） + 序号（右） ----
    sec_chip = "%d. %s" % (item["sec"], item["sec_title"])
    f_sec = F(13)
    while d.textlength(sec_chip, font=f_sec) > W - 2 * M - 76 and len(sec_chip) > 5:
        sec_chip = sec_chip[:-1]
    right = "#%d/%d" % (item["num"], total)
    chip(d, M, 8, sec_chip, f_sec, pad=6, height=20)
    text_vcenter(d, W - M, 18, right, f_idx, right=True)
    d.line([(M, 34), (W - M, 34)], fill=0, width=2)

    # ---- 组内布局：标题 + 说人话框，整体在正文区内垂直居中 ----
    REG_TOP, REG_BOT = 44, 240
    inner_x = M + 13
    inner_w = (W - M - 10) - inner_x

    f_title, t_lines, t_lh, t_sz = fit_wrap(
        item["title"] or item["plain"], d, [20, 19, 18, 17, 16], W - 2 * M, 2)
    title_h = (len(t_lines) - 1) * t_lh + t_sz

    # 从大到小试正文字号，选第一个「标题+框」能整体放下的
    picked = None
    for sz in (15, 14, 13, 12):
        f = F(sz)
        lines = wrap(item["plain"], f, inner_w, d)
        lh = int(sz * 1.34) + 2
        box_h = 20 + len(lines) * lh + 12
        if title_h + 18 + box_h <= REG_BOT - REG_TOP:
            picked = (f, lines, lh, box_h, sz)
            break
    if picked is None:                       # 极端长文：最小字号 + 省略号兜底
        sz = 12
        f = F(sz)
        lh = int(sz * 1.34) + 2
        max_l = max(2, (REG_BOT - REG_TOP - title_h - 18 - 32) // lh)
        lines = ellipsize(wrap(item["plain"], f, inner_w, d), max_l, d, f)
        picked = (f, lines, lh, 20 + len(lines) * lh + 12, sz)
    f_body, b_lines, b_lh, box_h, b_sz = picked

    y = REG_TOP + max(0, (REG_BOT - REG_TOP - (title_h + 18 + box_h)) // 2)

    for i, ln in enumerate(t_lines):
        d.text((M, y + i * t_lh), ln, font=f_title, fill=0, anchor="la")

    box_top = y + title_h + 18
    box_bottom = box_top + box_h
    d.rectangle([M, box_top, W - M, box_bottom], outline=0, width=2)
    d.rectangle([M, box_top, M + 5, box_bottom], fill=0)          # 左侧黑条
    chip(d, M + 14, box_top - 9, "说人话", f_label, pad=6, height=18, filled=True)
    for i, ln in enumerate(b_lines):
        d.text((inner_x, box_top + 20 + i * b_lh), ln, font=f_body, fill=0, anchor="la")

    # ---- 标签行：证据等级 + 性价比 + 钱/时间/毅力/收益 ----
    tyy = 248
    x = chip(d, M, tyy, "%s 级" % item["grade"], f_chip, pad=6, height=20, filled=True)[0]
    x += 6
    parts = ["性价比 %s" % item["ratio"]] if item["ratio"] else []
    for k in ("钱", "时间", "毅力", "收益"):
        v = item["tags"].get(k)
        if v:
            parts.append("%s %s" % (k, v))
    tag_txt = " · ".join(parts)
    f_tag = F(12)
    while d.textlength(tag_txt, font=f_tag) > W - M - x - 2 and " · " in tag_txt:
        tag_txt = tag_txt.rsplit(" · ", 1)[0]
    text_vcenter(d, x, tyy + 10, tag_txt, f_tag)

    # ---- 底部 ----
    text_vcenter(d, M, 285, "%d年%d月%d日 %s" % (
        now.year, now.month, now.day, WD_CN[now.weekday()]), f_meta)
    text_vcenter(d, W - M, 285, "文献 %d 篇" % item["src_n"], f_meta, right=True)

    final = img.point(lambda p: 0 if p < THRESHOLD else 255).convert("RGB")
    final.save(out_path)
    return {
        "id": item["id"], "title": item["title"], "grade": item["grade"],
        "ratio": item["ratio"], "title_lines": len(t_lines), "body_lines": len(b_lines),
        "body_sz": b_sz, "body_chars": len(item["plain"]), "out": out_path,
    }


# ---------- 推送 ----------
def multipart(path, api_key, fields, files):
    boundary = ("----WebKitFormBoundary" + uuid.uuid4().hex[:16]).encode()
    body = b""
    for k, v in fields.items():
        body += b"--" + boundary + b"\r\n"
        body += ('Content-Disposition: form-data; name="%s"' % k).encode() + b"\r\n\r\n"
        body += str(v).encode() + b"\r\n\r\n"
    for k, fn, ct, data in files:
        body += b"--" + boundary + b"\r\n"
        body += ('Content-Disposition: form-data; name="%s"; filename="%s"' % (k, fn)).encode() + b"\r\n"
        body += ('Content-Type: %s' % ct).encode() + b"\r\n\r\n"
        body += data + b"\r\n"
    body += b"--" + boundary + b"--\r\n"
    req = urllib.request.Request(BASE + path, data=body, method="POST")
    req.add_header("X-API-Key", api_key)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("Content-Type", "multipart/form-data; boundary=" + boundary.decode())
    try:
        r = urllib.request.urlopen(req, timeout=40)
        return r.status, r.read().decode()
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()


def main():
    ap = argparse.ArgumentParser(description="《高性价比人生指南》墨水屏推送")
    ap.add_argument("--id", default=os.environ.get("ZECTRIX_LIFE_ID"),
                    help="指定条目 id，如 s3-1（不消耗洗牌袋）")
    ap.add_argument("--page", default=os.environ.get("ZECTRIX_PAGE"), help="推送页码 1-5")
    ap.add_argument("--out", default=os.environ.get("ZECTRIX_LIFE_OUT"), help="预览图输出路径")
    ap.add_argument("--no-push", action="store_true", help="只渲染不推送")
    ap.add_argument("--stats", action="store_true", help="只打印数据概览后退出")
    args = ap.parse_args()

    data, data_path = load_data()
    items = data["items"]

    if args.stats:
        from collections import Counter
        g = Counter(i["grade"] for i in items)
        print("数据 %s" % data_path)
        print("  %d 节 / %d 条，生成于 %s" % (len(data["sections"]), len(items), data.get("generated", "?")))
        print("  证据等级 A=%d B=%d C=%d" % (g.get("A", 0), g.get("B", 0), g.get("C", 0)))
        print("  上游 %s（%s）" % (data.get("upstream"), data.get("license")))
        return

    no_push = args.no_push or os.environ.get("ZECTRIX_NO_PUSH") == "1"
    out_path = args.out or os.path.join(tempfile.gettempdir(), "zectrix_life_screen.png")

    item = pick_item(items, args.id)
    info = render(item, len(items), datetime.datetime.now(), out_path)

    print("数据源 %s（%d 条，生成于 %s）" % (data_path, len(items), data.get("generated", "?")))
    print("抽出 %s | %s | %s级 性价比%s" % (info["id"], info["title"], info["grade"], info["ratio"]))
    print("标题 %d 行 / 正文 %d 行 @%dpx（原文 %d 字）" % (
        info["title_lines"], info["body_lines"], info["body_sz"], info["body_chars"]))
    print("saved %s" % out_path)

    if no_push:
        print("只渲染，未推送（去掉 --no-push 即推送）")
        return

    cfg = load_config(required=True)
    page = args.page or cfg.get("page", "2")
    with open(out_path, "rb") as f:
        fb = f.read()
    st, body = multipart("/devices/%s/display/image" % cfg["device_id"],
                         cfg["api_key"],
                         {"pageId": str(page), "dither": "false"},
                         [("images", "life.png", "image/png", fb)])
    print("PUSH pageId=%s -> %s %s" % (page, st, body[:200]))


if __name__ == "__main__":
    main()
