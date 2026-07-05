#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
梅花易数起卦引擎 v1.0 · HeiGe-SuanMing / bazi-mingli skill

把梅花易数最容易手推错的一段（先天八卦数取余定卦、互卦、变卦、体用定位）交给脚本算准，
推演层（体用生克断吉凶、卦气旺衰、应期、万物类象）见 references/18_meihua_yishu.md。

Required Notice: Copyright 2026 HeiGeAi (Blake Xu) (https://github.com/HeiGeAi)
License: PolyForm Noncommercial 1.0.0（完整条款见仓库根 LICENSE）

梅花是占卜（占一件具体的事、某个时刻起卦），非命理（从生辰批一生）。一事一占，趋势化断，不打分。

用法：
  python3 meihua.py --time 2020 3 15 14 30            # 时间起卦（公历，脚本转农历取数）
  python3 meihua.py --time 2020 3 15 14 30 --lunar    # 按农历年月日时输入（闰月用负数月）
  python3 meihua.py --time 2020 3 15 23 30 --zi-sect 1  # 晚子时归次日口径（默认 2=不换日）
  python3 meihua.py --numbers 34 43                   # 数字起卦（上数 下数，须≥1）
  python3 meihua.py --gua 2 3 1                        # 直接给 上卦数 下卦数 动爻
  python3 meihua.py --numbers 34 43 --query "问近期求职" --json   # JSON 输出
"""

import argparse
import os
import sys

__version__ = "1.0.1"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# 五行表与年份闸门统一从 paipan 引入，避免两处定义漂移（paipan 为原始核心引擎，零本地依赖）
from paipan import ZHI, WUXING_SHENG, WUXING_KE, YEAR_MIN, YEAR_MAX  # noqa: E402

# 先天八卦数：乾1 兑2 离3 震4 巽5 坎6 艮7 坤8
XIANTIAN = {1: "乾", 2: "兑", 3: "离", 4: "震", 5: "巽", 6: "坎", 7: "艮", 8: "坤"}
XIANTIAN_NUM = {v: k for k, v in XIANTIAN.items()}
# 三爻，自下而上（阳=1 阴=0）
TRIGRAM_YAO = {"乾": [1, 1, 1], "兑": [1, 1, 0], "离": [1, 0, 1], "震": [1, 0, 0],
               "巽": [0, 1, 1], "坎": [0, 1, 0], "艮": [0, 0, 1], "坤": [0, 0, 0]}
YAO_TO_TRIGRAM = {tuple(v): k for k, v in TRIGRAM_YAO.items()}
TRIGRAM_WX = {"乾": "金", "兑": "金", "离": "火", "震": "木", "巽": "木",
              "坎": "水", "艮": "土", "坤": "土"}
TRIGRAM_XIANG = {"乾": "天", "兑": "泽", "离": "火", "震": "雷", "巽": "风",
                 "坎": "水", "艮": "山", "坤": "地"}
# 八卦基本类象（简，供断事联想；详见 references/18）
TRIGRAM_LEI = {
    "乾": "天·君·父·首·官贵·圆·金玉·刚健",
    "兑": "泽·少女·口舌·喜悦·毁折·巫医",
    "离": "火·中女·目·文书·明丽·礼·电",
    "震": "雷·长男·足·动·惊·车·声名",
    "巽": "风·长女·股·进退·草木·利市三倍",
    "坎": "水·中男·耳·险陷·盗·血·忧",
    "艮": "山·少男·手·止·门阙·稳",
    "坤": "地·母·腹·众·柔顺·田土·吝啬",
}
# 六十四卦名，键 (上卦, 下卦)
_G = "乾兑离震巽坎艮坤"
GUA64 = {
    ("乾", "乾"): "乾为天", ("乾", "兑"): "天泽履", ("乾", "离"): "天火同人", ("乾", "震"): "天雷无妄",
    ("乾", "巽"): "天风姤", ("乾", "坎"): "天水讼", ("乾", "艮"): "天山遁", ("乾", "坤"): "天地否",
    ("兑", "乾"): "泽天夬", ("兑", "兑"): "兑为泽", ("兑", "离"): "泽火革", ("兑", "震"): "泽雷随",
    ("兑", "巽"): "泽风大过", ("兑", "坎"): "泽水困", ("兑", "艮"): "泽山咸", ("兑", "坤"): "泽地萃",
    ("离", "乾"): "火天大有", ("离", "兑"): "火泽睽", ("离", "离"): "离为火", ("离", "震"): "火雷噬嗑",
    ("离", "巽"): "火风鼎", ("离", "坎"): "火水未济", ("离", "艮"): "火山旅", ("离", "坤"): "火地晋",
    ("震", "乾"): "雷天大壮", ("震", "兑"): "雷泽归妹", ("震", "离"): "雷火丰", ("震", "震"): "震为雷",
    ("震", "巽"): "雷风恒", ("震", "坎"): "雷水解", ("震", "艮"): "雷山小过", ("震", "坤"): "雷地豫",
    ("巽", "乾"): "风天小畜", ("巽", "兑"): "风泽中孚", ("巽", "离"): "风火家人", ("巽", "震"): "风雷益",
    ("巽", "巽"): "巽为风", ("巽", "坎"): "风水涣", ("巽", "艮"): "风山渐", ("巽", "坤"): "风地观",
    ("坎", "乾"): "水天需", ("坎", "兑"): "水泽节", ("坎", "离"): "水火既济", ("坎", "震"): "水雷屯",
    ("坎", "巽"): "水风井", ("坎", "坎"): "坎为水", ("坎", "艮"): "水山蹇", ("坎", "坤"): "水地比",
    ("艮", "乾"): "山天大畜", ("艮", "兑"): "山泽损", ("艮", "离"): "山火贲", ("艮", "震"): "山雷颐",
    ("艮", "巽"): "山风蛊", ("艮", "坎"): "山水蒙", ("艮", "艮"): "艮为山", ("艮", "坤"): "山地剥",
    ("坤", "乾"): "地天泰", ("坤", "兑"): "地泽临", ("坤", "离"): "地火明夷", ("坤", "震"): "地雷复",
    ("坤", "巽"): "地风升", ("坤", "坎"): "地水师", ("坤", "艮"): "地山谦", ("坤", "坤"): "坤为地",
}


def _mod(n, base):
    """取余，整除时归为 base（8→坤 / 6→上爻）。"""
    r = n % base
    return r if r else base


def _gua_name(up_tri, down_tri):
    return GUA64[(up_tri, down_tri)]


def _relation(from_wx, to_wx):
    """from 对 to 的五行关系（用于用/互/变对体卦）。"""
    if from_wx == to_wx:
        return "比和"
    if WUXING_SHENG[from_wx] == to_wx:
        return "生"      # from 生 to
    if WUXING_KE[from_wx] == to_wx:
        return "克"      # from 克 to
    if WUXING_SHENG[to_wx] == from_wx:
        return "被生"    # to 生 from（即 from 泄 to）
    return "被克"        # to 克 from


def build_gua(up_num, down_num, dong):
    """给定上卦数、下卦数、动爻(1-6)，推本卦/互卦/变卦 + 体用 + 五行生克。"""
    if not (1 <= up_num <= 8 and 1 <= down_num <= 8):
        raise ValueError("上下卦数须为 1-8")
    if not (1 <= dong <= 6):
        raise ValueError("动爻须为 1-6")
    up_tri, down_tri = XIANTIAN[up_num], XIANTIAN[down_num]
    ben = _gua_name(up_tri, down_tri)
    yao = TRIGRAM_YAO[down_tri] + TRIGRAM_YAO[up_tri]  # 自下而上，爻 1-6

    # 互卦：下互取 2·3·4 爻，上互取 3·4·5 爻
    hu_down = YAO_TO_TRIGRAM[tuple(yao[1:4])]
    hu_up = YAO_TO_TRIGRAM[tuple(yao[2:5])]
    hu = _gua_name(hu_up, hu_down)

    # 变卦：动爻阴阳互换
    byao = yao[:]
    byao[dong - 1] ^= 1
    b_down = YAO_TO_TRIGRAM[tuple(byao[0:3])]
    b_up = YAO_TO_TRIGRAM[tuple(byao[3:6])]
    bian = _gua_name(b_up, b_down)

    # 体用：动爻所在经卦为用，另一卦为体
    if dong <= 3:
        yong_tri, ti_tri, dong_pos = down_tri, up_tri, "下卦"
    else:
        yong_tri, ti_tri, dong_pos = up_tri, down_tri, "上卦"
    ti_wx, yong_wx = TRIGRAM_WX[ti_tri], TRIGRAM_WX[yong_tri]

    rel_yong = _relation(yong_wx, ti_wx)
    rel_hu_up = _relation(TRIGRAM_WX[hu_up], ti_wx)
    rel_hu_down = _relation(TRIGRAM_WX[hu_down], ti_wx)
    rel_bian_ti = _relation(TRIGRAM_WX[b_up if dong > 3 else b_down], ti_wx)

    return {
        "version": __version__,
        "起卦": {"上卦": f"{up_tri}({up_num})", "下卦": f"{down_tri}({down_num})", "动爻": dong},
        "本卦": {"名": ben, "上": up_tri, "下": down_tri,
                 "yao": yao, "象": f"上{TRIGRAM_XIANG[up_tri]}下{TRIGRAM_XIANG[down_tri]}"},
        "互卦": {"名": hu, "上": hu_up, "下": hu_down},
        "变卦": {"名": bian, "上": b_up, "下": b_down},
        "体用": {
            "体卦": ti_tri, "体五行": ti_wx,
            "用卦": yong_tri, "用五行": yong_wx,
            "动在": dong_pos,
            "用对体": rel_yong,
        },
        "生克": {
            "用卦对体": f"{yong_tri}({yong_wx}) {rel_yong} 体{ti_tri}({ti_wx})",
            "互上对体": f"{hu_up}({TRIGRAM_WX[hu_up]}) {rel_hu_up} 体",
            "互下对体": f"{hu_down}({TRIGRAM_WX[hu_down]}) {rel_hu_down} 体",
            "变卦对体": f"变{('上' if dong > 3 else '下')}{(b_up if dong > 3 else b_down)} {rel_bian_ti} 体",
        },
        "断语提示": _duan_hint(rel_yong, rel_bian_ti),
        "类象": {"体": TRIGRAM_LEI[ti_tri], "用": TRIGRAM_LEI[yong_tri]},
    }


def _duan_hint(rel_yong, rel_bian):
    """把体用生克翻成趋势化断语提示（不打分、不铁口）。"""
    now = {
        "生": "用卦生体，事有外助、易得力，倾向顺遂",
        "比和": "体用比和，气顺、阻力小，倾向平顺",
        "克": "用卦克体，事有阻力或外压，需注意、宜谨慎",
        "被生": "体生用，主付出、耗神费力，得失参半",
        "被克": "体克用，体能制事，多主可控、或有小得",
    }[rel_yong]
    fut = {
        "生": "终局得生助，走向偏吉",
        "比和": "终局平顺",
        "克": "终局受克，收尾需防波折",
        "被生": "终局仍耗，宜留余力",
        "被克": "终局体制局面，尚可把握",
    }[rel_bian]
    return f"当下：{now}。发展看互卦为过程。{fut}。（趋势化参考，一事一占，非铁口，不打分）"


def qigua_by_numbers(a, b):
    """数字起卦：上数 a、下数 b。上卦=a%8，下卦=b%8，动爻=(a+b)%6。数须为 ≥1 的计数。"""
    if a < 1 or b < 1:
        raise ValueError("数字起卦须为 ≥1 的整数（数是计数：声音数、字数、物数）")
    return build_gua(_mod(a, 8), _mod(b, 8), _mod(a + b, 6))


def qigua_by_time_numbers(year_zhi_idx, month, day, hour_zhi_idx):
    """时间起卦（已换算好的农历取数）：
    上卦=(年支+月+日)%8，下卦=(年支+月+日+时支)%8，动爻=(年支+月+日+时支)%6。"""
    s = year_zhi_idx + month + day
    return build_gua(_mod(s, 8), _mod(s + hour_zhi_idx, 8), _mod(s + hour_zhi_idx, 6))


def _validate_time_input(y, mo, d, h, mi, lunar):
    """时间起卦前置校验：与 paipan.py 同风格的中文报错，不把上游裸异常漏给用户。"""
    if not (YEAR_MIN <= y <= YEAR_MAX):
        sys.exit(f"年份超出支持范围：本引擎支持公历 {YEAR_MIN}-{YEAR_MAX} 年，收到 {y}。")
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        sys.exit("输入有误：时0-23、分0-59。")
    if lunar:
        if not (1 <= mo <= 12 or -12 <= mo <= -1):
            sys.exit("农历月须为 1-12，闰月用对应负数表示（如 -2=闰二月）。")
        if not (1 <= d <= 30):
            sys.exit("农历日须为 1-30。")
    else:
        from datetime import datetime
        try:
            datetime(y, mo, d, h, mi)
        except ValueError as e:
            sys.exit(f"日期非法：{e}")


def qigua_by_time(y, mo, d, h, mi, lunar=False, zi_sect=2):
    """公历(默认)或农历时间起卦，用 lunar_python 取农历年支序/月/日/时支序。
    zi_sect：晚子时（23 点后）取日口径，1=归次日、2=不换日（默认，主流梅花口径之一，起卦前声明即可）。"""
    try:
        from lunar_python import Solar, Lunar
    except ImportError:
        sys.exit("缺少依赖 lunar_python，请先运行：pip3 install lunar_python")
    _validate_time_input(y, mo, d, h, mi, lunar)
    try:
        if lunar:
            lun = Lunar.fromYmdHms(y, mo, d, h, mi, 0)
        else:
            if zi_sect == 1 and h == 23:
                # 晚子归次日：日数取次日农历日（时支仍为子）
                from datetime import datetime, timedelta
                nd = datetime(y, mo, d, h, mi) + timedelta(hours=1)
                lun = Solar.fromYmdHms(nd.year, nd.month, nd.day, 23, mi, 0).getLunar()
                lun_next = Solar.fromYmdHms(nd.year, nd.month, nd.day, 12, 0, 0).getLunar()
                year_idx = ZHI.index(lun_next.getYearZhi()) + 1
                month = abs(lun_next.getMonth())
                day = lun_next.getDay()
                hour_idx = 1  # 子
                res = qigua_by_time_numbers(year_idx, month, day, hour_idx)
                res["起卦法"] = (f"时间起卦（晚子归次日）：农历{lun_next.getYearInGanZhi()}年 {month}月 {day}日 子时"
                                f"（年支{year_idx}+月{month}+日{day}+时支{hour_idx}）")
                return res
            lun = Solar.fromYmdHms(y, mo, d, h, mi, 0).getLunar()
    except Exception as e:
        sys.exit(f"时间起卦失败（请核对日期是否存在，农历留意小月）：{e}")
    year_idx = ZHI.index(lun.getYearZhi()) + 1     # 子1..亥12
    month = abs(lun.getMonth())                     # 农历月（闰月取绝对值）
    day = lun.getDay()
    hour_idx = ZHI.index(lun.getTimeZhi()) + 1
    res = qigua_by_time_numbers(year_idx, month, day, hour_idx)
    res["起卦法"] = (f"时间起卦：农历{lun.getYearInGanZhi()}年 {month}月 {day}日 {lun.getTimeZhi()}时"
                    f"（年支{year_idx}+月{month}+日{day}+时支{hour_idx}）")
    return res


def render_text(c, query=None):
    L = []
    def P(s=""): L.append(s)
    P("════════════════════ 梅花易数 · 起卦 ════════════════════")
    if query:
        P(f"所占：{query}")
    if c.get("起卦法"):
        P(c["起卦法"])
    q = c["起卦"]
    P(f"起卦：上卦 {q['上卦']}　下卦 {q['下卦']}　动爻 第{q['动爻']}爻")
    P("")
    b = c["本卦"]
    P(f"【本卦】{b['名']}（{b['象']}）")
    P(f"【互卦】{c['互卦']['名']}（上{c['互卦']['上']}下{c['互卦']['下']}）　主事情发展过程")
    P(f"【变卦】{c['变卦']['名']}（上{c['变卦']['上']}下{c['变卦']['下']}）　主结果终局")
    P("")
    ty = c["体用"]
    P(f"【体用】动爻在{ty['动在']} → 用卦 {ty['用卦']}({ty['用五行']})、体卦 {ty['体卦']}({ty['体五行']})")
    P(f"  体代表求测者自身，用代表所占之事。")
    for k, v in c["生克"].items():
        P(f"  {k}：{v}")
    P("")
    P(f"【类象】体{ty['体卦']}：{c['类象']['体']}")
    P(f"        用{ty['用卦']}：{c['类象']['用']}")
    P("")
    P(f"【断语提示】{c['断语提示']}")
    P("══════════════════════════════════════════════════")
    P(f"梅花易数引擎 v{c['version']}　占卜一事一占，趋势化参考，非铁口断，不承诺祸福")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=f"梅花易数起卦引擎 v{__version__}")
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--time", type=int, nargs="+", metavar="Y M D H [Mi]",
                   help="时间起卦：公历 年 月 日 时 [分]（配 --lunar 则按农历）")
    g.add_argument("--numbers", type=int, nargs=2, metavar=("上数", "下数"),
                   help="数字起卦：上数 下数")
    g.add_argument("--gua", type=int, nargs=3, metavar=("上卦数", "下卦数", "动爻"),
                   help="直接指定：上卦数(1-8) 下卦数(1-8) 动爻(1-6)")
    ap.add_argument("--lunar", action="store_true",
                    help="--time 按农历输入（闰月用负数月，如 -2=闰二月；闰月与本月取数相同）")
    ap.add_argument("--zi-sect", type=int, choices=[1, 2], default=2,
                    help="晚子时(23点后)取日口径：1=归次日、2=不换日(默认)；23点起卦时声明所用口径")
    ap.add_argument("--query", type=str, default=None, help="所占之事（一事一占）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"meihua v{__version__}")
    args = ap.parse_args()

    try:
        if args.time:
            if not (4 <= len(args.time) <= 5):
                sys.exit("--time 需 年 月 日 时 [分]")
            t = list(args.time) + [0] * (5 - len(args.time))
            chart = qigua_by_time(t[0], t[1], t[2], t[3], t[4], lunar=args.lunar, zi_sect=args.zi_sect)
        elif args.numbers:
            chart = qigua_by_numbers(args.numbers[0], args.numbers[1])
        else:
            chart = build_gua(args.gua[0], args.gua[1], args.gua[2])
    except (ValueError, KeyError) as e:
        sys.exit(f"起卦失败：{e}")
    except Exception as e:
        sys.exit(f"起卦失败（意外错误，请核对输入）：{e}")

    if args.json:
        import json
        print(json.dumps(chart, ensure_ascii=False, indent=2))
    else:
        print(render_text(chart, args.query))


if __name__ == "__main__":
    main()
