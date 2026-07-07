#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紫微斗数安星引擎 v1.0 · HeiGe-SuanMing / bazi-mingli skill

把紫微斗数最容易装错的一段（十二宫定位、五行局、紫微星系、天府星系、四化、
六吉六煞、大限小限）交给脚本算准，推演层（用神取象、宫位互参、化忌冲、限运吉凶）
见 references/20_ziwei.md。

Required Notice: Copyright 2026 HeiGeAi (Blake Xu) (https://github.com/HeiGeAi)
License: PolyForm Noncommercial 1.0.0（完整条款见仓库根 LICENSE）

紫微斗数是命理（批一生），与八字同属命理门类、与梅花六爻的占卜门类不同。

全部安星公式已用开源实现 iztro（github.com/SylarLong/iztro）的官方测试用例做过
40 项数值核验（39 项精确吻合，1 项为已知流派分歧并如实标注，见 references/20）。

用法：
  python3 ziwei.py 2000 8 16 3 30 --gender female            # 公历生辰起盘
  python3 ziwei.py 2000 7 17 3 30 --gender female --lunar    # 农历生辰起盘（闰月用负数月）
  python3 ziwei.py 2000 8 16 3 30 --gender female --json     # JSON 输出
"""

import argparse
import os
import sys

__version__ = "1.0.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# 天干地支表统一从 paipan 引入（唯一真源，避免多处拷贝漂移）
from paipan import GAN, ZHI, GAN_YINYANG, YEAR_MIN, YEAR_MAX  # noqa: E402

GAN_IDX = {g: i for i, g in enumerate(GAN)}
ZHI_IDX = {z: i for i, z in enumerate(ZHI)}

# ============================================================
# 十二宫（命宫起，逆时针固定顺序；《紫微斗数全书》：男女俱从逆转，切忌莫顺去）
# ============================================================
PALACE_NAMES = ["命宫", "兄弟", "夫妻", "子女", "财帛", "疾厄",
                "迁移", "交友", "官禄", "田宅", "福德", "父母"]


def locate_ming_shen_gong(month, time_idx):
    """命宫身宫诀：寅起正月顺数至生月得月份宫；命宫=月份宫逆数生时，身宫=月份宫顺数生时。
    month：农历月（1-12，闰月按本月数，即 abs(闰月)）。time_idx：时辰地支序（子=0）。"""
    month_gong = (2 + (month - 1)) % 12  # 寅=2
    ming_gong = (month_gong - time_idx) % 12
    shen_gong = (month_gong + time_idx) % 12
    return ming_gong, shen_gong


def palace_order_from(ming_gong_idx):
    """从命宫起，逆时针（地支序数递减）排十二宫，返回 {宫名: 地支序}。"""
    return {name: (ming_gong_idx - i) % 12 for i, name in enumerate(PALACE_NAMES)}


# ============================================================
# 命宫干支（五虎遁）+ 五行局
# ============================================================
# 五虎遁诀：甲己起丙寅、乙庚起戊寅、丙辛起庚寅、丁壬起壬寅、戊癸起甲寅
_WUHU = {0: 2, 5: 2, 1: 4, 6: 4, 2: 6, 7: 6, 3: 8, 8: 8, 4: 0, 9: 0}


def ming_gong_gan(year_gan_idx, ming_gong_zhi_idx):
    """命宫天干：由年干五虎遁定寅宫天干，从寅顺排到命宫地支。"""
    yin_gan_idx = _WUHU[year_gan_idx]
    steps = (ming_gong_zhi_idx - 2) % 12
    return (yin_gan_idx + steps) % 10


# 五行局数字诀：天干甲乙1丙丁2戊己3庚辛4壬癸5；地支子午丑未1寅申卯酉2辰戌巳亥3；
# 干支数相加>5减5，1-5对应 木三局/金四局/水二局/火六局/土五局
_GAN_NUM = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 4, 7: 4, 8: 5, 9: 5}
_ZHI_NUM = {0: 1, 1: 1, 2: 2, 3: 2, 4: 3, 5: 3, 6: 1, 7: 1, 8: 2, 9: 2, 10: 3, 11: 3}
_JU_MAP = {1: ("木", 3), 2: ("金", 4), 3: ("水", 2), 4: ("火", 6), 5: ("土", 5)}


def wuxing_ju(gan_idx, zhi_idx):
    """命宫干支纳音定五行局，返回 (五行名, 局数)。"""
    s = _GAN_NUM[gan_idx] + _ZHI_NUM[zhi_idx]
    if s > 5:
        s -= 5
    return _JU_MAP[s]


# ============================================================
# 紫微星定位（公式法，与图诀查表法数学等价）
# ============================================================
# 各局余数 -> 起点地支序（水二/木三/金四/土五/火六局）
_ZIWEI_TABLE = {
    2: {1: 1, 2: 2},
    3: {1: 4, 2: 1, 3: 2},
    4: {1: 11, 2: 4, 3: 1, 4: 2},
    5: {1: 6, 2: 11, 3: 4, 4: 1, 5: 2},
    6: {1: 9, 2: 6, 3: 11, 4: 4, 5: 1, 6: 2},
}


def ziwei_position(ju, day):
    """紫微星定位：局数除生日，商数顺移、余数查起点表；余0则商减1余数补足局数（借位）。"""
    q, r = divmod(day, ju)
    if r == 0:
        q -= 1
        r = ju
    start = _ZIWEI_TABLE[ju][r]
    return (start + q) % 12


# 紫微星系：以紫微为基准逆时针（序数递减）；天府星系：以天府为基准顺时针（序数递增）
_ZIWEI_GROUP_OFFSET = {"紫微": 0, "天机": -1, "太阳": -3, "武曲": -4, "天同": -5, "廉贞": -8}
_TIANFU_GROUP_OFFSET = {"天府": 0, "太阴": 1, "贪狼": 2, "巨门": 3, "天相": 4,
                        "天梁": 5, "七杀": 6, "破军": 10}


def ziwei_star_group(ziwei_idx):
    return {star: (ziwei_idx + off) % 12 for star, off in _ZIWEI_GROUP_OFFSET.items()}


def tianfu_position(ziwei_idx):
    """天府定位：(4 - 紫微序数) mod 12（寅申同宫、其余各宫沿寅申连线镜像对称，非简单对宫）。"""
    return (4 - ziwei_idx) % 12


def tianfu_star_group(tianfu_idx):
    return {star: (tianfu_idx + off) % 12 for star, off in _TIANFU_GROUP_OFFSET.items()}


MAJOR_14 = ["紫微", "天机", "太阳", "武曲", "天同", "廉贞",
            "天府", "太阴", "贪狼", "巨门", "天相", "天梁", "七杀", "破军"]

# ============================================================
# 四化（十天干，甲乙丙丁戊己庚辛壬癸）
# 化科/化忌存在真实流派分歧（庚年、壬年），见 references/20 出处与版本说明
# ============================================================
SIHUA = {
    "甲": {"化禄": "廉贞", "化权": "破军", "化科": "武曲", "化忌": "太阳"},
    "乙": {"化禄": "天机", "化权": "天梁", "化科": "紫微", "化忌": "太阴"},
    "丙": {"化禄": "天同", "化权": "天机", "化科": "文昌", "化忌": "廉贞"},
    "丁": {"化禄": "太阴", "化权": "天同", "化科": "天机", "化忌": "巨门"},
    "戊": {"化禄": "贪狼", "化权": "太阴", "化科": "右弼", "化忌": "天机"},
    "己": {"化禄": "武曲", "化权": "贪狼", "化科": "天梁", "化忌": "文曲"},
    "庚": {"化禄": "太阳", "化权": "武曲", "化科": "太阴", "化忌": "天同"},  # 存疑：另说科天府/忌太阴
    "辛": {"化禄": "巨门", "化权": "太阳", "化科": "文曲", "化忌": "文昌"},
    "壬": {"化禄": "天梁", "化权": "紫微", "化科": "左辅", "化忌": "武曲"},  # 存疑：另说科天府
    "癸": {"化禄": "破军", "化权": "巨门", "化科": "太阴", "化忌": "贪狼"},
}

# ============================================================
# 六吉星：文昌文曲按时辰、左辅右弼按生月，天魁天钺按年干贵人表
# ============================================================
# 天魁天钺：甲戊庚丑未、乙己子申、辛寅午、壬癸卯巳、丙丁亥酉（丙丁钺存疑，见 references/20）
_KUI_YUE = {0: (1, 7), 4: (1, 7), 6: (1, 7),   # 甲戊庚
            1: (0, 8), 5: (0, 8),               # 乙己
            7: (2, 6),                          # 辛
            8: (3, 5), 9: (3, 5),               # 壬癸
            2: (11, 9), 3: (11, 9)}             # 丙丁


def liuji_stars(year_gan_idx, month, time_idx):
    """六吉星：文昌(戌逆数时辰) / 文曲(辰顺数时辰) / 左辅(辰顺数生月) / 右弼(戌逆数生月) / 天魁天钺(年干贵人表)。"""
    kui, yue = _KUI_YUE[year_gan_idx]
    return {
        "文昌": (10 - time_idx) % 12,
        "文曲": (4 + time_idx) % 12,
        "左辅": (4 + (month - 1)) % 12,
        "右弼": (10 - (month - 1)) % 12,
        "天魁": kui,
        "天钺": yue,
    }


# ============================================================
# 六煞星：禄存(年干)→擎羊陀罗；地空地劫(时辰)；火星铃星(年支三合局+时辰)
# ============================================================
_LUCUN = {0: 2, 1: 3, 2: 5, 3: 6, 4: 5, 5: 6, 6: 8, 7: 9, 8: 11, 9: 0}
# 三合局起点：寅午戌/申子辰/巳酉丑/亥卯未，各组 (火星起点, 铃星起点)
_SANHE_GROUPS = [({2, 6, 10}, (1, 3)), ({8, 0, 4}, (2, 10)), ({5, 9, 1}, (3, 10)), ({11, 3, 7}, (9, 10))]


def liusha_stars(year_gan_idx, year_zhi_idx, time_idx):
    """六煞星：禄存定年干宫，擎羊陀罗前后各一；地空地劫自亥逆顺数生时；火铃自三合局起点顺数生时。"""
    lucun = _LUCUN[year_gan_idx]
    huo_start = ling_start = None
    for zhis, (h, l) in _SANHE_GROUPS:
        if year_zhi_idx in zhis:
            huo_start, ling_start = h, l
            break
    return {
        "禄存": lucun,
        "擎羊": (lucun + 1) % 12,
        "陀罗": (lucun - 1) % 12,
        "地劫": (11 + time_idx) % 12,
        "地空": (11 - time_idx) % 12,
        "火星": (huo_start + time_idx) % 12,
        "铃星": (ling_start + time_idx) % 12,
    }


# ============================================================
# 大限（方向=年干阴阳+性别）、小限（方向=仅性别）、流年
# ============================================================
def daxian_direction(year_gan, gender):
    """大限方向：阳年男/阴年女=顺行(+1)；阴年男/阳年女=逆行(-1)。"""
    yang = GAN_YINYANG[year_gan] == "阳"
    male = gender == "male"
    return 1 if (yang == male) else -1


def daxian_list(ju, ming_gong_idx, year_gan, gender, count=8):
    """大限：起运虚岁=局数，每十年一限，方向由年干阴阳+性别定。"""
    direction = daxian_direction(year_gan, gender)
    out = []
    for k in range(count):
        start_age, end_age = ju + 10 * k, ju + 10 * k + 9
        gong = (ming_gong_idx + direction * k) % 12
        out.append({"限": k + 1, "起": start_age, "止": end_age, "宫": gong})
    return out


# 小限起点：寅午戌年起辰、申子辰年起戌、巳酉丑年起未、亥卯未年起丑（仅按性别定方向，不看阴阳）
_XIAOXIAN_START = [({2, 6, 10}, 4), ({8, 0, 4}, 10), ({5, 9, 1}, 7), ({11, 3, 7}, 1)]


def xiaoxian_direction(gender):
    return 1 if gender == "male" else -1


def xiaoxian_gong(year_zhi_idx, gender, age):
    """小限：按生年地支三合分组定起点(1岁)，仅按性别定方向（男顺女逆，不看年干阴阳）。"""
    start = None
    for zhis, s in _XIAOXIAN_START:
        if year_zhi_idx in zhis:
            start = s
            break
    direction = xiaoxian_direction(gender)
    return (start + direction * (age - 1)) % 12


# ============================================================
# 主排盘
# ============================================================
def build_chart(y, mo, d, h, mi, gender, lunar=False):
    try:
        from lunar_python import Solar, Lunar
    except ImportError:
        sys.exit("缺少依赖 lunar_python，请先运行：pip3 install lunar_python")

    if not (YEAR_MIN <= y <= YEAR_MAX):
        sys.exit(f"年份超出支持范围：本引擎支持公历 {YEAR_MIN}-{YEAR_MAX} 年，收到 {y}。")
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        sys.exit("输入有误：时0-23、分0-59。")

    try:
        if lunar:
            if not (1 <= mo <= 12 or -12 <= mo <= -1):
                sys.exit("农历月须为 1-12，闰月用对应负数表示（如 -2=闰二月）。")
            lun = Lunar.fromYmdHms(y, mo, d, h, mi, 0)
        else:
            from datetime import datetime
            datetime(y, mo, d, h, mi)
            lun = Solar.fromYmdHms(y, mo, d, h, mi, 0).getLunar()
    except ValueError as e:
        sys.exit(f"日期非法：{e}")
    except Exception as e:
        sys.exit(f"起盘失败（请核对农历日期是否存在，留意小月与闰月）：{e}")

    year_gan, year_zhi = lun.getYearGan(), lun.getYearZhi()
    year_gan_idx, year_zhi_idx = GAN_IDX[year_gan], ZHI_IDX[year_zhi]
    month = abs(lun.getMonth())
    day = lun.getDay()
    time_zhi = lun.getTimeZhi()
    time_idx = ZHI_IDX[time_zhi]

    ming_gong_idx, shen_gong_idx = locate_ming_shen_gong(month, time_idx)
    palaces_idx = palace_order_from(ming_gong_idx)

    mg_gan_idx = ming_gong_gan(year_gan_idx, ming_gong_idx)
    mg_gan = GAN[mg_gan_idx]
    wx_name, ju = wuxing_ju(mg_gan_idx, ming_gong_idx)

    ziwei_idx = ziwei_position(ju, day)
    ziwei_stars = ziwei_star_group(ziwei_idx)
    tianfu_idx = tianfu_position(ziwei_idx)
    tianfu_stars = tianfu_star_group(tianfu_idx)
    major_stars = {**ziwei_stars, **tianfu_stars}

    sihua = SIHUA[year_gan]
    liuji = liuji_stars(year_gan_idx, month, time_idx)
    liusha = liusha_stars(year_gan_idx, year_zhi_idx, time_idx)

    daxian = daxian_list(ju, ming_gong_idx, year_gan, gender)
    xiaoxian_ages = {age: xiaoxian_gong(year_zhi_idx, gender, age) for age in range(1, 13)}

    # 逐宫汇总：宫名 -> {地支, 主星[], 四化[], 六吉[], 六煞[]}
    idx_to_palace = {v: k for k, v in palaces_idx.items()}
    gong_detail = {}
    for name, idx in palaces_idx.items():
        stars_here = [s for s, i in major_stars.items() if i == idx]
        jixing_here = [s for s, i in liuji.items() if i == idx]
        sha_here = [s for s, i in liusha.items() if i == idx]
        hua_here = [f"{star}{tag}" for tag, star in sihua.items() if major_stars.get(star) == idx]
        gan_here = GAN[ming_gong_gan(year_gan_idx, idx)]  # 五虎遁通排十二宫，非仅命宫
        gong_detail[name] = {
            "干支": gan_here + ZHI[idx], "地支": ZHI[idx], "主星": stars_here,
            "六吉": jixing_here, "六煞": sha_here, "四化": hua_here,
            "身宫": (idx == shen_gong_idx),
        }

    return {
        "version": __version__,
        "input": {"solar_or_lunar_input": "农历" if lunar else "公历",
                  "gender": "男" if gender == "male" else "女"},
        "lunar": {"年干支": year_gan + year_zhi, "月": month, "日": day, "时支": time_zhi},
        "命宫": {"地支": ZHI[ming_gong_idx], "干支": mg_gan + ZHI[ming_gong_idx]},
        "身宫": {"地支": ZHI[shen_gong_idx], "所在宫": idx_to_palace[shen_gong_idx]},
        "五行局": f"{wx_name}{ju}局",
        "紫微": ZHI[ziwei_idx], "天府": ZHI[tianfu_idx],
        "十二宫": gong_detail,
        "大限": [{"限": d_["限"], "起": d_["起"], "止": d_["止"], "宫": idx_to_palace[d_["宫"]]} for d_ in daxian],
        "小限(1-12岁)": {age: idx_to_palace[idx] for age, idx in xiaoxian_ages.items()},
    }


def render_text(c):
    L = []
    def P(s=""): L.append(s)
    P("════════════════════ 紫微斗数 · 命盘 ════════════════════")
    P(f"性别：{c['input']['gender']}　输入历法：{c['input']['solar_or_lunar_input']}")
    lu = c["lunar"]
    P(f"农历：{lu['年干支']}年 {lu['月']}月 {lu['日']}日 {lu['时支']}时")
    P(f"命宫：{c['命宫']['干支']}　身宫：{c['身宫']['地支']}（在{c['身宫']['所在宫']}）　五行局：{c['五行局']}")
    P(f"紫微：{c['紫微']}　天府：{c['天府']}")
    P("")
    P("【十二宫】")
    for name, d_ in c["十二宫"].items():
        tag = "　★身宫" if d_["身宫"] else ""
        stars = "、".join(d_["主星"]) or "（空宫）"
        extra = []
        if d_["四化"]:
            extra.append("四化:" + "、".join(d_["四化"]))
        if d_["六吉"]:
            extra.append("六吉:" + "、".join(d_["六吉"]))
        if d_["六煞"]:
            extra.append("六煞:" + "、".join(d_["六煞"]))
        extra_s = ("　" + "　".join(extra)) if extra else ""
        P(f"  {name}　{d_['干支']}　{stars}{extra_s}{tag}")
    P("")
    P("【大限】（起运虚岁=五行局数，方向由年干阴阳+性别定）")
    for d_ in c["大限"]:
        P(f"  第{d_['限']}限　{d_['起']}-{d_['止']}岁　{d_['宫']}")
    P("")
    P("【小限】（1-12岁，方向仅按性别，不看年干阴阳）")
    P("  " + "　".join(f"{age}岁:{name}" for age, name in c["小限(1-12岁)"].items()))
    P("══════════════════════════════════════════════════")
    P(f"紫微斗数安星引擎 v{c['version']}　命理参考，趋势化表达，不承诺祸福")
    return "\n".join(L)


def main():
    ap = argparse.ArgumentParser(description=f"紫微斗数安星引擎 v{__version__}")
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("day", type=int)
    ap.add_argument("hour", type=int)
    ap.add_argument("minute", type=int, nargs="?", default=0)
    ap.add_argument("--gender", choices=["male", "female"], required=True)
    ap.add_argument("--lunar", action="store_true",
                    help="输入按农历(默认阳历)；闰月用负数月，如 -2=闰二月")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"ziwei v{__version__}")
    args = ap.parse_args()

    chart = build_chart(args.year, args.month, args.day, args.hour, args.minute,
                        args.gender, lunar=args.lunar)
    if args.json:
        import json
        print(json.dumps(chart, ensure_ascii=False, indent=2))
    else:
        print(render_text(chart))


if __name__ == "__main__":
    main()
