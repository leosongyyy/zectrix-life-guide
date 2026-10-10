#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
zectrix-life-guide 初始化向导

收集两项信息并写入 ~/.config/zectrix-life-guide/config.json：
  1. Zectrix API Key（极趣云控制台获取，zt_ 开头）
  2. 设备 ID（设备 MAC，形如 AA:BB:CC:DD:EE:FF）
另可指定推送到第几页（1-5，默认 2）。

用法:
  python3 scripts/init.py                      # 交互式引导（推荐首次使用）
  python3 scripts/init.py --api-key zt_xxx --device AA:BB:CC:DD:EE:FF
  python3 scripts/init.py --api-key zt_xxx --list-devices     # 只列设备
  python3 scripts/init.py --page 3                            # 只改推送页（需已有配置）
  python3 scripts/init.py --show                              # 打印当前配置（密钥打码）
"""
import sys
import os
import json
import argparse
import urllib.request
import urllib.error

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import CONFIG_DIR, CONFIG_FILE, BASE, load_config  # noqa: E402


def api(path, key):
    req = urllib.request.Request(BASE + path)
    req.add_header("User-Agent", "Mozilla/5.0")
    req.add_header("X-API-Key", key)
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return r.status, r.read().decode("utf-8", "ignore")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "ignore")


def input_required(prompt, secret=False):
    try:
        if secret:
            import getpass
            v = getpass.getpass(prompt)
        else:
            v = input(prompt)
    except EOFError:
        v = ""
    v = (v or "").strip()
    if not v:
        print("未提供，已取消。", file=sys.stderr)
        sys.exit(1)
    return v


def list_devices(key):
    st, body = api("/devices", key)
    if st != 200:
        print("请求失败 (HTTP %s): %s" % (st, body[:300]), file=sys.stderr)
        return None
    try:
        js = json.loads(body)
    except Exception:
        print("返回解析失败: %s" % body[:300], file=sys.stderr)
        return None
    data = js.get("data")
    if isinstance(data, list):
        devs = data
    elif isinstance(data, dict):
        devs = data.get("devices") or data.get("list") or []
    else:
        devs = []
    out = []
    for d in devs:
        if not isinstance(d, dict):
            continue
        out.append({
            "device_id": d.get("deviceId") or d.get("device_id") or d.get("mac"),
            "name": d.get("deviceName") or d.get("name") or "",
            "model": d.get("model") or d.get("productModel") or "",
        })
    return out


def verify(key, device, no_verify=False):
    if no_verify:
        print("已跳过校验（--no-verify）。")
        return True
    devs = list_devices(key)
    if devs is None:
        return False
    ids = [d["device_id"] for d in devs if d.get("device_id")]
    if not ids:
        print("未能解析出设备列表，如确认信息无误可加 --no-verify 强制写入。", file=sys.stderr)
        return False
    if device and device.upper() not in [i.upper() for i in ids]:
        print("警告：设备 %s 不在该 Key 的设备列表里" % device, file=sys.stderr)
        for d in devs:
            print("   可用：%s  %s %s" % (d["device_id"], d["name"], d["model"]), file=sys.stderr)
        print("如果确认设备号正确可加 --no-verify，但更可能是填错了。", file=sys.stderr)
        return False
    print("API Key 校验通过，共 %d 台设备。" % len(ids))
    return True


def main():
    ap = argparse.ArgumentParser(description="zectrix-life-guide 初始化")
    ap.add_argument("--api-key")
    ap.add_argument("--device")
    ap.add_argument("--page", default=None, help="推送到哪一页 1-5，默认 2")
    ap.add_argument("--list-devices", action="store_true", help="列出该 Key 下所有设备后退出")
    ap.add_argument("--no-verify", action="store_true", help="跳过 API Key/设备校验")
    ap.add_argument("--show", action="store_true", help="打印当前配置（密钥打码）后退出")
    args = ap.parse_args()

    if args.list_devices:
        if not args.api_key:
            print("需要 --api-key", file=sys.stderr)
            sys.exit(1)
        devs = list_devices(args.api_key) or []
        if not devs:
            print("没解析到设备，原始返回见上。")
            return
        for d in devs:
            print("%s\t%s\t%s" % (d["device_id"], d["name"], d["model"]))
        return

    if args.show:
        try:
            cfg = json.load(open(CONFIG_FILE, encoding="utf-8"))
        except Exception:
            print("尚无配置文件：%s" % CONFIG_FILE)
            return
        shown = dict(cfg)
        if shown.get("api_key"):
            k = shown["api_key"]
            shown["api_key"] = k[:6] + "*" * max(0, len(k) - 6)
        print(json.dumps(shown, ensure_ascii=False, indent=2))
        print("\n配置文件：%s" % CONFIG_FILE)
        return

    old = {}
    if os.path.exists(CONFIG_FILE):
        try:
            old = json.load(open(CONFIG_FILE, encoding="utf-8"))
        except Exception:
            old = {}

    print("== zectrix-life-guide 初始化 ==")
    print("需要两项信息：Zectrix API Key、设备 ID。\n")

    key = args.api_key or old.get("api_key") or \
        input_required("1) Zectrix API Key（zt_ 开头，输入不回显）: ", secret=True)
    device = args.device or old.get("device_id") or \
        input_required("2) 设备 ID（MAC，如 AA:BB:CC:DD:EE:FF）: ")
    page = args.page or old.get("page") or "2"

    if not verify(key, device, args.no_verify):
        print("\n提示：如确认信息无误，可加 --no-verify 强制写入。", file=sys.stderr)
        sys.exit(4)

    cfg = {
        "api_key": key,
        "device_id": device,
        "page": str(page),
        "updated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    }
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
    try:
        os.chmod(CONFIG_FILE, 0o600)
    except Exception:
        pass

    print("\n已写入 %s（权限 600）" % CONFIG_FILE)
    print("  设备 : %s" % device)
    print("  页码 : %s" % page)
    print("\n下一步：")
    print("  python3 scripts/build_data.py                 # 可选：重建最新数据")
    print("  ZECTRIX_NO_PUSH=1 python3 scripts/zectrix_life_push.py   # 先本地预览")
    print("  python3 scripts/zectrix_life_push.py                     # 确认无误后推送")


if __name__ == "__main__":
    main()
