---
name: zectrix-life-guide
description: Zectrix 墨水屏《高性价比人生指南》单条推送。从 676 条建议里用洗牌袋抽一条，渲染成 400×300 黑白单色图推到指定页（默认第 2 屏），可配 30 分钟定时轮换。每条带证据等级（A/B/C）、性价比档与「说人话」白话解释。首次使用引导用户提供 API Key 和设备 ID。触发词：人生指南、高性价比、墨水屏看书、推送一条建议、zectrix life、性价比指南。
agent_created: true
---

# 墨水屏《高性价比人生指南》单条推送

给 **Zectrix 400×300 单色墨水屏**渲染一页，每次展示开源书《高性价比人生指南》里的一条建议。

原书按「性价比」排序，每条写清**花掉什么、换回什么、证据多硬**，只引期刊论文和官方文件。本技能不复刻阅读页，只做一件事，把条目变成**墨水屏上一条能站着看完的建议**。

效果见 `assets/preview.png`：

```
   [23. 学什么技能划算]              #13/676     ← 节名黑底标签 + 序号
  ─────────────────────────────────────────
   同样的钱和时间，优先选能直接上岗的           ← 标题，1–2 行，超长自动收字号
   短周期项目
   ┌─说人话──────────────────────────────┐
   │ 政策鼓励短平快培训和职业院校微专业……    │     ← 正文，15→12px 自适应
   └────────────────────────────────────┘
   [C 级] 性价比 一般 · 钱 少 · 时间 中 · 毅力 些 · 收益 中
   2026年10月10日 周六                    文献 1 篇
```

- **数据**：随仓库分发 `data/life_guide.json`，34 节 / **676 条**（A 级 439、B 级 182、C 级 55）
- **抽取**：**洗牌袋**（shuffle bag）而非纯随机，一轮抽完才重新洗牌，不会出现「同一条连着抽到两次」，676 次内保证不重复
- **状态**：洗牌袋进度存在配置目录，**不在技能目录内**，所以技能可以安全更新/分享

## 一、首次使用：必须初始化（脱敏，无内置密钥）

本技能**不含任何 API Key、设备号**，全部由用户自备，首次运行前必须初始化。

```bash
cd ~/.workbuddy/skills/zectrix-life-guide/scripts   # 或本仓库任意位置
python3 init.py                      # 交互式引导，推荐
python3 init.py --api-key zt_xxx --device AA:BB:CC:DD:EE:FF --page 2   # 非交互
python3 init.py --api-key zt_xxx --list-devices     # 先看看这个 Key 下有哪些设备
python3 init.py --show                              # 查看当前配置（密钥打码）
```

需要向用户收集两样东西，缺一不可（**不要猜、不要用示例值**）：

1. **Zectrix API Key**：用户在极趣云控制台获取，`zt_` 开头。
2. **设备 ID**：设备 MAC，形如 `AA:BB:CC:DD:EE:FF`；不确定就先跑 `--list-devices`。

初始化会校验 Key 与设备是否匹配（不匹配会列出可用设备并退出，确认识别问题可加 `--no-verify`），随后写入 `~/.config/zectrix-life-guide/config.json`（权限 600）：

```json
{
  "api_key": "zt_xxx",
  "device_id": "AA:BB:CC:DD:EE:FF",
  "page": "2"
}
```

配置与状态都在 `~/.config/zectrix-life-guide/`（可用环境变量 `ZECTRIX_LIFE_CONFIG_DIR` 覆盖）。环境变量优先级更高：`ZECTRIX_API_KEY` / `ZECTRIX_DEVICE_ID` / `ZECTRIX_PAGE`。

> 未初始化就推送，脚本会打印 `NEED_INIT:` 并以退出码 2 结束。此时按本节引导用户补配置信息，**不要自行编造 Key**。

## 二、日常使用

```bash
python3 scripts/zectrix_life_push.py --no-push   # 只渲染预览，不需要配置
python3 scripts/zectrix_life_push.py             # 抽一条、渲染并推送
python3 scripts/zectrix_life_push.py --stats     # 只看数据概览
python3 scripts/zectrix_life_push.py --id s3-1 --no-push   # 指定某条调排版（不消耗洗牌袋）
python3 scripts/zectrix_life_push.py --page 3    # 推到第 3 页
```

预览图默认输出到系统临时目录下的 `zectrix_life_screen.png`，可用 `--out` 指定。

想同步上游最新内容时重建数据：

```bash
python3 scripts/build_data.py                    # 联网抓取阅读页
python3 scripts/build_data.py --html x.html      # 离线解析已下载的 HTML
```

## 三、字体：本仓库不内置字体（重要）

