# zectrix-life-guide

把开源书《高性价比人生指南》的 **676 条建议**，每次随机抽一条，渲染成 **400×300 黑白图**推到 [Zectrix 极趣云](https://cloud.zectrix.com) 墨水屏上。可配 30 分钟自动换一条。

![preview](assets/preview.png)

原书按「性价比」排序，每条写清**花掉什么、换回什么、证据多硬**，只引期刊论文和官方文件。这个仓库不复刻阅读页，只做一件事，把条目变成墨水屏上一条能站着看完的建议。

每条都带：所属章节、全局序号、证据等级（A/B/C）、性价比档、「说人话」白话解释、钱/时间/毅力/收益标签、参考文献数。

## 特性

- **洗牌袋抽取**，不是纯随机。676 条打乱成一袋逐条抽，一轮抽完才重新洗牌，不会连着抽到同一条，676 次内保证不重复
- **开箱即用**，`data/life_guide.json` 已随仓库分发，不用先联网抓数据
- **脱敏**，仓库里不含任何 API Key / 设备号，配置写在 `~/.config/`，可以放心分享给别人
- **排版自适应**，标题 1–2 行、正文 15→12px 逐级降字号，标题与正文框整体垂直居中，短句不顶在上边、长文不溢出

## 快速开始

```bash
git clone https://github.com/leosongyyy/zectrix-life-guide.git
cd zectrix-life-guide
pip install pillow

# 1) 初始化：填你的 API Key 和设备 ID（交互引导）
python3 scripts/init.py
#   或一步到位：
#   python3 scripts/init.py --api-key zt_xxx --device AA:BB:CC:DD:EE:FF --page 2
#   不知道设备 ID？先列一下：
#   python3 scripts/init.py --api-key zt_xxx --list-devices

# 2) 先本地预览（这一步不需要配置也能跑）
python3 scripts/zectrix_life_push.py --no-push

# 3) 确认没问题再推
python3 scripts/zectrix_life_push.py
```

推送成功会看到 `PUSH pageId=2 -> 200 {"code":0,...}`。设备是**拉取式**刷新，屏幕会在下次轮询时更新，不是推送的瞬间就变。

## 作为 Agent Skill 使用

这个仓库本身就是标准 skill 结构（根目录有 `SKILL.md`），可以直接被支持 skill 的 agent 加载。

```bash
# WorkBuddy / Claude Code / Codex / 通用 agents，任选其一
ln -s "$(pwd)" ~/.workbuddy/skills/zectrix-life-guide
ln -s "$(pwd)" ~/.claude/skills/zectrix-life-guide
ln -s "$(pwd)" ~/.codex/skills/zectrix-life-guide
```

装好后对 agent 说「墨水屏推一条人生指南」「更新第二屏」之类即可。首次使用 agent 会跑 `init.py` 向你收集 API Key 和设备 ID；**未初始化时脚本会打印 `NEED_INIT:` 并以退出码 2 结束**，agent 应当回头问你，而不是自己编一个 Key。

## 字体（请先看这条）

仓库**故意不内置任何字体**。常见的中文点阵字体 `Zfull-GB` 版权方标注「商用须授权」，不适合随公开仓库分发。

想获得最佳效果（1-bit 屏零锯齿），装一个**开源点阵字体**：

| 字体 | 授权 | 说明 |
|------|------|------|
| [Ark Pixel 方舟像素](https://github.com/TakWolf/ark-pixel-font) | OFL-1.1 | 推荐，中文点阵，多种字号 |
| [Fusion Pixel 缝合像素](https://github.com/TakWolf/fusion-pixel-font) | OFL-1.1 | 推荐，12px 最清晰 |
| [Zpix 最像素](https://github.com/SolidZORO/zpix-pixel-font) | 自由 | 12px 像素字体 |

然后二选一：

```bash
export ZECTRIX_FONT=/path/to/ArkPixel.ttf     # 显式指定
cp ArkPixel.ttf ~/Library/Fonts/              # 或放进字体目录，自动探测
```

一个都找不到时会回退到系统 CJK 字体（PingFang / 苹黑 / Noto CJK / 文泉驿），能显示但不点阵化，小字号会有灰边。完全找不到中文字体会打印警告。

## 定时推送（每 30 分钟）

macOS，保存为 `~/Library/LaunchAgents/com.zectrix.life-guide.plist`（把 `/PATH/TO/` 换成实际路径）：

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

Linux 用 cron：

```cron
*/30 * * * * /usr/bin/python3 /PATH/TO/zectrix-life-guide/scripts/zectrix_life_push.py >> /tmp/zectrix-life-guide.log 2>&1
```

> 同一 pageId 只能有一个任务在推。若该页已经别的屏在用，两者会互相覆盖，先卸掉旧的。

## 命令行参数

| 参数 | 作用 |
|------|------|
| `--no-push` | 只渲染不推送（无需配置，可先跑这个看效果） |
| `--id s3-1` | 渲染指定条目，调试排版用，**不消耗洗牌袋** |
| `--page 3` | 推到第 3 页，默认 2 |
| `--out a.png` | 指定预览图输出路径 |
| `--stats` | 只打印数据概览 |

对应的环境变量：`ZECTRIX_NO_PUSH`、`ZECTRIX_LIFE_ID`、`ZECTRIX_PAGE`、`ZECTRIX_FONT`、`ZECTRIX_API_KEY`、`ZECTRIX_DEVICE_ID`、`ZECTRIX_LIFE_CONFIG_DIR`。

## 数据与上游

```bash
python3 scripts/build_data.py                 # 联网抓上游阅读页，重建 data/life_guide.json
python3 scripts/build_data.py --html x.html   # 离线解析已下载的 HTML
python3 scripts/dev_render_samples.py         # 生成示例图（含最长正文/最长标题极端样本）
```

- 原书 [eternity4719/HowToLiveBetter](https://github.com/eternity4719/HowToLiveBetter)，**Unlicense（公有领域）**
- 阅读页 [cdyforever/how-to-live-better](https://github.com/cdyforever/how-to-live-better)，单文件 HTML，上游每日自动重建；解析正则针对它的 DOM，改版后需要同步调整
- 上游 README 写的 528 条是旧口径，2026-10 实测 **34 节 / 676 条**（A 439、B 182、C 55）

## 排障

| 现象 | 原因与处理 |
|------|-----------|
| 打印 `NEED_INIT:` 退出码 2 | 还没初始化，跑 `python3 scripts/init.py` |
| 中文是方块/空白 | 没找到中文字体，见上面字体一节 |
| 推送返回非 200 | 用 `python3 scripts/init.py --show` 核对 Key 和设备；`--list-devices` 确认设备在该 Key 下 |
| 屏上内容没变 | 设备是拉取式，`code:0` 只代表云端已收到，等设备下次联网唤醒 |
| 偶尔推送失败 | 脚本用 urllib 且无重试，偶发 SSL 失败，下一个周期会自动重试 |
| 想重置洗牌袋 | 删掉 `~/.config/zectrix-life-guide/state.json` |

## 授权

- **代码**：MIT，见 [LICENSE](LICENSE)
- **数据**：源自 Unlicense（公有领域）作品，可自由使用，仍建议保留署名
- **字体**：不在本仓库内，各自按字体自身授权使用
