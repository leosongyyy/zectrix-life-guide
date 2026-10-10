#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zectrix-life-guide 公共模块：配置读取（脱敏）与字体探测。

设计要点
  1. 仓库内**不含任何 API Key / 设备号**，运行时从 ~/.config/zectrix-life-guide/config.json 读，
     所以本仓库可以安全公开分享、被他人 clone 后各自填自己的设备。
  2. 仓库内**不内置任何字体**（字体授权各不相同，见 README），运行时按优先级探测系统字体。

环境变量（优先级高于配置文件）
  ZECTRIX_API_KEY      极趣云 API Key，zt_ 开头
  ZECTRIX_DEVICE_ID    设备 MAC，如 AA:BB:CC:DD:EE:FF
  ZECTRIX_PAGE         推送到第几页，1-5，默认 2
  ZECTRIX_FONT         指定字体文件路径
  ZECTRIX_LIFE_CONFIG_DIR  配置/状态目录，默认 ~/.config/zectrix-life-guide
"""
import os
import sys
import glob
import json

APP = "zectrix-life-guide"
CONFIG_DIR = os.environ.get("ZECTRIX_LIFE_CONFIG_DIR",
                            os.path.expanduser("~/.config/" + APP))
CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
STATE_FILE = os.path.join(CONFIG_DIR, "state.json")

BASE = "https://cloud.zectrix.com/open/v1"

DATA_REL = ("..", "data", "life_guide.json")   # 相对 scripts/


def repo_data_path():
    here = os.path.dirname(os.path.abspath(__file__))
    return os.path.normpath(os.path.join(here, *DATA_REL))


def load_config(required=True):
    """读取配置。找不到且 required 时打印 NEED_INIT 并以退出码 2 结束。"""
    cfg = {}
    try:
        with open(CONFIG_FILE, encoding="utf-8") as f:
            cfg = json.load(f)
    except Exception:
        cfg = {}

    if os.environ.get("ZECTRIX_API_KEY"):
        cfg["api_key"] = os.environ["ZECTRIX_API_KEY"]
    if os.environ.get("ZECTRIX_DEVICE_ID"):
        cfg["device_id"] = os.environ["ZECTRIX_DEVICE_ID"]
    if os.environ.get("ZECTRIX_PAGE"):
        cfg["page"] = os.environ["ZECTRIX_PAGE"]
    cfg.setdefault("page", "2")

    if required and not (cfg.get("api_key") and cfg.get("device_id")):
        sys.stderr.write(
            "NEED_INIT: 尚未配置 Zectrix API Key / 设备 ID。\n"
            "  交互式：  python3 scripts/init.py\n"
            "  非交互：  python3 scripts/init.py --api-key zt_xxx --device AA:BB:CC:DD:EE:FF\n"
            "  列设备：  python3 scripts/init.py --api-key zt_xxx --list-devices\n")
        sys.exit(2)
    return cfg


# ---------------- 字体探测 ----------------
# 顺序说明：
#   1) ZECTRIX_FONT 指定的
#   2) 开源点阵字体（1-bit 墨水屏上零锯齿，效果最好）
#   3) 用户自备的点阵字体（如 Zfull-GB，注意其商用需授权）
#   4) 系统自带 CJK 字体（能显示，但非点阵，小字号会有灰边）
FONT_CANDIDATES = [
    os.environ.get("ZECTRIX_FONT", ""),
    # 开源点阵字体（推荐）
    "~/Library/Fonts/Ark Pixel 12px Proportional zh_CN.otf",
    "~/Library/Fonts/ArkPixel.ttf",
    "/Library/Fonts/Ark Pixel 12px Proportional zh_CN.otf",
    "~/Library/Fonts/FusionPixel.ttf",
    "/Library/Fonts/FusionPixel.ttf",
    "~/Library/Fonts/Zpix.ttf",
    "/Library/Fonts/Zpix.ttf",
    "/usr/share/fonts/truetype/ark-pixel/ark-pixel-12px-proportional-zh_cn.otf",
    # 用户自备点阵（商用需自行确认授权）
    "~/Library/Fonts/Zfull.ttf",
    "/Library/Fonts/Zfull.ttf",
    # 系统 CJK 兜底
    "/System/Library/Fonts/PingFang.ttc",
    "/System/Library/Fonts/STHeiti Medium.ttc",
    "/System/Library/Fonts/Hiragino Sans GB.ttc",
    "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc",
    "/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc",
    "/usr/share/fonts/wenquanyi/wqy-zenhei.ttc",
    "/usr/share/fonts/truetype/arphic/uming.ttc",
]

_FONT_EXTS = (".ttf", ".otf", ".ttc")
_FONT_KEYWORDS = ("pixel", "zpix", "arkpixel", "fusionpixel", "zfull", "unifont")


def find_font():
    """按优先级找第一个存在的字体；没有则扫常见字体目录找点阵关键字。"""
    for p in FONT_CANDIDATES:
        p = os.path.expanduser(p) if p else ""
        if p and os.path.exists(p):
            return p

    bases = [os.path.expanduser("~/Library/Fonts"), "/Library/Fonts",
             "/System/Library/Fonts", "/usr/share/fonts"]
    for base in bases:
        if not os.path.isdir(base):
            continue
        for root, _dirs, files in os.walk(base):
            if root.count(os.sep) - base.count(os.sep) > 3:
                continue
            for fn in files:
                low = fn.lower()
                if low.endswith(_FONT_EXTS) and any(k in low for k in _FONT_KEYWORDS):
                    return os.path.join(root, fn)
    return None


def font_or_warn():
    """找不到字体时给出明确警告（中文会渲染不出来），但不中断渲染流程。"""
    f = find_font()
    if not f:
        sys.stderr.write(
            "WARN: 没找到中文字体，中文会渲染成方块或空白。\n"
            "  推荐安装开源点阵字体（Ark Pixel / Fusion Pixel / Zpix，均为 OFL 等自由授权），\n"
            "  然后设置 ZECTRIX_FONT=/path/to/font.ttf 或把字体放进 ~/Library/Fonts/\n")
    return f


def load_state():
    try:
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(st):
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(st, f, ensure_ascii=False)
    except Exception as e:
        sys.stderr.write("状态写入失败（不影响本次推送）：%s\n" % e)
