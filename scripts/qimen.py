#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qimen.py：时家奇门遁甲排局引擎（转盘 · 拆补法）。

定位：本库第六个引擎、第三个占测引擎（梅花、六爻之后）。只做「排局层」：
定局（阴阳遁+局数+三元）→ 地盘三奇六仪 → 旬首值符值使 → 天盘九星 →
八门 → 八神 → 附加标注（旬空/驿马/伏吟反吟）。断局方法论见 references/21。

流派口径（与 references/21 一致，全部有双源依据）：
- 排局法：拆补法（无状态、现代软件事实主流）。置闰法（超神接气）有历史
  状态且开源实现普遍有 bug，本版不实现，文档如实记录两法分歧。
- 盘式：转盘（主流）。飞盘不做。
- 子时：默认 23 点换日（时家主流，lunar_python 需显式 setSect(1)），
  --zi-sect 2 可选夜子时不换日。
- 中五寄宫：一律寄坤二（当代主流）。
- 八神：值符螣蛇太阴六合白虎玄武九地九天；阳遁古法白虎=勾陈、玄武=朱雀，
  属同位异名，输出以白虎/玄武为主名。

全部排布公式经开源实现交叉核验（kinqimen/qfdk/qimenpaipan+元亨利贞四源，
黄金用例见 tests/test_qimen.py），出处与存疑标注见 references/21。
"""

import argparse
import datetime
import json
import os
import sys

__version__ = "1.1.0"

_HERE = os.path.dirname(os.path.abspath(__file__))
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
# 天干地支表统一从 paipan 引入（唯一真源，避免多处拷贝漂移）
from paipan import (GAN, ZHI, YEAR_MIN, YEAR_MAX,  # noqa: E402
                    GAN_WUXING, GAN_YINYANG, ZHI_WUXING,
                    WUXING_SHENG, WUXING_KE)

GAN_IDX = {g: i for i, g in enumerate(GAN)}
ZHI_IDX = {z: i for i, z in enumerate(ZHI)}

# ============================================================
# 常量层（洛书九宫 / 转盘环序 / 元旦盘 / 六仪 / 72 局表）
# ============================================================

# 洛书九宫：宫号 → (卦名, 方位)
GONG_INFO = {
    1: ("坎", "正北"), 2: ("坤", "西南"), 3: ("震", "正东"),
    4: ("巽", "东南"), 5: ("中", "中宫"), 6: ("乾", "西北"),
    7: ("兑", "正西"), 8: ("艮", "东北"), 9: ("离", "正南"),
}

# 转盘顺时针环序（坎1→艮8→震3→巽4→离9→坤2→兑7→乾6），阴阳遁不变
RING = [1, 8, 3, 4, 9, 2, 7, 6]
RING_IDX = {g: i for i, g in enumerate(RING)}

# 地盘布干顺序：六仪在前、三奇在后（注意三奇是丁丙乙）
ORDER = ["戊", "己", "庚", "辛", "壬", "癸", "丁", "丙", "乙"]

# 元旦盘：宫号 → 原始九星 / 原始八门（中5无门）
STAR_HOME = {"天蓬": 1, "天芮": 2, "天冲": 3, "天辅": 4, "天禽": 5,
             "天心": 6, "天柱": 7, "天任": 8, "天英": 9}
GONG_STAR = {v: k for k, v in STAR_HOME.items()}
DOOR_HOME = {"休门": 1, "死门": 2, "伤门": 3, "杜门": 4, "景门": 9,
             "惊门": 7, "生门": 8, "开门": 6}
GONG_DOOR = {v: k for k, v in DOOR_HOME.items()}

# 六甲旬首 → 遁仪（甲子戊 甲戌己 甲申庚 甲午辛 甲辰壬 甲寅癸）
# 键为旬首地支序 (z-g) mod 12
XUNSHOU_YI = {0: "戊", 10: "己", 8: "庚", 6: "辛", 4: "壬", 2: "癸"}

# 八神固定顺序（转盘主流名单；阳遁古法白虎=勾陈、玄武=朱雀，同位异名）
SHEN_ORDER = ["值符", "螣蛇", "太阴", "六合", "白虎", "玄武", "九地", "九天"]
SHEN_ALIAS = {"白虎": "勾陈", "玄武": "朱雀"}

# 24 节气 × 三元 = 72 局总表：节气 → (遁, (上元, 中元, 下元))
# 三源逐项核对一致（歌诀文献 + kinqimen + qfdk/qimen），出处见 references/21
JU_TABLE = {
    "冬至": ("阳", (1, 7, 4)), "小寒": ("阳", (2, 8, 5)), "大寒": ("阳", (3, 9, 6)),
    "立春": ("阳", (8, 5, 2)), "雨水": ("阳", (9, 6, 3)), "惊蛰": ("阳", (1, 7, 4)),
    "春分": ("阳", (3, 9, 6)), "清明": ("阳", (4, 1, 7)), "谷雨": ("阳", (5, 2, 8)),
    "立夏": ("阳", (4, 1, 7)), "小满": ("阳", (5, 2, 8)), "芒种": ("阳", (6, 3, 9)),
    "夏至": ("阴", (9, 3, 6)), "小暑": ("阴", (8, 2, 5)), "大暑": ("阴", (7, 1, 4)),
    "立秋": ("阴", (2, 5, 8)), "处暑": ("阴", (1, 4, 7)), "白露": ("阴", (9, 3, 6)),
    "秋分": ("阴", (7, 1, 4)), "寒露": ("阴", (6, 9, 3)), "霜降": ("阴", (5, 8, 2)),
    "立冬": ("阴", (6, 9, 3)), "小雪": ("阴", (5, 8, 2)), "大雪": ("阴", (4, 7, 1)),
}
YUAN_NAME = ["上元", "中元", "下元"]

# 地支 → 落宫（旬空、驿马标注用）
ZHI_GONG = {"子": 1, "丑": 8, "寅": 8, "卯": 3, "辰": 4, "巳": 4,
            "午": 9, "未": 2, "申": 2, "酉": 7, "戌": 6, "亥": 6}

# 驿马：按时支三合局（申子辰马在寅、寅午戌马在申、巳酉丑马在亥、亥卯未马在巳）
YIMA = {"申": "寅", "子": "寅", "辰": "寅", "寅": "申", "午": "申", "戌": "申",
        "巳": "亥", "酉": "亥", "丑": "亥", "亥": "巳", "卯": "巳", "未": "巳"}

# 对冲宫（反吟标注用）
GONG_CHONG = {1: 9, 9: 1, 2: 8, 8: 2, 3: 7, 7: 3, 4: 6, 6: 4}

# 二十四节气环序（置闰法符头链数块用）
SEQ_24 = ["冬至", "小寒", "大寒", "立春", "雨水", "惊蛰", "春分", "清明", "谷雨",
          "立夏", "小满", "芒种", "夏至", "小暑", "大暑", "立秋", "处暑", "白露",
          "秋分", "寒露", "霜降", "立冬", "小雪", "大雪"]

# 甲子日锚点（元亨利贞与 lunar_python 双源核对）
JIAZI_ANCHOR = datetime.date(2024, 12, 26)

# ============================================================
# 断局标注常量层（十干克应 / 格局 / 四害 / 旺衰，出处见 references/22）
# ============================================================

# 十干克应：天盘干 → {地盘干: 格名}（转盘九干口径，甲隐遁以旬首仪代；
# 81 组经两独立来源逐项核对，8 处名称异文取主源、断语方向一致，详表见 references/22）
KEYING = {
    "戊": {"戊": "青龙伏吟", "乙": "青龙和会", "丙": "青龙返首", "丁": "青龙耀明",
           "己": "贵人入狱", "庚": "值符飞宫", "辛": "青龙折足", "壬": "龙入天牢",
           "癸": "青龙华盖"},
    "乙": {"戊": "利阴害阳", "乙": "日奇伏吟", "丙": "奇仪顺遂", "丁": "奇仪相佐",
           "己": "日奇入雾", "庚": "日奇被刑", "辛": "青龙逃走", "壬": "日奇入地",
           "癸": "华盖逢星"},
    "丙": {"戊": "飞鸟跌穴", "乙": "日月并行", "丙": "月奇悖师", "丁": "星奇朱雀",
           "己": "火悖入刑", "庚": "荧入太白", "辛": "丙辛相合", "壬": "火入天罗",
           "癸": "华盖悖师"},
    "丁": {"戊": "青龙转光", "乙": "人遁吉格", "丙": "星随月转", "丁": "奇入太阴",
           "己": "火入勾陈", "庚": "文书阻隔", "辛": "朱雀入狱", "壬": "五神互合",
           "癸": "朱雀投江"},
    "己": {"戊": "犬遇青龙", "乙": "墓神不明", "丙": "火悖地户", "丁": "朱雀入墓",
           "己": "地户逢鬼", "庚": "刑格", "辛": "游魂入墓", "壬": "地网高张",
           "癸": "地刑玄武"},
    "庚": {"戊": "太白伏宫", "乙": "太白蓬星", "丙": "太白入荧", "丁": "亭亭之格",
           "己": "官符刑格", "庚": "太白同宫", "辛": "白虎干格", "壬": "小格",
           "癸": "大格"},
    "辛": {"戊": "困龙被伤", "乙": "白虎猖狂", "丙": "干合悖师", "丁": "狱神得奇",
           "己": "入狱自刑", "庚": "白虎出力", "辛": "伏吟天庭", "壬": "凶蛇入狱",
           "癸": "天牢华盖"},
    "壬": {"戊": "小蛇化龙", "乙": "小蛇得势", "丙": "水蛇入火", "丁": "干合蛇刑",
           "己": "反吟蛇刑", "庚": "太白擒蛇", "辛": "腾蛇相缠", "壬": "蛇入地罗",
           "癸": "幼女奸淫"},
    "癸": {"戊": "天乙会合", "乙": "华盖逢星", "丙": "华盖悖师", "丁": "腾蛇夭矫",
           "己": "华盖地户", "庚": "太白入网", "辛": "网盖天牢", "壬": "复见腾蛇",
           "癸": "天网四张"},
}

# 六仪击刑：天盘六仪落该宫为击刑（戊落震3子刑卯、己落坤2戌刑未、庚落艮8申刑寅、
# 辛落离9午自刑、壬落巽4辰自刑、癸落巽4寅刑巳）
JIXING = {"戊": 3, "己": 2, "庚": 8, "辛": 9, "壬": 4, "癸": 4}

# 十干入墓：天盘干落该宫为入墓（乙丙戊墓乾6戌、丁己庚墓艮8丑、辛壬墓巽4辰、癸墓坤2未）
RUMU = {"乙": 6, "丙": 6, "戊": 6, "丁": 8, "己": 8, "庚": 8, "辛": 4, "壬": 4, "癸": 2}

# 八门 / 九宫 / 九星 五行（门迫门制与旺衰修正用）
DOOR_WUXING = {"休门": "水", "生门": "土", "伤门": "木", "杜门": "木",
               "景门": "火", "死门": "土", "惊门": "金", "开门": "金"}
GONG_WUXING = {1: "水", 2: "土", 3: "木", 4: "木", 5: "土", 6: "金", 7: "金", 8: "土", 9: "火"}
STAR_WUXING = {"天蓬": "水", "天芮": "土", "天冲": "木", "天辅": "木", "天禽": "土",
               "天心": "金", "天柱": "金", "天任": "土", "天英": "火"}

# 三奇得使：天盘三奇 + 地盘对应六仪（乙+己/辛、丙+戊/庚、丁+壬/癸）
SANQI_DESHI = {"乙": ("己", "辛"), "丙": ("戊", "庚"), "丁": ("壬", "癸")}
# 三奇升殿：乙落震3（卯）、丙落离9（午）、丁落兑7（酉）
SANQI_SHENGDIAN = {"乙": 3, "丙": 9, "丁": 7}


# ============================================================
# 干支与节气（底座：lunar_python，含两个已实测的工程坑的兜底）
# ============================================================

def _ganzhi_index(gz):
    """干支 → 六十甲子序号（甲子=0…癸亥=59）。"""
    g, z = GAN_IDX[gz[0]], ZHI_IDX[gz[1]]
    for n in range(60):
        if n % 10 == g and n % 12 == z:
            return n
    raise ValueError(f"非法干支：{gz}")


def _xun_kong(gz):
    """某柱干支 → 所在旬的两个空亡支。"""
    n = _ganzhi_index(gz)
    xun_start = n - n % 10  # 旬首序号（甲X）
    # 旬空 = 该旬十干配完后剩下的两个地支
    k1 = ZHI[(xun_start + 10) % 12]
    k2 = ZHI[(xun_start + 11) % 12]
    return k1 + k2


def get_pillars(y, mo, d, h, mi, zi_sect=1):
    """四柱干支。默认 sect=1（23 点换日，时家奇门主流）。

    ⚠️ lunar_python 的 EightChar 默认 sect=2（夜子时日柱用当天），与时家
    奇门主流相反，必须显式 setSect；此坑已实测确认（references/21）。
    """
    from lunar_python import Solar
    ec = Solar.fromYmdHms(y, mo, d, h, mi, 0).getLunar().getEightChar()
    ec.setSect(zi_sect)
    return {
        "年柱": ec.getYear(), "月柱": ec.getMonth(),
        "日柱": ec.getDay(), "时柱": ec.getTime(),
    }


def get_jieqi(y, mo, d, h, mi):
    """当前时刻所属节气（按精确交气时刻，24 节气全取）。

    ⚠️ lunar_python 的 getPrevJieQi(True) 按「日期」粒度返回：交气当天即使
    时刻未到也返回新节气。必须再取精确交气时刻比较，未到则回退上一节气。
    此坑已实测确认（2025-12-21 00:30 即返回冬至，实际 23:03:05 才交气）。
    """
    from lunar_python import Solar
    now = datetime.datetime(y, mo, d, h, mi)
    jq = Solar.fromYmdHms(y, mo, d, h, mi, 0).getLunar().getPrevJieQi(True)
    s = jq.getSolar()
    jt = datetime.datetime(s.getYear(), s.getMonth(), s.getDay(),
                           s.getHour(), s.getMinute(), s.getSecond())
    if now < jt:  # 交气时刻未到，回退到上一节气
        prev_day = jt - datetime.timedelta(days=1)
        jq = Solar.fromYmdHms(prev_day.year, prev_day.month, prev_day.day,
                              12, 0, 0).getLunar().getPrevJieQi(True)
        s = jq.getSolar()
        jt = datetime.datetime(s.getYear(), s.getMonth(), s.getDay(),
                               s.getHour(), s.getMinute(), s.getSecond())
    return jq.getName(), jt


# ============================================================
# 置闰法定局（超神接气·符头分类法，无状态；出处与 43 用例电池见 references/21）
# ============================================================

def _day_index_by_date(d):
    """民用日 → 六十甲子序号（甲子=0），锚点 2024-12-26 甲子。"""
    return (d - JIAZI_ANCHOR).days % 60


def _solstice_day(year, name):
    """公历 year 年冬至/夏至的交气日（交气时刻所在民用日）。

    ⚠️ lunar_python 的 JieQiTable 以农历年为界：公历 Y 年 12 月的冬至要用
    fromYmd(Y+1,6,1) 查；异常不吞（吞掉会致符头链锚错位，终审钉过此坑）。
    """
    from lunar_python import Solar
    q = year + 1 if name == "冬至" else year
    s = Solar.fromYmd(q, 6, 1).getLunar().getJieQiTable()[name]
    d = datetime.date(s.getYear(), s.getMonth(), s.getDay())
    if d.year != year:
        raise ValueError(f"{year} 年{name}交气日取到 {d}，节气表异常")
    return d


def _solstices_around(F):
    """按时间排序、覆盖 F 前后各一年的 (交气日, 名称) 列表。"""
    out = []
    for y in (F.year - 1, F.year, F.year + 1):
        for nm in ("夏至", "冬至"):
            out.append((_solstice_day(y, nm), nm))
    return sorted(set(out))


def _zhirun_jieqi_of_futou(F, leap_min):
    """置闰法：上元符头日 F 起哪个节气的上元。返回 (节气名, 状态描述)。"""
    sol = _solstices_around(F)
    S, s_name = next((s, nm) for s, nm in sol if s >= F)
    gap = (S - F).days
    if gap <= 14:
        if gap == 0:
            return s_name, "正授"
        if gap < leap_min:
            return s_name, f"超神{gap}天"
        leap = "大雪" if s_name == "冬至" else "芒种"
        return leap, f"置闰段（闰{leap}）"
    # F 属上一个二至的符头链，按 15 天块顺数
    P, p_name = [x for x in sol if x[0] < F][-1]
    A = P - datetime.timedelta(days=_day_index_by_date(P) % 15)
    gap_p = (P - A).days
    if gap_p < leap_min:
        start = p_name
    else:
        start = "大雪" if p_name == "冬至" else "芒种"
    k = (F - A).days // 15  # 两个上元符头之差恒为 15 的倍数
    jq = SEQ_24[(SEQ_24.index(start) + k) % 24]
    m = (F - P).days
    status = f"接气{m}天" if jq in ("冬至", "夏至") and m <= 14 else "常规段"
    return jq, status


def zhirun_ding_ju(day_pillar_date, leap_min=8):
    """置闰法定局：日柱所在民用日 → (遁, 局数, 元, 节气归属, 符头, 状态)。

    黄金值 oracle=元亨利贞在线置闰排盘（43 用例实测全过）；leap_min=8 为
    「含头尾满九天即闰」派（元亨利贞实测口径，默认），9 为古籍「超过九天」派，
    两派仅在 2007/2010/2015/2030 四段各差半年局数。
    """
    n = _day_index_by_date(day_pillar_date)
    yuan = (n // 5) % 3
    F = day_pillar_date - datetime.timedelta(days=n % 15)
    jq, status = _zhirun_jieqi_of_futou(F, leap_min)
    dun, ju_list = JU_TABLE[jq]
    futou = GAN[(n - n % 5) % 10] + ZHI[(n - n % 5) % 12]
    return dun, ju_list[yuan], YUAN_NAME[yuan], jq, futou, status


# ============================================================
# 排局核心（每步公式的出处与手推核验记录见 references/21）
# ============================================================

def ding_ju(jieqi_name, day_gz):
    """定局（拆补法）：节气 + 日柱 → (遁, 局数, 元)。

    三元判定用纯公式：日柱六十甲子序号 n，符头 = n - n%5（甲/己日），
    元 = (n//5) % 3。必须回溯符头定元，不能看当日日支（工程陷阱，
    references/21 有反例）。
    """
    if jieqi_name not in JU_TABLE:
        raise ValueError(f"未知节气：{jieqi_name}")
    dun, ju_list = JU_TABLE[jieqi_name]
    n = _ganzhi_index(day_gz)
    futou_n = n - n % 5
    yuan = (n // 5) % 3
    futou = GAN[futou_n % 10] + ZHI[futou_n % 12]
    return dun, ju_list[yuan], YUAN_NAME[yuan], futou


def di_pan(dun, ju):
    """地盘三奇六仪：宫号 → 干。gong(i) = ((ju-1 + s*i) mod 9) + 1，
    ORDER 下标 i=0..8，阳遁 s=+1、阴遁 s=-1；中五宫正常落干。"""
    s = 1 if dun == "阳" else -1
    pan = {}
    for i, gan in enumerate(ORDER):
        gong = ((ju - 1 + s * i) % 9) + 1
        pan[gong] = gan
    return pan

def xun_shou(hour_gz):
    """时柱 → (旬首名, 遁仪)。旬首地支序 = (z - g) mod 12。"""
    g, z = GAN_IDX[hour_gz[0]], ZHI_IDX[hour_gz[1]]
    key = (z - g) % 12
    yi = XUNSHOU_YI[key]
    return "甲" + ZHI[key], yi


def tian_pan(dun, dipan, hour_gz, yi):
    """天盘九星 + 值符值使 + 八门 + 八神，一次排完。

    返回 dict：含值符星/值使门身份与落宫、每宫天盘星/干/门/神、
    星门各自的 steps（伏吟=0、反吟=4）。
    """
    gan_gong = {v: k for k, v in dipan.items()}  # 干 → 地盘宫

    # 旬首仪落宫 F：值符星、值使门的老家
    F = gan_gong[yi]
    zhifu_star = GONG_STAR[F]            # F=5 时即天禽（随芮）
    zhishi_door = GONG_DOOR.get(F, "死门")  # 中5无门，借死门

    # 时干落宫 L：甲时用旬首仪（甲遁于仪下，全盘伏吟）；落中5寄坤2
    hg = hour_gz[0]
    L = F if hg == "甲" else gan_gong[hg]
    F2 = 2 if F == 5 else F  # 寄宫后的环上位置
    L2 = 2 if L == 5 else L

    # 九星整体转动：值符星从 F' 移到 L'，其余星同步前移 steps 步
    steps = (RING_IDX[L2] - RING_IDX[F2]) % 8
    stars = {}   # 宫 → [星]（芮禽同宫成对）
    for home_gong in RING:
        star = GONG_STAR[home_gong]
        dest = RING[(RING_IDX[home_gong] + steps) % 8]
        stars.setdefault(dest, []).append(star)
        if home_gong == 2:  # 天禽永寄坤2随天芮同行
            stars[dest].append("天禽")

    # 天盘干 = 星携原始宫地盘干；芮禽同宫带双干（芮宫干 + 中5寄干）
    tian_gan = {}
    for gong, star_list in stars.items():
        gans = [dipan[STAR_HOME[star_list[0]]]]
        if "天禽" in star_list:
            gans.append(dipan[5])  # 寄干
        tian_gan[gong] = gans

    # 值使门飞宫：按九宫数含中五数（起数用真实宫数 F，旬首入中从 5 起数，
    # 此为已被多方权威盘证伪 qfdk 少数派数法后钉死的口径，见 references/21）
    n_seq = GAN_IDX[hg] + 1  # 时干旬内序数：甲1…癸10
    offset = n_seq - 1
    if dun == "阳":
        g_dest = ((F - 1 + offset) % 9) + 1
    else:
        g_dest = ((F - 1 - offset) % 9) + 1
    zhishi_gong_raw = g_dest
    g2 = 2 if g_dest == 5 else g_dest  # 落中5寄坤2显示

    # 其余七门整体转动
    men_steps = (RING_IDX[g2] - RING_IDX[F2]) % 8
    doors = {}
    for home_gong in RING:
        door = GONG_DOOR[home_gong]
        dest = RING[(RING_IDX[home_gong] + men_steps) % 8]
        doors[dest] = door

    # 八神：从值符星落宫起，阳顺阴逆布八宫；中5无神
    shens = {}
    d = 1 if dun == "阳" else -1
    for k, shen in enumerate(SHEN_ORDER):
        dest = RING[(RING_IDX[L2] + d * k) % 8]
        shens[dest] = shen

    return {
        "旬首落宫F": F, "值符星": zhifu_star, "值使门": zhishi_door,
        "值符落宫": L2, "值使落宫": g2, "值使落宫原始": zhishi_gong_raw,
        "星steps": steps, "门steps": men_steps,
        "天盘星": stars, "天盘干": tian_gan, "八门": doors, "八神": shens,
    }


def _star_wangshuai(star, month_zhi):
    """九星旺衰（古法专用口径，源自烟波钓叟歌）：星生月令=旺、同=相、
    星克月令=休、月令克星=囚、月令生星=废。"""
    se, me = STAR_WUXING[star], ZHI_WUXING[month_zhi]
    if WUXING_SHENG[se] == me:
        return "旺"
    if se == me:
        return "相"
    if WUXING_KE[se] == me:
        return "休"
    if WUXING_KE[me] == se:
        return "囚"
    return "废"


def _wu_bu_yu_shi(day_gz, hour_gz):
    """五不遇时：时干克日干且同阴阳（十组，如甲日庚午时）。"""
    dg, hg = day_gz[0], hour_gz[0]
    return (WUXING_KE[GAN_WUXING[hg]] == GAN_WUXING[dg]
            and GAN_YINYANG[hg] == GAN_YINYANG[dg])


def annotate_duanju(gongs, pillars, tp, dipan):
    """断局标注层：逐宫十干克应/击刑/入墓/门迫门制/星旺衰 + 全局格局。

    只做可计算标注，断语方法论见 references/22。就地修改 gongs，返回格局清单。
    """
    month_zhi = pillars["月柱"][1]
    patterns = []
    for gong in range(1, 10):
        g = gongs[gong]
        if gong == 5 or not g["天盘星"]:
            continue
        tg = g["天盘干"][0]  # 主天盘干（芮禽同宫以芮宫干为主，寄干见文档）
        dg = g["地盘干"]
        door, shen = g["门"], g["神"]
        g["克应"] = KEYING[tg][dg]
        g["星旺衰"] = _star_wangshuai(g["天盘星"][0], month_zhi)
        marks = g["标注"]
        if JIXING.get(tg) == gong:
            marks.append("击刑")
        if RUMU.get(tg) == gong:
            marks.append("入墓")
        de, ge = DOOR_WUXING[door], GONG_WUXING[gong]
        if WUXING_KE[de] == ge:
            marks.append("门迫")
        elif WUXING_KE[ge] == de:
            marks.append("门制")
        # 全局格局（三遁 / 三奇得使 / 三奇升殿）
        if door == "生门" and tg == "丙" and dg == "丁":
            patterns.append(f"天遁（{GONG_INFO[gong][0]}{gong}宫）")
        if door == "开门" and tg == "乙" and dg == "己":
            patterns.append(f"地遁（{GONG_INFO[gong][0]}{gong}宫）")
        if door == "休门" and tg == "丁" and shen == "太阴":
            patterns.append(f"人遁（{GONG_INFO[gong][0]}{gong}宫）")
        if tg in SANQI_DESHI and dg in SANQI_DESHI[tg]:
            patterns.append(f"三奇得使·{tg}加{dg}（{GONG_INFO[gong][0]}{gong}宫）")
        if SANQI_SHENGDIAN.get(tg) == gong:
            patterns.append(f"三奇升殿·{tg}（{GONG_INFO[gong][0]}{gong}宫）")
        # 庚格系列（伏干 / 飞干 / 岁月日时格）
        day_g, hour_g = pillars["日柱"][0], pillars["时柱"][0]
        if tg == "庚" and dg == day_g:
            patterns.append(f"伏干格·庚加日干（{GONG_INFO[gong][0]}{gong}宫）")
        if tg == day_g and dg == "庚" and tg != "庚":
            patterns.append(f"飞干格·日干加庚（{GONG_INFO[gong][0]}{gong}宫）")
        if tg == "庚":
            for label, pg in (("岁格", pillars["年柱"][0]), ("月格", pillars["月柱"][0]),
                              ("日格", day_g), ("时格", hour_g)):
                if dg == pg:
                    patterns.append(f"{label}·庚加{label[0]}干（{GONG_INFO[gong][0]}{gong}宫）")
    # 玉女守门：值使门落宫的地盘干为丁
    if dipan.get(tp["值使落宫"]) == "丁":
        patterns.append("玉女守门（值使落宫地盘丁）")
    return patterns


def build_pan(y, mo, d, h, mi, zi_sect=1, ju_fa="chaibu", leap_min=8):
    """排一局完整时家转盘奇门。返回结构化 dict。ju_fa: chaibu 拆补（默认）/ zhirun 置闰。"""
    # 输入校验（引擎侧全兜底，勿信上游库的宽松校验）
    if not (YEAR_MIN <= y <= YEAR_MAX):
        sys.exit(f"年份超出支持范围（{YEAR_MIN}-{YEAR_MAX}）：{y}")
    try:
        datetime.datetime(y, mo, d, h, mi)
    except ValueError as e:
        sys.exit(f"非法日期时间：{y}-{mo}-{d} {h}:{mi}（{e}）")
    if not (0 <= h <= 23):
        sys.exit(f"小时须在 0-23 之间：{h}")
    if zi_sect not in (1, 2):
        sys.exit(f"--zi-sect 只能为 1（23点换日，默认）或 2（夜子时不换日）：{zi_sect}")
    if ju_fa not in ("chaibu", "zhirun"):
        sys.exit(f"--ju-fa 只能为 chaibu（拆补，默认）或 zhirun（置闰）：{ju_fa}")
    if leap_min not in (8, 9):
        sys.exit(f"--zhirun-leap-min 只能为 8（含头尾满九天即闰，默认）或 9（古籍派）：{leap_min}")

    pillars = get_pillars(y, mo, d, h, mi, zi_sect)
    jieqi_name, jieqi_time = get_jieqi(y, mo, d, h, mi)
    zhirun_status = None
    if ju_fa == "zhirun":
        # 日柱所在民用日：23 点换日口径下 23 时属次日
        pd = datetime.date(y, mo, d)
        if zi_sect == 1 and h == 23:
            pd += datetime.timedelta(days=1)
        # 内部一致性：锚点算出的日柱须与 lunar_python 四柱一致
        n_chk = _day_index_by_date(pd)
        gz_chk = GAN[n_chk % 10] + ZHI[n_chk % 12]
        if gz_chk != pillars["日柱"]:
            raise AssertionError(f"置闰日柱校验失败：锚点算 {gz_chk}，四柱为 {pillars['日柱']}")
        dun, ju, yuan, jq_owner, futou, zhirun_status = zhirun_ding_ju(pd, leap_min)
    else:
        dun, ju, yuan, futou = ding_ju(jieqi_name, pillars["日柱"])
        jq_owner = jieqi_name
    dipan = di_pan(dun, ju)
    xs_name, yi = xun_shou(pillars["时柱"])
    tp = tian_pan(dun, dipan, pillars["时柱"], yi)

    # 附加标注：旬空（日/时柱）、驿马（时支）、伏吟反吟
    day_kong = _xun_kong(pillars["日柱"])
    hour_kong = _xun_kong(pillars["时柱"])
    kong_gongs = sorted({ZHI_GONG[z] for z in hour_kong})
    ma_zhi = YIMA[pillars["时柱"][1]]
    ma_gong = ZHI_GONG[ma_zhi]
    fuyin = tp["星steps"] == 0
    fanyin = tp["星steps"] == 4

    gongs = {}
    for gong in range(1, 10):
        if gong == 5:
            gongs[gong] = {
                "卦位": "中宫", "地盘干": dipan[5],
                "天盘干": [], "天盘星": [], "门": None, "神": None,
                "备注": "寄坤二，不布星门神",
            }
            continue
        marks = []
        if gong in kong_gongs:
            marks.append("时空亡")
        if gong == ma_gong:
            marks.append("驿马")
        gongs[gong] = {
            "卦位": GONG_INFO[gong][0] + GONG_INFO[gong][1],
            "地盘干": dipan[gong],
            "天盘干": tp["天盘干"].get(gong, []),
            "天盘星": tp["天盘星"].get(gong, []),
            "门": tp["八门"].get(gong),
            "神": tp["八神"].get(gong),
            "标注": marks,
        }

    patterns = annotate_duanju(gongs, pillars, tp, dipan)
    wubuyu = _wu_bu_yu_shi(pillars["日柱"], pillars["时柱"])
    if wubuyu:
        patterns.append("五不遇时（时干克日干，百事不宜）")

    ju_info = {"遁": dun, "局数": ju, "元": yuan, "符头": futou, "节气归属": jq_owner}
    if zhirun_status:
        ju_info["置闰状态"] = zhirun_status

    return {
        "version": __version__,
        "input": {"公历": f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{mi:02d}",
                  "zi_sect": zi_sect,
                  "排局法": "置闰" if ju_fa == "zhirun" else "拆补",
                  "盘式": "转盘", "寄宫": "中五寄坤二"},
        "四柱": pillars,
        "节气": {"名": jieqi_name, "交气": jieqi_time.strftime("%Y-%m-%d %H:%M:%S")},
        "局": ju_info,
        "格局": patterns,
        "五不遇时": wubuyu,
        "旬首": {"名": xs_name, "遁仪": yi},
        "值符": {"星": tp["值符星"], "落宫": tp["值符落宫"]},
        "值使": {"门": tp["值使门"], "落宫": tp["值使落宫"],
                 "落宫原始": tp["值使落宫原始"]},
        "旬空": {"日柱空": day_kong, "时柱空": hour_kong},
        "驿马": {"支": ma_zhi, "宫": ma_gong},
        "伏吟": fuyin, "反吟": fanyin,
        "星steps": tp["星steps"], "门steps": tp["门steps"],
        "九宫": gongs,
    }


# ============================================================
# 文本渲染
# ============================================================

def _cell(c, gong):
    """渲染单宫为多行文本。"""
    g = c
    if gong == 5:
        return [f"中5 {GONG_INFO[5][0]}", f"地:{g['地盘干']}", "(寄坤二)", ""]
    shen = g["神"] or ""
    stars = "".join(s.replace("天", "") for s in g["天盘星"])
    tg = "".join(g["天盘干"])
    door = g["门"] or ""
    mark = "·".join(g.get("标注", []))
    kua = GONG_INFO[gong][0]
    return [f"{shen}", f"{stars} {tg}", f"{door} 地:{g['地盘干']}",
            f"{kua}{gong} {mark}".rstrip()]


def render_text(pan):
    lines = []
    lines.append("═" * 21 + " 奇门遁甲 · 时家转盘 " + "═" * 21)
    lines.append(f"公历：{pan['input']['公历']}　排局：{pan['input']['排局法']}法"
                 f"　盘式：转盘（中五寄坤二）")
    p = pan["四柱"]
    lines.append(f"四柱：{p['年柱']}年 {p['月柱']}月 {p['日柱']}日 {p['时柱']}时")
    jq = pan["节气"]
    ju = pan["局"]
    lines.append(f"节气：{jq['名']}（交气 {jq['交气']}）")
    ju_extra = f"，属{ju['节气归属']}"
    if ju.get("置闰状态"):
        ju_extra += f"·{ju['置闰状态']}"
    lines.append(f"局：{ju['遁']}遁{ju['局数']}局 {ju['元']}（符头 {ju['符头']}{ju_extra}）"
                 f"　旬首：{pan['旬首']['名']}（遁{pan['旬首']['遁仪']}）")
    lines.append(f"值符：{pan['值符']['星']} 落{GONG_INFO[pan['值符']['落宫']][0]}"
                 f"{pan['值符']['落宫']}宫　值使：{pan['值使']['门']} "
                 f"落{GONG_INFO[pan['值使']['落宫']][0]}{pan['值使']['落宫']}宫")
    extra = []
    if pan["伏吟"]:
        extra.append("全盘星伏吟")
    if pan["反吟"]:
        extra.append("全盘星反吟")
    lines.append(f"旬空：日空 {pan['旬空']['日柱空']}　时空 {pan['旬空']['时柱空']}"
                 f"　驿马：{pan['驿马']['支']}（{GONG_INFO[pan['驿马']['宫']][0]}"
                 f"{pan['驿马']['宫']}宫）" + ("　" + "·".join(extra) if extra else ""))
    lines.append("")

    # 3×3 洛书方位排布（上南下北：巽4 离9 坤2 / 震3 中5 兑7 / 艮8 坎1 乾6）
    LAYOUT = [[4, 9, 2], [3, 5, 7], [8, 1, 6]]
    W = 16
    sep = "+" + ("-" * W + "+") * 3
    lines.append(sep)
    for row in LAYOUT:
        cells = [_cell(pan["九宫"][g], g) for g in row]
        for r in range(4):
            line = "|"
            for c in cells:
                txt = c[r] if r < len(c) else ""
                pad = W - sum(2 if ord(ch) > 0x2E80 else 1 for ch in txt)
                line += txt + " " * max(0, pad) + "|"
            lines.append(line)
        lines.append(sep)
    lines.append("（每宫从上到下：八神 / 天盘星·天盘干 / 八门·地盘干 / 宫位·标注）")
    # 断局标注块（可计算层；断语方法论见 references/22）
    ky = []
    for gong in [4, 9, 2, 3, 7, 8, 1, 6]:
        g = pan["九宫"][gong]
        if "克应" not in g:
            continue
        extra = "·".join(m for m in g["标注"] if m in ("击刑", "入墓", "门迫", "门制"))
        ky.append(f"{GONG_INFO[gong][0]}{gong} {g['克应']}[{g['星旺衰']}]"
                  + (f"·{extra}" if extra else ""))
    lines.append("克应：" + "　".join(ky[:4]))
    lines.append("　　　" + "　".join(ky[4:]))
    if pan["格局"]:
        lines.append("格局：" + "　".join(pan["格局"]))
    lines.append("═" * 62)
    lines.append(f"奇门排局引擎 v{__version__}　占测参考，趋势化表达，不承诺吉凶成败")
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="时家奇门遁甲排局（转盘·拆补法）")
    ap.add_argument("year", type=int)
    ap.add_argument("month", type=int)
    ap.add_argument("day", type=int)
    ap.add_argument("hour", type=int)
    ap.add_argument("minute", type=int, nargs="?", default=0)
    ap.add_argument("--zi-sect", type=int, default=1, choices=(1, 2),
                    help="子时流派：1=23点换日（默认，时家主流）、2=夜子时不换日")
    ap.add_argument("--ju-fa", default="chaibu", choices=("chaibu", "zhirun"),
                    help="排局法：chaibu=拆补（默认）、zhirun=置闰（超神接气）")
    ap.add_argument("--zhirun-leap-min", type=int, default=8, choices=(8, 9),
                    help="置闰阈值：8=含头尾满九天即闰（默认，元亨利贞派）、9=古籍「超过九天」派")
    ap.add_argument("--json", action="store_true", help="输出 JSON")
    ap.add_argument("--version", action="version", version=f"qimen.py v{__version__}")
    a = ap.parse_args()
    pan = build_pan(a.year, a.month, a.day, a.hour, a.minute, a.zi_sect,
                    a.ju_fa, a.zhirun_leap_min)
    if a.json:
        print(json.dumps(pan, ensure_ascii=False, indent=2))
    else:
        print(render_text(pan))


if __name__ == "__main__":
    main()
