#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
八字排盘引擎 v1.1 — HeiGe-SuanMing / bazi-mingli skill
精确排四柱、藏干、十神、纳音、长生十二宫、五行力量、神煞、刑冲合会、大运、流年。

排盘核心依赖 lunar_python：自动以「立春」定年柱、以「节气」定月柱、处理农历闰月，
规避模型手推干支时最常犯的三类错误（年柱误用正月初一、月柱误用农历月、忽略真太阳时）。

安装：pip3 install lunar_python

用法：
  python3 paipan.py 1990 5 15 14 30 --gender male
  python3 paipan.py 1990 5 15 14 30 --gender female --json
  python3 paipan.py 1990 4 21 14 30 --gender male --lunar         # 按农历输入
  python3 paipan.py 1990 5 15 14 30 --gender male --lng 113.3     # 经度→真太阳时校正
  python3 paipan.py 1990 5 15 14 30 --gender male --years 2024 12 # 从2024年起排12个流年
"""

import argparse
import json
import math
import sys
from datetime import datetime, timedelta

__version__ = "1.1.0"

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
XING_ZI = set("辰午酉亥")  # 自刑


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
    labels = ["年", "月", "日", "时"]
    z = [p[1] for p in pillars]
    rel = {"六合": [], "三合": [], "半合": [], "三会": [], "六冲": [], "相刑": [], "六害": [], "自刑": []}

    for i in range(4):
        for j in range(i + 1, 4):
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
        idxs = [k for k in range(4) if z[k] in combo]
        chars = set(z[k] for k in idxs)
        who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
        if len(chars) == 3:
            rel["三合"].append(f"{combo}三合{wx}局({who})")
        elif len(chars) == 2 and combo[1] in chars:
            rel["半合"].append(f"{combo[:3]}半合{wx}({who})")
    # 三会
    for combo, wx in SANHUI.items():
        idxs = [k for k in range(4) if z[k] in combo]
        if len(set(z[k] for k in idxs)) == 3:
            who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
            rel["三会"].append(f"{combo}三会{wx}方({who})")
    # 三刑（≥2字）
    for grp, name in ((XING3_A, "寅巳申·无恩之刑"), (XING3_B, "丑戌未·恃势之刑")):
        idxs = [k for k in range(4) if z[k] in grp]
        chars = set(z[k] for k in idxs)
        if len(chars) >= 2:
            who = "·".join(f"{labels[k]}{z[k]}" for k in idxs)
            full = "三刑全" if len(chars) == 3 else "半刑"
            rel["相刑"].append(f"{name}({full}: {who})")
    # 自刑
    for zz in XING_ZI:
        idxs = [k for k in range(4) if z[k] == zz]
        if len(idxs) >= 2:
            who = "·".join(labels[k] for k in idxs)
            rel["自刑"].append(f"{zz}{zz}自刑({who})")

    return {k: v for k, v in rel.items() if v}


def detect_gan_relations(pillars):
    labels = ["年", "月", "日", "时"]
    g = [p[0] for p in pillars]
    rel = {"天干五合": [], "天干相冲": []}
    for i in range(4):
        for j in range(i + 1, 4):
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

    td = TIANDE.get(month_zhi)
    if td and td in gans:
        res["天德贵人"] = [labels[i] for i, g in enumerate(gans) if g == td]
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

    for base_zhi in {year_zhi, day_zhi}:
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
    return res


# ============================================================
# 真太阳时 / 长生
# ============================================================
def true_solar_time(dt, lng, tz_offset):
    n = dt.timetuple().tm_yday
    b = math.radians(360.0 * (n - 81) / 364.0)
    eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
    delta = (lng - tz_offset * 15.0) * 4.0 + eot
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


# ============================================================
# 主排盘
# ============================================================
def build_chart(args):
    try:
        from lunar_python import Solar, Lunar
    except ImportError:
        sys.exit("缺少依赖 lunar_python，请先运行：pip3 install lunar_python")

    y, mo, d, h, mi = args.year, args.month, args.day, args.hour, args.minute
    corr_note = None

    if args.lunar:
        lunar = Lunar.fromYmdHms(y, mo, d, h, mi, 0)
        solar = lunar.getSolar()
        y, mo, d, h, mi = (solar.getYear(), solar.getMonth(), solar.getDay(),
                           solar.getHour(), solar.getMinute())

    if args.lng is not None and not args.lunar:
        dt, delta = true_solar_time(datetime(y, mo, d, h, mi), args.lng, args.tz)
        y, mo, d, h, mi = dt.year, dt.month, dt.day, dt.hour, dt.minute
        corr_note = f"经度{args.lng}°、时区UTC+{args.tz} → 真太阳时校正 {delta:+} 分钟"

    solar = Solar.fromYmdHms(y, mo, d, h, mi, 0)
    lunar = solar.getLunar()
    ec = lunar.getEightChar()
    if args.zi_sect:
        ec.setSect(args.zi_sect)

    ganzhi = {"年": ec.getYear(), "月": ec.getMonth(), "日": ec.getDay(), "时": ec.getTime()}
    pillars = [(ganzhi[k][0], ganzhi[k][1]) for k in ["年", "月", "日", "时"]]
    day_gan = pillars[2][0]
    month_zhi = pillars[1][1]

    keys = ["年", "月", "日", "时"]
    nayin = {"年": ec.getYearNaYin(), "月": ec.getMonthNaYin(), "日": ec.getDayNaYin(), "时": ec.getTimeNaYin()}
    dishi = {"年": ec.getYearDiShi(), "月": ec.getMonthDiShi(), "日": ec.getDayDiShi(), "时": ec.getTimeDiShi()}
    xunkong = {"年": ec.getYearXunKong(), "月": ec.getMonthXunKong(), "日": ec.getDayXunKong(), "时": ec.getTimeXunKong()}
    gan_shen = {"年": ten_god(day_gan, pillars[0][0]), "月": ten_god(day_gan, pillars[1][0]),
                "日": "日主", "时": ten_god(day_gan, pillars[3][0])}
    zhi_shen = {k: zhi_ten_gods(day_gan, pillars[i][1]) for i, k in enumerate(keys)}

    score, tong, yi, tong_d, yi_d = wuxing_strength(pillars, day_gan)
    cnt, lack = wuxing_count(pillars)
    shensha = compute_shensha(pillars)
    zhi_rel = detect_zhi_relations(pillars)
    gan_rel = detect_gan_relations(pillars)

    # 节气
    jieqi = None
    try:
        pj, nj = lunar.getPrevJieQi(), lunar.getNextJieQi()
        bd = datetime(solar.getYear(), solar.getMonth(), solar.getDay())
        ps = pj.getSolar()
        pdt = datetime(ps.getYear(), ps.getMonth(), ps.getDay())
        jieqi = f"{pj.getName()}（{ps.toYmd()}）后第 {(bd - pdt).days} 天，下一节气 {nj.getName()}"
    except Exception:
        pass

    # 大运
    gender_int = 1 if args.gender == "male" else 0
    year_yang = GAN_YINYANG[pillars[0][0]] == "阳"
    forward = (year_yang and gender_int == 1) or (not year_yang and gender_int == 0)
    yun = ec.getYun(gender_int)
    dayun_list = []
    for dy in yun.getDaYun():
        gz = dy.getGanZhi()
        if not gz:
            dayun_list.append({"start_age": dy.getStartAge(), "end_age": dy.getEndAge(),
                               "start_year": dy.getStartYear(), "ganzhi": "", "note": "幼运(未上大运)"})
            continue
        g, z = gz[0], gz[1]
        dayun_list.append({"start_age": dy.getStartAge(), "end_age": dy.getEndAge(),
                           "start_year": dy.getStartYear(), "ganzhi": gz,
                           "gan_shen": ten_god(day_gan, g), "zhi_shen": zhi_ten_gods(day_gan, z),
                           "dishi": _dishi_of(day_gan, z)})

    # 流年
    start_year, span = (args.years[0], args.years[1]) if args.years else (datetime.now().year, 10)
    liunian = []
    for yy in range(start_year, start_year + span):
        g, z = GAN[(yy - 4) % 10], ZHI[(yy - 4) % 12]
        liunian.append({"year": yy, "ganzhi": g + z, "gan_shen": ten_god(day_gan, g),
                        "zhi_shen": zhi_ten_gods(day_gan, z), "age": yy - solar.getYear() + 1})

    return {
        "version": __version__,
        "input": {
            "solar": f"{solar.getYear()}-{solar.getMonth():02d}-{solar.getDay():02d} {solar.getHour():02d}:{solar.getMinute():02d}",
            "lunar": lunar.toString(), "shengxiao": SHENGXIAO[pillars[0][1]],
            "xingzuo": solar.getXingZuo(), "gender": "男" if gender_int else "女",
            "jieqi": jieqi, "correction": corr_note,
        },
        "pillars": ganzhi, "day_master": f"{day_gan}{GAN_WUXING[day_gan]}",
        "gan_shen": gan_shen, "zhi_canggan": {k: ZHI_CANGGAN[pillars[i][1]] for i, k in enumerate(keys)},
        "zhi_shen": zhi_shen, "nayin": nayin, "dishi": dishi, "xunkong": xunkong,
        "month_ling": f"{month_zhi}（{ZHI_WUXING[month_zhi]}）",
        "wuxing_score": score, "wuxing_count": cnt, "wuxing_lack": lack,
        "tong_dang": tong, "yi_dang": yi, "tong_detail": tong_d, "yi_detail": yi_d,
        "zhi_relations": zhi_rel, "gan_relations": gan_rel, "shensha": shensha,
        "taiyuan": ec.getTaiYuan(), "minggong": ec.getMingGong(), "shengong": ec.getShenGong(),
        "yun_direction": "顺排" if forward else "逆排",
        "start_age": yun.getStartYear(), "start_solar": yun.getStartSolar().toYmd(),
        "dayun": dayun_list, "liunian": liunian,
    }


# ============================================================
# 文本渲染
# ============================================================
def render_text(c):
    L, P = [], None
    out = []
    def P(s=""): out.append(s)
    inp = c["input"]
    cols = ["年", "月", "日", "时"]
    P("════════════════════ 八字命盘 ════════════════════")
    P(f"公历：{inp['solar']}　性别：{inp['gender']}　生肖：{inp['shengxiao']}　星座：{inp['xingzuo']}")
    P(f"农历：{inp['lunar']}")
    if inp["jieqi"]:
        P(f"节气：{inp['jieqi']}")
    if inp["correction"]:
        P(f"校正：{inp['correction']}")
    P("")
    P("【四柱】     " + "    ".join(f"{k}柱" for k in cols))
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
    P(f"【胎元】{c['taiyuan']}　【命宫】{c['minggong']}　【身宫】{c['shengong']}")
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
    P(f"【大运】{c['yun_direction']}　{c['start_age']}岁起运（{c['start_solar']}）")
    for dy in c["dayun"]:
        if not dy["ganzhi"]:
            P(f"  幼运 {dy['start_age']}-{dy['end_age']}岁（{dy['start_year']}-）")
            continue
        P(f"  {dy['ganzhi']}　{dy['start_age']:>2}-{dy['end_age']:>2}岁　{dy['start_year']}年起"
          f"　[{dy['gan_shen']}/{'/'.join(dy['zhi_shen'])}]　星运:{dy['dishi']}")
    P("")
    P(f"【流年】{c['liunian'][0]['year']}-{c['liunian'][-1]['year']}")
    for ln in c["liunian"]:
        P(f"  {ln['year']}（虚{ln['age']}岁）{ln['ganzhi']}　[{ln['gan_shen']}/{'/'.join(ln['zhi_shen'])}]")
    P("══════════════════════════════════════════════════")
    P(f"排盘引擎 v{c['version']}　仅供传统文化研究与自我认知参考")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser(description=f"八字排盘引擎 v{__version__}")
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("day", type=int)
    ap.add_argument("hour", type=int)
    ap.add_argument("minute", type=int, nargs="?", default=0)
    ap.add_argument("--gender", choices=["male", "female"], required=True)
    ap.add_argument("--lunar", action="store_true", help="输入按农历(默认阳历)")
    ap.add_argument("--lng", type=float, default=None, help="出生地经度(东经正)，启用真太阳时校正")
    ap.add_argument("--tz", type=float, default=8.0, help="时区偏移(默认+8)")
    ap.add_argument("--zi-sect", type=int, choices=[1, 2], default=None,
                    help="子时流派：1=晚子(23点)换日，2=不换日；不传用库默认")
    ap.add_argument("--years", type=int, nargs=2, metavar=("START", "SPAN"),
                    help="流年起始年与年数，如 --years 2024 12")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"bazi paipan v{__version__}")
    args = ap.parse_args()

    if not (1 <= args.month <= 12 and 1 <= args.day <= 31 and 0 <= args.hour <= 23 and 0 <= args.minute <= 59):
        sys.exit("输入有误：月1-12、日1-31、时0-23、分0-59。农历请加 --lunar。")
    if not args.lunar:
        try:
            datetime(args.year, args.month, args.day, args.hour, args.minute)
        except ValueError as e:
            sys.exit(f"日期非法：{e}")

    chart = build_chart(args)
    if args.json:
        print(json.dumps(chart, ensure_ascii=False, indent=2))
    else:
        print(render_text(chart))


if __name__ == "__main__":
    main()
