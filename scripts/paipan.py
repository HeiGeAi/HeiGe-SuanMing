#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字排盘引擎 · HeiGe-SuanMing / bazi-mingli skill（版本见 __version__，--version 查看）
精确排四柱、藏干、十神、纳音、长生十二宫、五行力量、神煞、刑冲合会、大运、流年，
以及流月流日干支事实（--target-date）与合婚双盘对照（--partner）。

Required Notice: Copyright 2026 HeiGeAi (Blake Xu) (https://github.com/HeiGeAi)
License: PolyForm Noncommercial 1.0.0（完整条款见仓库根 LICENSE）

排盘核心依赖 lunar_python：自动以「立春」定年柱、以「节气」定月柱、处理农历闰月，
规避模型手推干支时最常犯的三类错误（年柱误用正月初一、月柱误用农历月、忽略真太阳时）。
支持公历年份范围：1600-2200。

安装：pip3 install lunar_python

用法：
  python3 paipan.py 1990 5 15 14 30 --gender male
  python3 paipan.py 1990 5 15 14 30 --gender female --json
  python3 paipan.py 1990 4 21 14 30 --gender male --lunar         # 按农历输入
  python3 paipan.py 2023 -2 15 14 30 --gender male --lunar        # 闰月用负数月：-2=闰二月
  python3 paipan.py 1990 5 15 14 30 --gender male --lng 113.3     # 经度→真太阳时校正
  python3 paipan.py 1990 5 15 14 30 --gender male --lng 139.7 --tz 9   # 海外出生地配时区
  python3 paipan.py 1990 5 15 14 30 --gender male --years 2024 12 # 从2024年起排12个流年
  python3 paipan.py 1990 5 15 14 30 --gender male --zi-sect 2     # 子时流派：不换日
  python3 paipan.py 1990 5 15 14 30 --gender male --target-date 2027 3 10   # 流月流日事实
  python3 paipan.py 1990 5 15 14 30 --gender male --partner 1992 8 20 10 30 --partner-gender female  # 合婚双盘
"""

import argparse
import json
import math
from datetime import datetime, timedelta, timezone

__version__ = "1.5.0"

# 支持的公历年份范围（lunar_python 节气与历表精度有保证的区间）
YEAR_MIN, YEAR_MAX = 1600, 2200

# ============================================================
# 基础常量
# ============================================================
GAN = "甲乙丙丁戊己庚辛壬癸"
ZHI = "子丑寅卯辰巳午未申酉戌亥"
SHENGXIAO = {"子": "鼠", "丑": "牛", "寅": "虎", "卯": "兔", "辰": "龙", "巳": "蛇",
             "午": "马", "未": "羊", "申": "猴", "酉": "鸡", "戌": "狗", "亥": "猪"}

GAN_WUXING = {"甲": "木", "乙": "木", "丙": "火", "丁": "火", "戊": "土",
              "己": "土", "庚": "金", "辛": "金", "壬": "水", "癸": "水"}
GAN_YINYANG = {"甲": "阳", "乙": "阴", "丙": "阳", "丁": "阴", "戊": "阳",
               "己": "阴", "庚": "阳", "辛": "阴", "壬": "阳", "癸": "阴"}
ZHI_WUXING = {"子": "水", "丑": "土", "寅": "木", "卯": "木", "辰": "土", "巳": "火",
              "午": "火", "未": "土", "申": "金", "酉": "金", "戌": "土", "亥": "水"}

# 地支藏干（本气, 中气, 余气）
ZHI_CANGGAN = {
    "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
    "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"], "未": ["己", "丁", "乙"],
    "申": ["庚", "壬", "戊"], "酉": ["辛"], "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
}

WUXING_SHENG = {"木": "火", "火": "土", "土": "金", "金": "水", "水": "木"}
WUXING_KE = {"木": "土", "土": "水", "水": "火", "火": "金", "金": "木"}

# 天干关系
GAN_HE = {frozenset("甲己"): "土", frozenset("乙庚"): "金", frozenset("丙辛"): "水",
          frozenset("丁壬"): "木", frozenset("戊癸"): "火"}
GAN_CHONG = [frozenset("甲庚"), frozenset("乙辛"), frozenset("丙壬"), frozenset("丁癸")]

# 地支关系
ZHI_LIUHE = {frozenset("子丑"): "土", frozenset("寅亥"): "木", frozenset("卯戌"): "火",
             frozenset("辰酉"): "金", frozenset("巳申"): "水", frozenset("午未"): "火/土"}
SANHE = {"申子辰": "水", "亥卯未": "木", "寅午戌": "火", "巳酉丑": "金"}  # 中神=combo[1]
SANHUI = {"寅卯辰": "木", "巳午未": "火", "申酉戌": "金", "亥子丑": "水"}
ZHI_CHONG = [frozenset("子午"), frozenset("丑未"), frozenset("寅申"),
             frozenset("卯酉"), frozenset("辰戌"), frozenset("巳亥")]
ZHI_HAI = [frozenset("子未"), frozenset("丑午"), frozenset("寅巳"),
           frozenset("卯辰"), frozenset("申亥"), frozenset("酉戌")]
XING3_A = set("寅巳申")   # 无恩之刑
XING3_B = set("丑戌未")   # 恃势之刑
XING_ZI = "辰午酉亥"      # 自刑（按固定次序遍历，保证输出顺序确定）
# 两支相刑成对表（与原局三刑的两支半刑同口径；寅申、丑未同时计冲与刑）
XING_PAIRS = [frozenset("子卯"), frozenset("寅巳"), frozenset("巳申"),
              frozenset("寅申"), frozenset("丑戌"), frozenset("戌未"), frozenset("丑未")]


def ten_god(day_gan, other_gan):
    dw, ow = GAN_WUXING[day_gan], GAN_WUXING[other_gan]
    same = GAN_YINYANG[day_gan] == GAN_YINYANG[other_gan]
    if ow == dw:
        return "比肩" if same else "劫财"
    if WUXING_SHENG[dw] == ow:
        return "食神" if same else "伤官"
    if WUXING_KE[dw] == ow:
        return "偏财" if same else "正财"
    if WUXING_KE[ow] == dw:
        return "七杀" if same else "正官"
    if WUXING_SHENG[ow] == dw:
        return "偏印" if same else "正印"
    return "?"


def zhi_ten_gods(day_gan, zhi):
    return [ten_god(day_gan, g) for g in ZHI_CANGGAN[zhi]]


# ============================================================
# 五行力量 / 个数
# ============================================================
def wuxing_strength(pillars, day_gan):
    score = {"木": 0.0, "火": 0.0, "土": 0.0, "金": 0.0, "水": 0.0}
    weights = [1.0, 0.5, 0.2]
    for idx, (gan, zhi) in enumerate(pillars):
        score[GAN_WUXING[gan]] += 1.0
        mult = 2.0 if idx == 1 else 1.0
        for i, g in enumerate(ZHI_CANGGAN[zhi]):
            w = weights[i] if i < len(weights) else 0.2
            score[GAN_WUXING[g]] += round(w * mult, 3)
    for k in score:
        score[k] = round(score[k], 2)

    dw = GAN_WUXING[day_gan]
    yin = next(k for k, v in WUXING_SHENG.items() if v == dw)
    guan = next(k for k, v in WUXING_KE.items() if v == dw)
    shang = WUXING_SHENG[dw]
    cai = WUXING_KE[dw]
    tong = round(score[dw] + score[yin], 2)
    yi = round(score[shang] + score[cai] + score[guan], 2)
    tong_d = f"比劫({dw}){score[dw]} + 印({yin}){score[yin]}"
    yi_d = f"食伤({shang}){score[shang]} + 财({cai}){score[cai]} + 官杀({guan}){score[guan]}"
    return score, tong, yi, tong_d, yi_d


def wuxing_count(pillars):
    """八字本字（四天干 + 四地支）五行个数与缺失五行。"""
    cnt = {"木": 0, "火": 0, "土": 0, "金": 0, "水": 0}
    for gan, zhi in pillars:
        cnt[GAN_WUXING[gan]] += 1
        cnt[ZHI_WUXING[zhi]] += 1
    lack = [k for k, v in cnt.items() if v == 0]
    return cnt, lack


# ============================================================
# 刑冲合会
# ============================================================
def detect_zhi_relations(pillars):
    labels = ["年", "月", "日", "时"][:len(pillars)]
    z = [p[1] for p in pillars]
    rel = {"六合": [], "三合": [], "半合": [], "三会": [], "六冲": [], "相刑": [], "六害": [], "自刑": []}

    for i in range(len(pillars)):
        for j in range(i + 1, len(pillars)):
            pair = frozenset([z[i], z[j]])
            tag = f"{labels[i]}{z[i]}·{labels[j]}{z[j]}"
            if z[i] != z[j] and pair in ZHI_LIUHE:
                rel["六合"].append(f"{tag}→合{ZHI_LIUHE[pair]}")
            if pair in ZHI_CHONG and z[i] != z[j]:
                rel["六冲"].append(tag)
            if pair in ZHI_HAI and z[i] != z[j]:
                rel["六害"].append(tag)
            if {z[i], z[j]} == set("子卯"):
                rel["相刑"].append(f"{tag}(子卯·无礼之刑)")

    # 三合 / 半合（半合需含中神）
    for combo, wx in SANHE.items():
        idxs = [k for k in range(len(pillars)) if z[k] in combo]
        chars = set(z[k] for k in idxs)
        who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
        if len(chars) == 3:
            rel["三合"].append(f"{combo}三合{wx}局({who})")
        elif len(chars) == 2 and combo[1] in chars:
            # 半合只列形成半合的两支，去重重复地支，避免把重复柱误列成三方
            _seen = set()
            pair_idxs = [k for k in idxs if not (z[k] in _seen or _seen.add(z[k]))]
            who2 = "·".join(f"{labels[k]}{z[k]}" for k in pair_idxs)
            rel["半合"].append(f"{combo[:3]}半合{wx}({who2})")
    # 三会
    for combo, wx in SANHUI.items():
        idxs = [k for k in range(len(pillars)) if z[k] in combo]
        if len(set(z[k] for k in idxs)) == 3:
            who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
            rel["三会"].append(f"{combo}三会{wx}方({who})")
    # 三刑（≥2字）
    for grp, name in ((XING3_A, "寅巳申·无恩之刑"), (XING3_B, "丑戌未·恃势之刑")):
        idxs = [k for k in range(len(pillars)) if z[k] in grp]
        chars = set(z[k] for k in idxs)
        if len(chars) >= 2:
            who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
            full = "三刑全" if len(chars) == 3 else "半刑"
            rel["相刑"].append(f"{name}({full}: {who})")
    # 自刑
    for zz in XING_ZI:
        idxs = [k for k in range(len(pillars)) if z[k] == zz]
        if len(idxs) >= 2:
            who = "·".join(labels[k] for k in idxs)
            rel["自刑"].append(f"{zz}{zz}自刑({who})")

    return {k: v for k, v in rel.items() if v}


def detect_gan_relations(pillars):
    labels = ["年", "月", "日", "时"][:len(pillars)]
    g = [p[0] for p in pillars]
    rel = {"天干五合": [], "天干相冲": []}
    for i in range(len(pillars)):
        for j in range(i + 1, len(pillars)):
            pair = frozenset([g[i], g[j]])
            tag = f"{labels[i]}{g[i]}·{labels[j]}{g[j]}"
            if pair in GAN_HE:
                rel["天干五合"].append(f"{tag}→合{GAN_HE[pair]}")
            if pair in GAN_CHONG:
                rel["天干相冲"].append(tag)
    return {k: v for k, v in rel.items() if v}


# ============================================================
# 神煞
# ============================================================
TIANYI = {"甲": "丑未", "戊": "丑未", "庚": "丑未", "乙": "子申", "己": "子申",
          "丙": "亥酉", "丁": "亥酉", "辛": "寅午", "壬": "卯巳", "癸": "卯巳"}
WENCHANG = {"甲": "巳", "乙": "午", "丙": "申", "丁": "酉", "戊": "申",
            "己": "酉", "庚": "亥", "辛": "子", "壬": "寅", "癸": "卯"}
LUSHEN = {"甲": "寅", "乙": "卯", "丙": "巳", "丁": "午", "戊": "巳",
          "己": "午", "庚": "申", "辛": "酉", "壬": "亥", "癸": "子"}
YANGREN = {"甲": "卯", "丙": "午", "戊": "午", "庚": "酉", "壬": "子"}
HONGYAN = {"甲": "午", "乙": "午", "丙": "寅", "丁": "未", "戊": "辰",
           "己": "辰", "庚": "戌", "辛": "酉", "壬": "子", "癸": "申"}
KUIGANG = {"庚辰", "庚戌", "壬辰", "戊戌"}
YUEDE = {"寅午戌": "丙", "申子辰": "壬", "亥卯未": "甲", "巳酉丑": "庚"}
GUACHEN = {  # 年支三会方 → (孤辰, 寡宿)
    "亥子丑": ("寅", "戌"), "寅卯辰": ("巳", "丑"),
    "巳午未": ("申", "辰"), "申酉戌": ("亥", "未"),
}

_SANHE = ["申子辰", "寅午戌", "巳酉丑", "亥卯未"]
TAOHUA = {"申子辰": "酉", "寅午戌": "卯", "巳酉丑": "午", "亥卯未": "子"}
YIMA = {"申子辰": "寅", "寅午戌": "申", "巳酉丑": "亥", "亥卯未": "巳"}
HUAGAI = {"申子辰": "辰", "寅午戌": "戌", "巳酉丑": "丑", "亥卯未": "未"}
JIANGXING = {"申子辰": "子", "寅午戌": "午", "巳酉丑": "酉", "亥卯未": "卯"}
TIANDE = {"寅": "丁", "卯": "申", "辰": "壬", "巳": "辛", "午": "亥", "未": "甲",
          "申": "癸", "酉": "寅", "戌": "丙", "亥": "乙", "子": "巳", "丑": "庚"}
# 天德按月支取，所得既可能是天干（如寅月丁）也可能是地支（卯月申、午月亥、酉月寅、子月巳），
# 干透天干、支见地支均算（references/06：按月支取对应天干/支透于四柱）。

# 神煞输出固定次序：按 references/06 吉神 → 动象中性 → 凶煞的传统排列
SHENSHA_ORDER = ["天乙贵人", "天德贵人", "月德贵人", "文昌贵人", "禄神", "将星", "金舆",
                 "驿马", "桃花", "华盖", "红艳", "羊刃", "魁罡", "孤辰", "寡宿"]
_PILLAR_ORDER = {"年": 0, "月": 1, "日": 2, "时": 3}


def _sanhe_of(zhi):
    for g in _SANHE:
        if zhi in g:
            return g
    return None


def _sanhui_of(zhi):
    for g in GUACHEN:
        if zhi in g:
            return g
    return None


def compute_shensha(pillars):
    labels = ["年", "月", "日", "时"]
    gans = [p[0] for p in pillars]
    zhis = [p[1] for p in pillars]
    day_gan, year_zhi, day_zhi, month_zhi = gans[2], zhis[0], zhis[2], zhis[1]
    res = {}

    def hit(name, target):
        found = [labels[i] for i, z in enumerate(zhis) if z in target]
        if found:
            res[name] = found

    hit("天乙贵人", set(TIANYI[day_gan]) | set(TIANYI[gans[0]]))
    hit("文昌贵人", {WENCHANG[day_gan]})
    hit("禄神", {LUSHEN[day_gan]})
    hit("红艳", {HONGYAN[day_gan]})
    hit("金舆", {ZHI[(ZHI.index(LUSHEN[day_gan]) + 2) % 12]})
    if day_gan in YANGREN:
        hit("羊刃", {YANGREN[day_gan]})

    # 天德贵人：按月支取，寅月丁等为天干（查四干），卯月申、午月亥、酉月寅、子月巳为地支（查四支）
    td = TIANDE.get(month_zhi)
    if td:
        if td in GAN:
            found = [labels[i] for i, g in enumerate(gans) if g == td]
        else:
            found = [labels[i] for i, z in enumerate(zhis) if z == td]
        if found:
            res["天德贵人"] = found
    for combo, yd in YUEDE.items():
        if month_zhi in combo and yd in gans:
            res["月德贵人"] = [labels[i] for i, g in enumerate(gans) if g == yd]
            break

    sh_year = _sanhui_of(year_zhi)
    if sh_year:
        gu, gua = GUACHEN[sh_year]
        hit("孤辰", {gu})
        hit("寡宿", {gua})

    if pillars[2][0] + pillars[2][1] in KUIGANG:
        res["魁罡"] = ["日"]

    # 年支为主、日支为辅，固定先后（避免 set 迭代顺序随哈希漂移）
    bases = [year_zhi] if year_zhi == day_zhi else [year_zhi, day_zhi]
    for base_zhi in bases:
        sh = _sanhe_of(base_zhi)
        if not sh:
            continue
        for name, table in (("桃花", TAOHUA), ("驿马", YIMA), ("华盖", HUAGAI), ("将星", JIANGXING)):
            tz = table[sh]
            for i, z in enumerate(zhis):
                if z == tz:
                    res.setdefault(name, [])
                    if labels[i] not in res[name]:
                        res[name].append(labels[i])

    # 输出确定性：神煞按传统次序（吉神→中性→凶煞），柱标按年月日时排序
    for name in res:
        res[name] = sorted(res[name], key=lambda x: _PILLAR_ORDER[x])
    return dict(sorted(res.items(),
                       key=lambda kv: SHENSHA_ORDER.index(kv[0]) if kv[0] in SHENSHA_ORDER else len(SHENSHA_ORDER)))


# ============================================================
# 真太阳时 / 长生
# ============================================================
def true_solar_time(dt, lng, tz_offset):
    n = dt.timetuple().tm_yday
    b = math.radians(360.0 * (n - 81) / 364.0)
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    longitude_delta = (lng - tz_offset * 15.0 + 180.0) % 360.0 - 180.0
    delta = longitude_delta * 4.0 + eot
    return dt + timedelta(minutes=delta), round(delta, 1)


_CHANGSHENG = {"甲": "亥", "丙": "寅", "戊": "寅", "庚": "巳", "壬": "申",
               "乙": "午", "丁": "酉", "己": "酉", "辛": "子", "癸": "卯"}
_CS_ORDER = ["长生", "沐浴", "冠带", "临官", "帝旺", "衰", "病", "死", "墓", "绝", "胎", "养"]


def _dishi_of(gan, zhi):
    start = _CHANGSHENG[gan]
    forward = GAN_YINYANG[gan] == "阳"
    si, zi = ZHI.index(start), ZHI.index(zhi)
    step = (zi - si) % 12 if forward else (si - zi) % 12
    return _CS_ORDER[step]


def _ming_shen_gong(year_gan, month_zhi, time_zhi):
    """用节气年月与真太阳时支组合计算命宫、身宫。"""
    month_order = "寅卯辰巳午未申酉戌亥子丑"
    month_index = month_order.index(month_zhi) + 1

    def ganzhi(offset):
        gan_index = ((GAN.index(year_gan) + 1) * 2 + offset - 1) % 10
        return GAN[gan_index] + month_order[offset - 1]

    ming_offset = month_index + month_order.index(time_zhi) + 1
    ming_offset = 26 - ming_offset if ming_offset >= 14 else 14 - ming_offset
    shen_offset = month_index + ZHI.index(time_zhi) + 1
    if shen_offset > 12:
        shen_offset -= 12
    return ganzhi(ming_offset), ganzhi(shen_offset)


# ============================================================
# 流年（与年柱同一套立春分界逻辑）
# ============================================================
def liunian_ganzhi(year):
    """公历年 year 对应的流年干支：取该年年中（必在立春后）的八字年柱，
    与本命年柱走同一套 lunar_python 立春分界逻辑。"""
    from lunar_python import Solar
    return Solar.fromYmd(year, 6, 1).getLunar().getEightChar().getYear()


def liunian_start_year(dt):
    """流年默认起始年：按立春分界。当前时刻若在本公历年立春之前，
    流年仍属上一干支年，起始年取 dt.year - 1。"""
    from lunar_python import Solar
    gz_now = Solar.fromYmdHms(dt.year, dt.month, dt.day, dt.hour,
                              dt.minute, dt.second).getLunar().getEightChar().getYear()
    return dt.year if gz_now == liunian_ganzhi(dt.year) else dt.year - 1


_BEIJING_TZ = timezone(timedelta(hours=8))


def _beijing_now(now=None):
    """将当前瞬间统一换算为 UTC+8 的无时区时刻，供立春分界使用。"""
    now = now or datetime.now(timezone.utc)
    return now.astimezone(_BEIJING_TZ).replace(tzinfo=None)


# ============================================================
# 流月 / 流日（断语止于月：引擎只出干支事实，每日吉凶留给方法论层，不做）
# ============================================================
def _zhi_vs_natal(ext_z, natal_zhis):
    """一个外来地支与原局四支的合冲害刑（流年/流月/流日引动原局的可计算事实）。"""
    labels = ["年", "月", "日", "时"]
    hits = []
    for i, nz in enumerate(natal_zhis):
        if ext_z == nz:
            if ext_z in XING_ZI:
                hits.append(f"自刑{labels[i]}{nz}")
            continue
        pair = frozenset([ext_z, nz])
        if pair in ZHI_LIUHE:
            hits.append(f"合{labels[i]}{nz}")
        if pair in ZHI_CHONG:
            hits.append(f"冲{labels[i]}{nz}")
        if pair in ZHI_HAI:
            hits.append(f"害{labels[i]}{nz}")
        if pair in XING_PAIRS:
            hits.append(f"刑{labels[i]}{nz}")
    return hits


def target_date_analysis(y, mo, d, day_gan, natal_zhis, zi_sect=None):
    """给定公历目标日，输出流年/流月/流日干支、十神、与原局四支的合冲害刑、流日旬空。
    流月以节气分界、流日与日柱同一套逻辑，与本命排盘口径一致。断语止于月由方法论层把关。
    干支按当日正午取；交节/立春当日前后归属不同，输出附边界提示。"""
    try:
        datetime(y, mo, d)
    except ValueError as e:
        raise ValueError(f"目标日期非法：{e}") from e
    if zi_sect not in (None, 1, 2):
        raise ValueError("zi_sect 须为 1 或 2。")
    try:
        from lunar_python import Solar
    except ImportError as e:
        raise RuntimeError("缺少依赖 lunar_python，请先运行：pip3 install lunar_python") from e
    ec = Solar.fromYmdHms(y, mo, d, 12, 0, 0).getLunar().getEightChar()
    if zi_sect:
        ec.setSect(zi_sect)
    out = {"date": f"{y}-{mo:02d}-{d:02d}", "liuri_xunkong": ec.getDayXunKong()}
    for key, gz in (("流年", ec.getYear()), ("流月", ec.getMonth()), ("流日", ec.getDay())):
        g, z = gz[0], gz[1]
        out[key] = {"ganzhi": gz, "gan_shen": ten_god(day_gan, g),
                    "zhi_shen": zhi_ten_gods(day_gan, z), "vs_natal": _zhi_vs_natal(z, natal_zhis)}
    # 交节/立春当日边界提示：日内首尾的年柱或月柱不一致，说明当天有换柱时刻
    ec0 = Solar.fromYmdHms(y, mo, d, 0, 0, 0).getLunar().getEightChar()
    ec1 = Solar.fromYmdHms(y, mo, d, 23, 59, 59).getLunar().getEightChar()
    if ec0.getYear() != ec1.getYear() or ec0.getMonth() != ec1.getMonth():
        out["边界提示"] = ("当日交节（或立春），流年流月归属以交节时刻为界前后不同；"
                       "此处按正午取值，临界时段请结合具体时辰核对。")
    return out


# ============================================================
# 合婚双盘对照（只出可计算的关系事实，不打分、不下「合/不合」判词）
# ============================================================
def _zhi_pair_desc(za, zb):
    pair = frozenset([za, zb])
    if za == zb:
        if za in XING_ZI:
            return f"同为 {za}（同气，带自刑）"
        return f"同为 {za}（同气）"
    relations = []
    if pair in ZHI_LIUHE:
        relations.append(f"{za}{zb} 六合（合{ZHI_LIUHE[pair]}）")
    for combo, wx in SANHE.items():
        if za in combo and zb in combo:
            # 与 detect_zhi_relations 同口径：含中神才算半合，无中神只作拱合
            if combo[1] in (za, zb):
                relations.append(f"{za}{zb} 半合{wx}局")
            else:
                relations.append(f"{za}{zb} 拱{wx}（无中神，联系弱）")
            break
    if pair in ZHI_CHONG:
        relations.append(f"{za}{zb} 相冲")
    if pair in XING_PAIRS and pair in ZHI_HAI:
        relations.append(f"{za}{zb} 相刑兼相害")
    elif pair in XING_PAIRS:
        relations.append(f"{za}{zb} 相刑")
    elif pair in ZHI_HAI:
        relations.append(f"{za}{zb} 相害")
    return "，".join(relations) if relations else f"{za} / {zb}（无合冲害刑）"


def compatibility(ca, cb):
    """双盘可计算关系事实：日干、夫妻宫(日支)、生肖(年支)、五行缺与个数。
    只列事实，互补与相处判断由 references/17 方法论推演，引擎不打分、不下合不合判词。"""
    da_g, da_z = ca["pillars"]["日"][0], ca["pillars"]["日"][1]
    db_g, db_z = cb["pillars"]["日"][0], cb["pillars"]["日"][1]
    ya_z, yb_z = ca["pillars"]["年"][1], cb["pillars"]["年"][1]
    res = {}
    gpair = frozenset([da_g, db_g])
    if da_g == db_g:
        res["日干"] = f"同为 {da_g} 日主（同类，性情相近）"
    elif gpair in GAN_HE:
        res["日干"] = f"{da_g}{db_g} 天干五合化{GAN_HE[gpair]}（相吸）"
    elif gpair in GAN_CHONG:
        res["日干"] = f"{da_g}{db_g} 天干相冲（个性易相左）"
    else:
        res["日干"] = f"{da_g} / {db_g}（无合冲）"
    res["夫妻宫(日支)"] = _zhi_pair_desc(da_z, db_z)
    res["生肖(年支)"] = _zhi_pair_desc(ya_z, yb_z)
    la, lb = ca.get("wuxing_lack", []), cb.get("wuxing_lack", [])
    res["五行缺"] = f"甲方缺 {('、'.join(la) or '无')}；乙方缺 {('、'.join(lb) or '无')}"
    def _fmt(counts):
        return " ".join(f"{key}{value}" for key, value in counts.items())
    res["五行个数"] = f"甲方 {_fmt(ca['wuxing_count'])}；乙方 {_fmt(cb['wuxing_count'])}"
    return res


# ============================================================
# 中国夏令时（1986-1991 实施，每年约 4-9 月钟表较北京标准时快 1 小时）
# ============================================================
_CHINA_DST = {1986: ((5, 4), (9, 14)), 1987: ((4, 12), (9, 13)), 1988: ((4, 17), (9, 11)),
              1989: ((4, 16), (9, 17)), 1990: ((4, 15), (9, 16)), 1991: ((4, 14), (9, 15))}


def china_dst_note(y, mo, d):
    """出生落在中国 1986-1991 夏令时实施期时，提示核对钟表时间是否已含夏令时。
    起止两个边界日切换发生在当日凌晨 2 时，单独给方向提示。"""
    win = _CHINA_DST.get(y)
    if not win:
        return None
    (sm, sd), (em, ed) = win
    if (mo, d) == (sm, sd):
        return (f"{y}-{sm}/{sd} 为该年夏令时开始日，当日凌晨 2 时起钟表拨快 1 小时；"
                f"2:00至2:59 的当地钟表时间不存在；3 时后所记钟表时间应减 1 小时再定时柱，请核对。")
    if (mo, d) == (em, ed):
        return (f"{y}-{em}/{ed} 为该年夏令时结束日，当日凌晨 2 时钟表回拨 1 小时；"
                f"00:00至00:59 为夏令时，所记钟表时间应减 1 小时；"
                f"01:00至01:59重复出现，第一次为夏令时需减 1 小时，"
                f"第二次为标准时不调整，须核对当时记录口径；02:00 后为标准时不调整。")
    if (sm, sd) < (mo, d) < (em, ed):
        return (f"出生于 {y} 年中国夏令时实施期（{sm}/{sd}–{em}/{ed}，钟表较北京标准时快 1 小时）。"
                f"若所记为当时钟表时间，真实时间应减 1 小时再定时柱，请核对。")
    return None


# ============================================================
# 主排盘
# ============================================================
def build_chart(args):
    validate_args(args)
    try:
        from lunar_python import Solar, Lunar
    except ImportError as e:
        raise RuntimeError("缺少依赖 lunar_python，请先运行：pip3 install lunar_python") from e

    hour_known = args.hour is not None
    y, mo, d = args.year, args.month, args.day
    h, mi = (args.hour, args.minute) if hour_known else (12, 0)
    corr_note = None

    if args.lunar:
        try:
            lunar_input = Lunar.fromYmdHms(y, mo, d, h, mi, 0)
            converted = lunar_input.getSolar()
        except Exception as e:
            raise ValueError(f"农历转换失败：{e}") from e
        y, mo, d, h, mi = (converted.getYear(), converted.getMonth(), converted.getDay(),
                           converted.getHour(), converted.getMinute())
        if not (YEAR_MIN <= y <= YEAR_MAX):
            raise ValueError(f"农历转换后的公历年份超出支持范围 {YEAR_MIN}-{YEAR_MAX}：{y}。")

    # 公历输入（农历则为转换后的公历），展示用，真太阳时校正不覆盖它
    local_dt = datetime(y, mo, d, h, mi)
    input_solar_str = (f"{y}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}" if hour_known
                       else f"{y}-{mo:02d}-{d:02d}（时辰未知）")
    true_solar_str = None
    china_dst = bool(getattr(args, "china_dst", False))
    dst_note = china_dst_note(y, mo, d) if china_dst else None

    # lunar_python 的节气时刻以 UTC+8 表达；年柱、月柱按同一真实瞬间换算，
    # 不受后面的经度真太阳时校正影响。
    boundary_dt = local_dt + timedelta(hours=8.0 - args.tz)
    if not (YEAR_MIN <= boundary_dt.year <= YEAR_MAX):
        raise ValueError(f"时区转换后的公历年份超出支持范围 {YEAR_MIN}-{YEAR_MAX}：{boundary_dt.year}。")

    apparent_dt = local_dt

    # 农历输入先转公历（上方已转），再做真太阳时校正，两者可叠加
    if args.lng is not None:
        apparent_dt, delta = true_solar_time(local_dt, args.lng, args.tz)
        if not (YEAR_MIN <= apparent_dt.year <= YEAR_MAX):
            raise ValueError(f"真太阳时校正后的公历年份超出支持范围 {YEAR_MIN}-{YEAR_MAX}：{apparent_dt.year}。")
        true_solar_str = apparent_dt.strftime("%Y-%m-%d %H:%M")
        corr_note = f"经度{args.lng}°、时区UTC{args.tz:+} → 真太阳时校正 {delta:+} 分钟"
        if abs(delta) > 120:
            corr_note += "　※ 强提示：校正幅度超过 ±120 分钟，请核对经度与时区（--tz）是否匹配"
    elif args.tz != 8.0:
        corr_note = (f"已指定时区 UTC{args.tz:+} 但未提供经度（--lng），真太阳时未校正；"
                     "--tz 需与 --lng 配合方可校正时柱。")

    local_solar = Solar.fromYmdHms(local_dt.year, local_dt.month, local_dt.day,
                                   local_dt.hour, local_dt.minute, 0)
    boundary_solar = Solar.fromYmdHms(boundary_dt.year, boundary_dt.month, boundary_dt.day,
                                      boundary_dt.hour, boundary_dt.minute, boundary_dt.second)
    apparent_solar = Solar.fromYmdHms(apparent_dt.year, apparent_dt.month, apparent_dt.day,
                                      apparent_dt.hour, apparent_dt.minute, 0)
    boundary_lunar = boundary_solar.getLunar()
    lunar = apparent_solar.getLunar()
    ec_boundary = boundary_lunar.getEightChar()
    ec_apparent = lunar.getEightChar()
    if args.zi_sect:
        ec_boundary.setSect(args.zi_sect)
        ec_apparent.setSect(args.zi_sect)
    effective_zi_sect = ec_apparent.getSect() if hour_known else None

    pillar_uncertainty = {}
    if not hour_known:
        endpoint_pillars = []
        for endpoint in (datetime(y, mo, d, 0, 0), datetime(y, mo, d, 23, 59, 59)):
            endpoint = endpoint + timedelta(hours=8.0 - args.tz)
            if not (YEAR_MIN <= endpoint.year <= YEAR_MAX):
                raise ValueError(f"时辰未知日期的时区转换可能落在支持范围外：{endpoint.year}。")
            endpoint_ec = Solar.fromYmdHms(endpoint.year, endpoint.month, endpoint.day,
                                           endpoint.hour, endpoint.minute, endpoint.second).getLunar().getEightChar()
            endpoint_pillars.append({"年": endpoint_ec.getYear(), "月": endpoint_ec.getMonth()})
        for key in ("年", "月"):
            values = list(dict.fromkeys(item[key] for item in endpoint_pillars))
            if len(values) > 1:
                pillar_uncertainty[key] = values

    ganzhi = {"年": ec_boundary.getYear(), "月": ec_boundary.getMonth(), "日": ec_apparent.getDay()}
    if hour_known:
        ganzhi["时"] = ec_apparent.getTime()
    keys = list(ganzhi)
    pillars = [(ganzhi[k][0], ganzhi[k][1]) for k in keys]
    day_gan = pillars[2][0]
    month_zhi = pillars[1][1]

    nayin = {"年": ec_boundary.getYearNaYin(), "月": ec_boundary.getMonthNaYin(),
             "日": ec_apparent.getDayNaYin()}
    xunkong = {"年": ec_boundary.getYearXunKong(), "月": ec_boundary.getMonthXunKong(),
               "日": ec_apparent.getDayXunKong()}
    if hour_known:
        nayin["时"] = ec_apparent.getTimeNaYin()
        xunkong["时"] = ec_apparent.getTimeXunKong()
    dishi = {k: _dishi_of(day_gan, pillars[i][1]) for i, k in enumerate(keys)}
    gan_shen = {k: ("日主" if k == "日" else ten_god(day_gan, pillars[i][0]))
                for i, k in enumerate(keys)}
    zhi_shen = {k: zhi_ten_gods(day_gan, pillars[i][1]) for i, k in enumerate(keys)}

    score, tong, yi, tong_d, yi_d = wuxing_strength(pillars, day_gan)
    cnt, lack = wuxing_count(pillars)
    shensha = compute_shensha(pillars)
    zhi_rel = detect_zhi_relations(pillars)
    gan_rel = detect_gan_relations(pillars)

    natal_zhis = [pillar[1] for pillar in pillars]
    target = None
    if getattr(args, "target_date", None):
        ty, tm, td_ = args.target_date[0], args.target_date[1], args.target_date[2]
        target = target_date_analysis(ty, tm, td_, day_gan, natal_zhis, args.zi_sect)

    # 节气
    jieqi = None
    try:
        pj, nj = boundary_lunar.getPrevJieQi(), boundary_lunar.getNextJieQi()
        bd = datetime(boundary_solar.getYear(), boundary_solar.getMonth(), boundary_solar.getDay())
        ps = pj.getSolar()
        pdt = datetime(ps.getYear(), ps.getMonth(), ps.getDay())
        jieqi = f"{pj.getName()}（{ps.toYmd()}）后第 {(bd - pdt).days} 天，下一节气 {nj.getName()}"
    except Exception:
        pass

    # 大运
    gender_int = 1 if args.gender == "male" else 0
    year_yang = GAN_YINYANG[pillars[0][0]] == "阳"
    forward = (year_yang and gender_int == 1) or (not year_yang and gender_int == 0)
    dayun_list = []
    start_age_xu = None
    start_solar = None
    if hour_known:
        yun = ec_boundary.getYun(gender_int)
        yun_start = yun.getStartSolar()
        yun_start_boundary = datetime(yun_start.getYear(), yun_start.getMonth(), yun_start.getDay(),
                                      yun_start.getHour(), yun_start.getMinute(), yun_start.getSecond())
        yun_start_local = yun_start_boundary.replace(tzinfo=timezone(timedelta(hours=8))).astimezone(
            timezone(timedelta(hours=args.tz))).replace(tzinfo=None)
        first_start_year = yun_start_local.year
        major_index = 0
        for dy in yun.getDaYun():
            gz = dy.getGanZhi()
            if not gz:
                if first_start_year > local_dt.year:
                    dayun_list.append({"start_age": 1,
                                       "end_age": first_start_year - local_dt.year,
                                       "start_year": local_dt.year,
                                       "ganzhi": "", "note": "幼运(未上大运)"})
                continue
            g, z = gz[0], gz[1]
            dy_start_year = first_start_year + major_index * 10
            dy_start_age = dy_start_year - local_dt.year + 1
            dayun_list.append({"start_age": dy_start_age, "end_age": dy_start_age + 9,
                               "start_year": dy_start_year, "ganzhi": gz,
                               "gan_shen": ten_god(day_gan, g), "zhi_shen": zhi_ten_gods(day_gan, z),
                               "dishi": _dishi_of(day_gan, z)})
            major_index += 1
        first_dayun = next((dy for dy in dayun_list if dy["ganzhi"]), None)
        start_age_xu = first_dayun["start_age"] if first_dayun else first_start_year - local_dt.year + 1
        start_solar = yun_start_local.strftime("%Y-%m-%d")

    # 流年：干支与年柱同一套立春分界逻辑；默认起始年也按立春定（立春前属上一干支年）
    if args.years:
        start_year, span = args.years
    else:
        start_year = max(liunian_start_year(_beijing_now()), local_solar.getYear())
        span = min(10, YEAR_MAX - start_year + 1)
    liunian = []
    for yy in range(start_year, start_year + span):
        gz = liunian_ganzhi(yy)
        g, z = gz[0], gz[1]
        liunian.append({"year": yy, "ganzhi": gz, "gan_shen": ten_god(day_gan, g),
                        "zhi_shen": zhi_ten_gods(day_gan, z), "age": yy - local_solar.getYear() + 1})

    limitations = None
    if not hour_known:
        limitations = ("时辰未知：年、月、日三柱按当日正午参考值排出；时柱、命宫、身宫、"
                       "时支神煞缺失，不输出精确起运时间与大运列表。"
                       "若实际出生在 23 时且采用晚子换日口径，日柱亦可能变化。")
        if pillar_uncertainty:
            details = "、".join(f"{key}柱可能为{'/'.join(values)}"
                                 for key, values in pillar_uncertainty.items())
            limitations += f"当日交节，{details}，正午值不代表全天唯一结果。"
    minggong, shengong = (_ming_shen_gong(ganzhi["年"][0], ganzhi["月"][1], ganzhi["时"][1])
                           if hour_known else (None, None))

    return {
        "version": __version__,
        "disclaimer": "本排盘与推演仅供传统文化研究与自我认知参考，不构成对命运、健康、婚姻、财富的预言或保证。",
        "input": {
            "calendar": "农历" if args.lunar else "公历",
            "solar": input_solar_str,
            "true_solar": true_solar_str,
            "lunar": lunar.toString(), "shengxiao": SHENGXIAO[pillars[0][1]],
            "xingzuo": local_solar.getXingZuo(), "gender": "男" if gender_int else "女",
            "jieqi": jieqi, "correction": corr_note, "dst_note": dst_note,
            "china_dst": china_dst,
            "hour_known": hour_known, "zi_sect": effective_zi_sect,
            "lng": args.lng, "tz": args.tz,
            "solar_term_time": boundary_dt.strftime(
                "%Y-%m-%d %H:%M:%S" if boundary_dt.second else "%Y-%m-%d %H:%M") + " UTC+8",
            "pillar_time_basis": None if hour_known else "当日正午参考值",
            "pillar_uncertainty": pillar_uncertainty,
            "limitations": limitations,
        },
        "pillars": ganzhi, "day_master": f"{day_gan}{GAN_WUXING[day_gan]}",
        "gan_shen": gan_shen, "zhi_canggan": {k: ZHI_CANGGAN[pillars[i][1]] for i, k in enumerate(keys)},
        "zhi_shen": zhi_shen, "nayin": nayin, "dishi": dishi, "xunkong": xunkong,
        "month_ling": f"{month_zhi}（{ZHI_WUXING[month_zhi]}）",
        "wuxing_score": score, "wuxing_count": cnt, "wuxing_lack": lack,
        "tong_dang": tong, "yi_dang": yi, "tong_detail": tong_d, "yi_detail": yi_d,
        "zhi_relations": zhi_rel, "gan_relations": gan_rel, "shensha": shensha,
        "taiyuan": ec_boundary.getTaiYuan(),
        "minggong": minggong, "shengong": shengong,
        "yun_direction": "顺排" if forward else "逆排",
        "start_age": start_age_xu, "start_solar": start_solar,
        "dayun": dayun_list, "liunian": liunian,
        "target_date": target,
    }


# ============================================================
# 文本渲染
# ============================================================
def render_text(c, *, include_partner=True):
    out = []
    def P(s=""): out.append(s)
    inp = c["input"]
    cols = list(c["pillars"])
    hour_known = c["input"].get("hour_known", "时" in cols)
    partner_chart = c.get("partner_chart") if include_partner else None
    if partner_chart:
        P("【甲方命盘】")
    P("════════════════════ 八字命盘 ════════════════════")
    P(f"公历：{inp['solar']}　性别：{inp['gender']}　生肖：{inp['shengxiao']}　星座：{inp['xingzuo']}")
    if inp.get("true_solar"):
        P(f"真太阳时：{inp['true_solar']}（按经度校正日柱、时柱；年月仍以节气瞬间为界）")
    P(f"农历：{inp['lunar']}")
    if inp["jieqi"]:
        P(f"节气：{inp['jieqi']}")
    if inp["correction"]:
        P(f"校正：{inp['correction']}")
    if inp.get("dst_note"):
        P(f"夏令时：{inp['dst_note']}")
    sect = inp.get("zi_sect") if hour_known else "不适用"
    lng = inp.get("lng")
    lng_text = f"{lng}°" if lng is not None else "未提供"
    P(f"排盘口径：子时流派={sect}；经度={lng_text}；时区=UTC{inp.get('tz', 8.0):+}；"
      f"节气比对时刻={inp.get('solar_term_time', '未记录')}")
    if inp.get("limitations"):
        P(f"局限：{inp['limitations']}")
    P("")
    P(("【四柱】" if hour_known else "【三柱】") + "     " + "    ".join(f"{k}柱" for k in cols))
    P("  天干十神   " + "  ".join(f"{c['gan_shen'][k]:<4}" for k in cols))
    P("  天干       " + "    ".join(f"{c['pillars'][k][0]}({GAN_WUXING[c['pillars'][k][0]]})" for k in cols))
    P("  地支       " + "    ".join(f"{c['pillars'][k][1]}({ZHI_WUXING[c['pillars'][k][1]]})" for k in cols))
    P("  藏干       " + "  ".join(f"{''.join(c['zhi_canggan'][k]):<5}" for k in cols))
    P("  藏干十神   " + " ".join("/".join(c['zhi_shen'][k]) + "  " for k in cols))
    P("  星运       " + "    ".join(f"{c['dishi'][k]:<4}" for k in cols))
    P("  纳音       " + "  ".join(f"{c['nayin'][k]:<5}" for k in cols))
    P("  旬空       " + "    ".join(f"{c['xunkong'][k]:<4}" for k in cols))
    P("")
    P(f"【日主】{c['day_master']}，生于 {c['month_ling']} 月令")
    if hour_known:
        P(f"【胎元】{c['taiyuan']}　【命宫】{c['minggong']}　【身宫】{c['shengong']}")
    else:
        P(f"【胎元】{c['taiyuan']}　【命宫】未排　【身宫】未排（时辰未知）")
    P("")
    if c["gan_relations"]:
        P("【天干关系】" + "　".join(f"{k}: {'，'.join(v)}" for k, v in c["gan_relations"].items()))
    if c["zhi_relations"]:
        P("【地支刑冲合会】")
        for k, v in c["zhi_relations"].items():
            P(f"  {k}：{'，'.join(v)}")
    if c["gan_relations"] or c["zhi_relations"]:
        P("")
    P("【五行个数】" + "　".join(f"{k}{v}" for k, v in c["wuxing_count"].items())
      + (f"　｜缺：{'、'.join(c['wuxing_lack'])}" if c["wuxing_lack"] else "　｜五行俱全"))
    P("【五行力量】（天干1 / 藏干本气1·中气0.5·余气0.2 / 月支司令×2）")
    P("  " + "  ".join(f"{k}:{v}" for k, v in c["wuxing_score"].items()))
    P(f"  同党(扶日主)={c['tong_dang']}  [{c['tong_detail']}]")
    P(f"  异党(耗日主)={c['yi_dang']}  [{c['yi_detail']}]")
    tot = c['tong_dang'] + c['yi_dang']
    ratio = c['tong_dang'] / tot if tot else 0
    tip = "偏强" if ratio > 0.55 else ("偏弱" if ratio < 0.45 else "均势(需细辨)")
    P(f"  同党占比 {ratio:.0%} → 量化参考：{tip}（最终旺衰须结合月令得失·通根透干·刑冲合会综合判断）")
    P("")
    if c["shensha"]:
        P("【神煞】" + "　".join(f"{k}({'·'.join(v)})" for k, v in c["shensha"].items()))
        P("")
    if hour_known:
        P(f"【大运】{c['yun_direction']}　{c['start_age']}岁起运（虚岁，{c['start_solar']}）")
        for dy in c["dayun"]:
            if not dy["ganzhi"]:
                P(f"  幼运 {dy['start_age']}-{dy['end_age']}岁（{dy['start_year']}-）")
                continue
            P(f"  {dy['ganzhi']}　{dy['start_age']:>2}-{dy['end_age']:>2}岁　{dy['start_year']}年起"
              f"　[{dy['gan_shen']}/{'/'.join(dy['zhi_shen'])}]　星运:{dy['dishi']}")
    else:
        P(f"【大运】{c['yun_direction']}；时辰未知，不输出精确起运时间与大运列表。")
    P("")
    P(f"【流年】{c['liunian'][0]['year']}-{c['liunian'][-1]['year']}")
    for ln in c["liunian"]:
        P(f"  {ln['year']}（虚{ln['age']}岁）{ln['ganzhi']}　[{ln['gan_shen']}/{'/'.join(ln['zhi_shen'])}]")
    if c.get("target_date"):
        td = c["target_date"]
        P("")
        P(f"【指定日推演】{td['date']}（断语止于月，流日仅列干支事实）")
        for key in ("流年", "流月", "流日"):
            t = td[key]
            vs = ("　引动：" + "，".join(t["vs_natal"])) if t["vs_natal"] else ""
            P(f"  {key} {t['ganzhi']}　[{t['gan_shen']}/{'/'.join(t['zhi_shen'])}]{vs}")
        P(f"  流日旬空：{td['liuri_xunkong']}")
        if td.get("边界提示"):
            P(f"  ※ {td['边界提示']}")
    if partner_chart:
        P("")
        P("【乙方命盘】")
        # 只渲染乙方本盘，忽略其潜在的合婚字段，避免嵌套或循环展示。
        P(render_text(partner_chart, include_partner=False))
    if include_partner and c.get("compatibility"):
        P("")
        P("【合婚双盘对照】（关系事实，不打分、不下合不合判词，判断见 references/17）")
        if c.get("partner_pillars"):
            pp = c["partner_pillars"]
            partner_input = c.get("partner_input", {})
            basis = "已做真太阳时校正" if partner_input.get("true_solar") else "未做真太阳时校正"
            cal = f"（{c['partner_calendar']}输入，{basis}）" if c.get("partner_calendar") else ""
            P(f"  乙方{'四' if len(pp) == 4 else '三'}柱：" + "  ".join(pp.values()) + cal)
            if partner_input.get("limitations"):
                P(f"  乙方局限：{partner_input['limitations']}")
        if c.get("partner_yun"):
            P(f"  乙方大运：{c['partner_yun']}")
        if c.get("partner_dst_note"):
            P(f"  乙方夏令时：{c['partner_dst_note']}")
        for k, v in c["compatibility"].items():
            P(f"  {k}：{v}")
    P("══════════════════════════════════════════════════")
    P(f"排盘引擎 v{c['version']}　仅供传统文化研究与自我认知参考")
    return "\n".join(out)


def _span_int(s):
    v = int(s)
    if v < 1:
        raise argparse.ArgumentTypeError(f"须为 ≥1 的整数，收到 {s}")
    return v


def validate_args(args):
    """输入校验：年份范围、经度范围、流年区间、公历/农历日期合法性（含闰月与小月）。"""
    # 前一农历年腊月可能落在公历下界内；最终支持范围在转换后核验。
    input_year_min = YEAR_MIN - 1 if getattr(args, "lunar", False) else YEAR_MIN
    if not (input_year_min <= args.year <= YEAR_MAX):
        raise ValueError(f"年份超出支持范围：本引擎支持公历 {YEAR_MIN}-{YEAR_MAX} 年，收到 {args.year}。")
    if getattr(args, "gender", None) not in ("male", "female"):
        raise ValueError("gender 须为 male 或 female。")

    hour = getattr(args, "hour", None)
    minute = getattr(args, "minute", 0)
    lng = getattr(args, "lng", None)
    tz = getattr(args, "tz", 8.0)
    zi_sect = getattr(args, "zi_sect", None)
    if zi_sect not in (None, 1, 2):
        raise ValueError("zi_sect 须为 1 或 2。")
    if hour is None:
        if minute not in (None, 0):
            raise ValueError("时辰未知时不能单独提供分钟。")
        if lng is not None:
            raise ValueError("时辰未知时无法进行真太阳时校正，请移除 --lng 或补充时辰。")
        if zi_sect is not None:
            raise ValueError("时辰未知时 zi_sect 不适用。")
    elif not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError("输入有误：时0-23、分0-59。")

    if not math.isfinite(tz) or not (-12.0 <= tz <= 14.0):
        raise ValueError(f"时区超出范围：--tz 须为 -12 ~ +14 之间的有限数，收到 {tz}。")
    if lng is not None and (not math.isfinite(lng) or not (-180.0 <= lng <= 180.0)):
        raise ValueError(f"经度超出范围：--lng 须在 -180 ~ 180 之间（东经为正、西经为负），收到 {lng}。")
    years = getattr(args, "years", None)
    if years is not None:
        if not isinstance(years, (tuple, list)) or len(years) != 2:
            raise ValueError("--years 须为「起始年、年数」两个整数。")
        start_year, span = years
        if (isinstance(start_year, bool) or isinstance(span, bool)
                or not isinstance(start_year, int) or not isinstance(span, int)):
            raise ValueError("--years 起始年与年数均须为整数。")
        if span < 1:
            raise ValueError("--years 年数须为 ≥1 的整数。")
        if not (YEAR_MIN <= start_year and start_year + span - 1 <= YEAR_MAX):
            raise ValueError(f"流年区间超出支持范围：--years 须落在公历 {YEAR_MIN}-{YEAR_MAX} 年内。")

    partner = getattr(args, "partner", None)
    partner_lunar = getattr(args, "partner_lunar", False)
    partner_gender = getattr(args, "partner_gender", None)
    partner_china_dst = getattr(args, "partner_china_dst", False)
    partner_lng = getattr(args, "partner_lng", None)
    partner_tz = getattr(args, "partner_tz", None)
    if partner is None and (partner_lunar or partner_gender is not None or partner_china_dst
                            or partner_lng is not None or partner_tz is not None):
        raise ValueError("乙方选项须与 --partner 一起使用。")
    if partner is not None:
        if not (3 <= len(partner) <= 5):
            raise ValueError("--partner 需 年 月 日 [时] [分]，如 --partner 1992 8 15 10 0")
        py_, pm_, pd_ = partner[:3]
        ph_ = partner[3] if len(partner) >= 4 else None
        pmi_ = partner[4] if len(partner) == 5 else 0
        partner_year_min = YEAR_MIN - 1 if partner_lunar else YEAR_MIN
        if not (partner_year_min <= py_ <= YEAR_MAX):
            raise ValueError(f"合婚第二人年份超出支持范围：本引擎支持公历 {YEAR_MIN}-{YEAR_MAX} 年。")
        if ph_ is not None and not (0 <= ph_ <= 23 and 0 <= pmi_ <= 59):
            raise ValueError("合婚第二人时间有误：时0-23、分0-59。")
        if partner_lunar:
            if not (1 <= pm_ <= 12 or -12 <= pm_ <= -1):
                raise ValueError("合婚第二人农历月须为 1-12，闰月用对应负数表示（如 -2=闰二月）。")
            if not (1 <= pd_ <= 30):
                raise ValueError("合婚第二人农历日须为 1-30。")
            try:
                from lunar_python import LunarMonth
            except ImportError as e:
                raise RuntimeError("缺少依赖 lunar_python，请先运行：pip3 install lunar_python") from e
            pmdesc = f"闰{-pm_}月" if pm_ < 0 else f"{pm_}月"
            plm = LunarMonth.fromYm(py_, pm_)
            if plm is None:
                raise ValueError(f"合婚第二人：农历 {py_} 年没有{pmdesc}，请核对。")
            if pd_ > plm.getDayCount():
                raise ValueError(f"合婚第二人：农历 {py_} 年{pmdesc}是小月，只有 {plm.getDayCount()} 天，没有 {pd_} 日。")
        else:
            try:
                datetime(py_, pm_, pd_, ph_ if ph_ is not None else 12, pmi_)
            except ValueError as e:
                raise ValueError(f"合婚第二人日期非法：{e}") from e
    if getattr(args, "target_date", None) is not None:
        ty, tm, tdd = args.target_date
        if not (YEAR_MIN <= ty <= YEAR_MAX):
            raise ValueError(f"--target-date 年份超出支持范围：本引擎支持公历 {YEAR_MIN}-{YEAR_MAX} 年。")
        try:
            datetime(ty, tm, tdd)
        except ValueError as e:
            raise ValueError(f"--target-date 日期非法：{e}") from e

    if getattr(args, "lunar", False):
        if not (1 <= args.month <= 12 or -12 <= args.month <= -1):
            raise ValueError("农历月须为 1-12，闰月用对应负数表示（如 -2=闰二月）。")
        if not (1 <= args.day <= 30):
            raise ValueError("农历日须为 1-30。")
        try:
            from lunar_python import LunarMonth
        except ImportError as e:
            raise RuntimeError("缺少依赖 lunar_python，请先运行：pip3 install lunar_python") from e
        mdesc = f"闰{-args.month}月" if args.month < 0 else f"{args.month}月"
        lm = LunarMonth.fromYm(args.year, args.month)
        if lm is None:
            raise ValueError(f"农历 {args.year} 年没有{mdesc}，请核对（闰月用负数月表示，如 -2=闰二月）。")
        if args.day > lm.getDayCount():
            raise ValueError(f"农历 {args.year} 年{mdesc}是小月，只有 {lm.getDayCount()} 天，没有 {args.day} 日。")
    else:
        if not (1 <= args.month <= 12 and 1 <= args.day <= 31):
            raise ValueError("输入有误：月1-12、日1-31。农历请加 --lunar（闰月用负数月，如 -2=闰二月）。")
        try:
            datetime(args.year, args.month, args.day, hour if hour is not None else 12,
                     minute if hour is not None else 0)
        except ValueError as e:
            raise ValueError(f"日期非法：{e}") from e


def main():
    ap = argparse.ArgumentParser(description=f"八字排盘引擎 v{__version__}（支持公历 {YEAR_MIN}-{YEAR_MAX} 年）")
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("day", type=int)
    ap.add_argument("hour", type=int, nargs="?", default=None,
                    help="出生时（0-23）；不传则按时辰未知输出三柱")
    ap.add_argument("minute", type=int, nargs="?", default=0)
    ap.add_argument("--gender", choices=["male", "female"], required=True)
    ap.add_argument("--lunar", action="store_true",
                    help="输入按农历(默认阳历)；闰月用负数月表示，如 -2=闰二月")
    ap.add_argument("--lng", type=float, default=None,
                    help="出生地经度(东经正、西经负，范围-180~180)，启用真太阳时校正")
    ap.add_argument("--tz", type=float, default=8.0, help="时区偏移(默认+8)")
    ap.add_argument("--china-dst", action="store_true",
                    help="明确按中国 1986-1991 夏令时规则提示核时（不根据经度自动推断）")
    ap.add_argument("--zi-sect", type=int, choices=[1, 2], default=None,
                    help="子时流派：1=晚子(23点)换日，2=不换日；不传用库默认")
    ap.add_argument("--years", type=_span_int, nargs=2, metavar=("START", "SPAN"),
                    help="流年起始年与年数(均须≥1)，如 --years 2024 12")
    ap.add_argument("--target-date", type=int, nargs=3, metavar=("Y", "M", "D"),
                    help="指定公历日，输出其流年/流月/流日干支与对原局的引动（断语止于月）")
    ap.add_argument("--partner", type=int, nargs="+", metavar="Y M D [H] [Mi]",
                    help="合婚第二人生辰(年 月 日 [时] [分])，三值表示时辰未知；默认公历")
    ap.add_argument("--partner-lunar", action="store_true",
                    help="合婚第二人生辰按农历输入（独立于主盘 --lunar，闰月用负数月）")
    ap.add_argument("--partner-gender", choices=["male", "female"], default=None,
                    help="合婚第二人性别，用于乙方盘大运顺逆（不传则同主盘）")
    ap.add_argument("--partner-china-dst", action="store_true",
                    help="明确按中国 1986-1991 夏令时规则提示核对乙方时间")
    ap.add_argument("--partner-lng", type=float, default=None,
                    help="合婚第二人出生地经度，用于乙方真太阳时校正")
    ap.add_argument("--partner-tz", type=float, default=None,
                    help="合婚第二人时区偏移（默认 +8）")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"bazi paipan v{__version__}")
    args = ap.parse_args()

    try:
        chart = build_chart(args)
        if args.partner:
            partner_hour = args.partner[3] if len(args.partner) >= 4 else None
            partner_minute = args.partner[4] if len(args.partner) == 5 else 0
            pargs = argparse.Namespace(year=args.partner[0], month=args.partner[1], day=args.partner[2],
                                       hour=partner_hour, minute=partner_minute,
                                       gender=args.partner_gender or args.gender,
                                       lunar=args.partner_lunar,
                                       lng=args.partner_lng,
                                       tz=args.partner_tz if args.partner_tz is not None else 8.0,
                                       zi_sect=args.zi_sect if partner_hour is not None else None,
                                       years=None, target_date=None,
                                       china_dst=args.partner_china_dst)
            partner_chart = build_chart(pargs)
            chart["partner_chart"] = partner_chart
            chart["compatibility"] = compatibility(chart, partner_chart)
            chart["partner_pillars"] = partner_chart["pillars"]
            chart["partner_input"] = partner_chart["input"]
            chart["partner_calendar"] = "农历" if args.partner_lunar else "公历"
            chart["partner_yun"] = None
            if partner_chart["input"]["hour_known"]:
                chart["partner_yun"] = (f"{partner_chart['yun_direction']}　"
                                        f"{partner_chart['start_age']}岁起运（虚岁，按{'乙方' if args.partner_gender else '主盘'}性别定顺逆）")
            chart["partner_dst_note"] = partner_chart["input"].get("dst_note")
    except (ValueError, RuntimeError) as e:
        ap.error(str(e))
    if args.json:
        print(json.dumps(chart, ensure_ascii=False, indent=2))
    else:
        print(render_text(chart))


if __name__ == "__main__":
    main()
