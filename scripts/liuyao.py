#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
六爻（纳甲筮法）装卦引擎 v1.0 · HeiGe-SuanMing / bazi-mingli skill

把六爻最容易装错的一段（纳甲配干支、八宫定世应、以宫五行配六亲、按日干起六神、
动爻变卦、月建日辰旬空）交给脚本装准，推演层（用神取用、旺衰、动静生克、应期）
见 references/19_liuyao.md。

Required Notice: Copyright 2026 HeiGeAi (Blake Xu) (https://github.com/HeiGeAi)
License: PolyForm Noncommercial 1.0.0（完整条款见仓库根 LICENSE）

六爻是占卜（占一件具体的事），非命理。一事一占，趋势化断，不打分。

用法：
  python3 liuyao.py --yao 787888 --date 2026 6 15                # 摇卦：六位数自初爻向上
                                                                 #（6=老阴动 7=少阳 8=少阴 9=老阳动）
  python3 liuyao.py --gua 1 5 4 --date 2026 6 15 --query "问合作" # 直接给 上卦数 下卦数 动爻(0=静卦)
  python3 liuyao.py --yao 999999                                  # 不给 --date 则略过六神/旬空/月建
"""

import argparse
import os
import sys

__version__ = "1.0.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
from meihua import GUA64, TRIGRAM_YAO, YAO_TO_TRIGRAM, XIANTIAN, TRIGRAM_WX  # noqa: E402

ZHI = "子丑寅卯辰巳午未申酉戌亥"
ZHI_WUXING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
              "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}
WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 京房纳甲：各经卦所纳天干（内卦用, 外卦用）
NAJIA_GAN = {"乾": ("甲", "壬"), "坤": ("乙", "癸"), "震": ("庚", "庚"), "巽": ("辛", "辛"),
             "坎": ("戊", "戊"), "离": ("己", "己"), "艮": ("丙", "丙"), "兑": ("丁", "丁")}
# 京房纳支：各经卦内卦三爻、外卦三爻所纳地支（自下而上）
NAJIA_ZHI = {"乾": ("子寅辰", "午申戌"), "震": ("子寅辰", "午申戌"),
             "坎": ("寅辰午", "申戌子"), "艮": ("辰午申", "戌子寅"),
             "坤": ("未巳卯", "丑亥酉"), "巽": ("丑亥酉", "未巳卯"),
             "离": ("卯丑亥", "酉未巳"), "兑": ("巳卯丑", "亥酉未")}

LIUSHEN = ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"]
LIUSHEN_START = {"甲": 0, "乙": 0, "丙": 1, "丁": 1, "戊": 2, "己": 3, "庚": 4, "辛": 4, "壬": 5, "癸": 5}


def _liuqin(gong_wx, yao_wx):
    """以卦宫五行为「我」配六亲。"""
    if yao_wx == gong_wx:
        return "兄弟"
    if WUXING_SHENG[yao_wx] == gong_wx:
        return "父母"      # 生我者
    if WUXING_SHENG[gong_wx] == yao_wx:
        return "子孙"      # 我生者
    if WUXING_KE[yao_wx] == gong_wx:
        return "官鬼"      # 克我者
    return "妻财"          # 我克者


def _build_palace_map():
    """从八纯卦按变爻序列生成八宫六十四卦：纯卦(世6)→初爻变(世1)→二(2)→三(3)→四(4)
    →五(5)→四爻复变=游魂(世4)→内卦复原=归魂(世3)。返回 tuple(六爻)→(宫卦, 世位)。"""
    m = {}
    for tri in XIANTIAN.values():
        base = TRIGRAM_YAO[tri] + TRIGRAM_YAO[tri]
        yao = base[:]
        m[tuple(yao)] = (tri, 6)
        for i, shi in ((0, 1), (1, 2), (2, 3), (3, 4), (4, 5)):
            yao[i] ^= 1
            m[tuple(yao)] = (tri, shi)
        yao[3] ^= 1                      # 游魂：第四爻复变
        m[tuple(yao)] = (tri, 4)
        yao[0], yao[1], yao[2] = base[0], base[1], base[2]  # 归魂：内卦复原
        m[tuple(yao)] = (tri, 3)
    return m


PALACE = _build_palace_map()


def _gua_name(yao):
    down = YAO_TO_TRIGRAM[tuple(yao[0:3])]
    up = YAO_TO_TRIGRAM[tuple(yao[3:6])]
    return GUA64[(up, down)], up, down


def _najia(up_tri, down_tri):
    """六爻纳甲干支（自初爻向上）。"""
    res = []
    for pos in range(6):
        tri, half = (down_tri, 0) if pos < 3 else (up_tri, 1)
        gan = NAJIA_GAN[tri][half]
        zhi = NAJIA_ZHI[tri][half][pos % 3]
        res.append(gan + zhi)
    return res


def _date_context(y, mo, d):
    """起卦日的月建（节气月支）、日干支、旬空。"""
    try:
        from lunar_python import Solar
    except ImportError:
        sys.exit("缺少依赖 lunar_python，请先运行：pip3 install lunar_python")
    ec = Solar.fromYmdHms(y, mo, d, 12, 0, 0).getLunar().getEightChar()
    return {"月建": ec.getMonth()[1], "日辰": ec.getDay(), "旬空": ec.getDayXunKong()}


def build_pan(yao_marks, date=None):
    """装卦。yao_marks：六个 6/7/8/9（自初爻向上）。6=老阴(动) 7=少阳 8=少阴 9=老阳(动)。"""
    if len(yao_marks) != 6 or any(m not in (6, 7, 8, 9) for m in yao_marks):
        raise ValueError("摇卦须为六位 6/7/8/9（自初爻向上）")
    yao = [1 if m in (7, 9) else 0 for m in yao_marks]
    dong = [i + 1 for i, m in enumerate(yao_marks) if m in (6, 9)]

    ben_name, up, down = _gua_name(yao)
    gong_tri, shi = PALACE[tuple(yao)]
    ying = shi + 3 if shi <= 3 else shi - 3
    gong_wx = TRIGRAM_WX[gong_tri]
    ganzhi = _najia(up, down)

    lines = []
    for i in range(6):
        gz = ganzhi[i]
        wx = ZHI_WUXING[gz[1]]
        lines.append({"爻位": i + 1, "干支": gz, "五行": wx,
                      "六亲": _liuqin(gong_wx, wx),
                      "动": (i + 1) in dong,
                      "标记": "世" if i + 1 == shi else ("应" if i + 1 == ying else "")})

    result = {
        "version": __version__,
        "本卦": {"名": ben_name, "宫": f"{gong_tri}宫（{gong_wx}）", "世": shi, "应": ying},
        "爻": lines, "动爻": dong,
    }

    if dong:
        byao = yao[:]
        for p in dong:
            byao[p - 1] ^= 1
        bian_name, bup, bdown = _gua_name(byao)
        bganzhi = _najia(bup, bdown)
        result["变卦"] = {"名": bian_name}
        for i in range(6):
            if lines[i]["动"]:
                gz = bganzhi[i]
                lines[i]["变"] = f"{gz}{ZHI_WUXING[gz[1]]}（{_liuqin(gong_wx, ZHI_WUXING[gz[1]])}）"

    if date:
        ctx = _date_context(*date)
        result["日月"] = ctx
        start = LIUSHEN_START[ctx["日辰"][0]]
        for i in range(6):
            lines[i]["六神"] = LIUSHEN[(start + i) % 6]

    return result


def from_gua(up_num, down_num, dong):
    """直接指定：上卦数 下卦数 动爻（0=静卦，1-6=该爻动）。转成摇卦标记。"""
    if not (1 <= up_num <= 8 and 1 <= down_num <= 8):
        raise ValueError("上下卦数须为 1-8")
    if not (0 <= dong <= 6):
        raise ValueError("动爻须为 0-6（0=静卦）")
    yao = TRIGRAM_YAO[XIANTIAN[down_num]] + TRIGRAM_YAO[XIANTIAN[up_num]]
    marks = []
    for i in range(6):
        if i + 1 == dong:
            marks.append(9 if yao[i] == 1 else 6)
        else:
            marks.append(7 if yao[i] == 1 else 8)
    return marks


def render_text(c, yao_bits, query=None):
    L = []
    def P(s=""): L.append(s)
    P("════════════════════ 六爻 · 装卦 ════════════════════")
    if query:
        P(f"所占：{query}")
    b = c["本卦"]
    head = f"【本卦】{b['名']}　{b['宫']}"
    if c.get("变卦"):
        head += f"　→　【变卦】{c['变卦']['名']}"
    P(head)
    if c.get("日月"):
        dm = c["日月"]
        P(f"【日月】月建 {dm['月建']}　日辰 {dm['日辰']}　旬空 {dm['旬空']}")
    P("")
    for i in range(5, -1, -1):
        line = c["爻"][i]
        pic = "▅▅▅▅▅" if yao_bits[i] == 1 else "▅▅ ▅▅"
        dong_mark = ("○" if yao_bits[i] == 1 else "×") if line["动"] else "　"
        shen = (line.get("六神", "") + "　") if line.get("六神") else ""
        mark = f"〔{line['标记']}〕" if line["标记"] else "　　　"
        bian = f"　→ {line['变']}" if line.get("变") else ""
        P(f"  {shen}{line['六亲']} {line['干支']}{line['五行']}　{pic} {dong_mark}{mark}{bian}")
    P("")
    P(f"动爻：{('第' + '、'.join(str(d) for d in c['动爻']) + '爻') if c['动爻'] else '无（静卦）'}")
    P("推演（用神取用、旺衰、动静生克、应期）见 references/19_liuyao.md。")
    P("══════════════════════════════════════════════════")
    P(f"六爻装卦引擎 v{c['version']}　占卜一事一占，趋势化参考，非铁口断，不打分")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=f"六爻装卦引擎 v{__version__}")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--yao", type=str, metavar="六位数",
                   help="摇卦结果，自初爻向上六位：6=老阴(动) 7=少阳 8=少阴 9=老阳(动)，如 787888")
    g.add_argument("--gua", type=int, nargs=3, metavar=("上卦数", "下卦数", "动爻"),
                   help="直接指定：上卦数(1-8) 下卦数(1-8) 动爻(0-6，0=静卦)")
    ap.add_argument("--date", type=int, nargs=3, metavar=("Y", "M", "D"),
                    help="起卦公历日期，用于月建/日辰/旬空/六神；不传则略过")
    ap.add_argument("--query", type=str, default=None, help="所占之事（一事一占）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"liuyao v{__version__}")
    args = ap.parse_args()

    try:
        if args.yao:
            if len(args.yao) != 6 or not args.yao.isdigit():
                sys.exit("摇卦须为六位数字（自初爻向上），如 --yao 787888")
            marks = [int(x) for x in args.yao]
        else:
            marks = from_gua(args.gua[0], args.gua[1], args.gua[2])
        if args.date:
            from datetime import datetime
            try:
                datetime(args.date[0], args.date[1], args.date[2])
            except ValueError as e:
                sys.exit(f"--date 日期非法：{e}")
        pan = build_pan(marks, date=tuple(args.date) if args.date else None)
    except ValueError as e:
        sys.exit(f"装卦失败：{e}")

    if args.json:
        import json
        print(json.dumps(pan, ensure_ascii=False, indent=2))
    else:
        yao_bits = [1 if m in (7, 9) else 0 for m in marks]
        print(render_text(pan, yao_bits, args.query))


if __name__ == "__main__":
    main()