仓库**故意不放任何字体文件**。原因：常见的中文点阵字体 `Zfull-GB` 版权方标注「商用须授权」，随公开仓库分发有法律风险。

运行时按顺序探测：

1. `$ZECTRIX_FONT` 指定的字体
2. 开源点阵字体：**Ark Pixel**（方舟像素，OFL-1.1）、**Fusion Pixel**（缝合像素，OFL-1.1）、**Zpix** —— 1-bit 屏上零锯齿，**强烈推荐**
3. 用户自备的点阵字体（如 `~/Library/Fonts/Zfull.ttf`）
4. 系统 CJK 字体兜底（PingFang / 苹黑 / 冬青黑 / Noto CJK / 文泉驿）

没找到中文字体会打印警告并继续（中文会渲染成方块）。给用户装字体的建议直接说：装 Ark Pixel 或 Fusion Pixel，`ZECTRIX_FONT` 指向它，或把字体放进 `~/Library/Fonts/`。

## 四、渲染与排版经验（改样式时务必遵守）

- **原生 400×300、1:1 渲染**，不要放大后再缩小；保存前按阈值 `THRESHOLD=128` 硬二值化（`dither=false` 推送），文字最锐利
- **点阵字体的度量不能信**：Pillow 的 `getbbox()` / `getmetrics()` 返回的是**轮廓**度量，和内嵌点阵的实际墨迹不一致，拿它算垂直居中会让中文顶到标签框边缘。正确做法是**真实渲染一次、用 `ImageOps.invert(tmp).getbbox()` 量出墨迹范围**，再据此居中（已封装成 `ink_span()` / `chip()` / `text_vcenter()`）
- **判断「字有没有被裁切」别靠肉眼**：放大 8 倍仍可能看不准，逐行统计黑白像素才靠谱
- **标题与正文框作为一组整体垂直居中**，短句不顶在上边、长文不溢出
- 正文字号从 15px 逐级降到 12px，选第一个「标题+框」能整体放下的；极端长文才截断加省略号
- 截断优先落在标点上，避免半句话被拦腰切开；末行不足 4 字就整行丢掉
- ▲▼ 等符号在点阵字体小字号会缺字形，一律用代码画，不要用字符
- 文字一律默认字重，不加粗不描边（1-bit 屏上加粗会糊成一团）

## 五、定时推送

设备是**拉取式**刷新，API 返回 `code:0` 即成功，屏幕会在下次轮询时更新。建议每 30 分钟推一次。

macOS（launchd），存 `~/Library/LaunchAgents/com.zectrix.life-guide.plist`：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.zectrix.life-guide</string>
    <key>ProgramArguments</key>
    <array>
        <string>/usr/bin/python3</string>
        <string>/PATH/TO/zectrix-life-guide/scripts/zectrix_life_push.py</string>
    </array>
    <key>StartInterval</key>
    <integer>1800</integer>
    <key>RunAtLoad</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/tmp/zectrix-life-guide.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/zectrix-life-guide.log</string>
</dict>
</plist>
```

```bash
launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.zectrix.life-guide.plist
```

Linux（cron）：

```cron
*/30 * * * * /usr/bin/python3 /PATH/TO/zectrix-life-guide/scripts/zectrix_life_push.py >> /tmp/zectrix-life-guide.log 2>&1
```

> 注意：同一 pageId 只能有一个任务在推。若该页已有别的屏（如基金走势），两者会互相覆盖，先卸掉旧的。

## 六、文件说明

| 文件 | 说明 |
|------|------|
| `scripts/init.py` | 初始化向导：收集 Key/设备/页码，校验并写配置 |
| `scripts/zectrix_life_push.py` | 抽条 + 渲染 + 推送主脚本 |
| `scripts/common.py` | 配置读取（脱敏）与字体探测 |
| `scripts/build_data.py` | 从上游阅读页抓取并解析出 `data/life_guide.json` |
| `scripts/dev_render_samples.py` | 生成文档示例图（含最长正文/最长标题极端样本） |
| `data/life_guide.json` | 676 条结构化数据（已随仓库分发，开箱即用） |
| `assets/preview.png` | 效果预览图 |

## 七、数据来源与授权

- 原书 [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter)，**Unlicense（公有领域）**
- 阅读页 [cdyforever/how-to-live-better](https://github.com/cdyforever/how-to-live-better)（单文件 HTML，上游每日自动重建），本技能的数据解析器针对它的 DOM 结构
- 本仓库的**代码**为 MIT；**数据**源自上述公有领域作品，可自由使用，仍建议保留署名
- 上游阅读页的 README 写着 528 条是旧口径，2026-10 实测解析为 676 条
