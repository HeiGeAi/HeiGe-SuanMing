#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""八星手机号结构分析引擎。

该模块负责可复现的数字结构计算，以及绑定固定版本的白话自查文案。
它不生成确定性命理断语。规则与解读文案分别版本化，避免改变计算口径时悄悄改写解释。
"""

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

__version__ = "0.2.0"
RULE_PROFILE = "eight_star_v1"
_LEVEL_STRENGTH = {"L1": 4, "L2": 3, "L3": 2, "L4": 1, None: 1}
_STAR_ORDER = ("天医", "生气", "延年", "伏位", "绝命", "祸害", "五鬼", "六煞")
_STAR_TYPE_LABELS = {"auspicious": "吉星", "neutral": "伏位", "inauspicious": "凶星"}
_STAR_CLASSES = {
    "天医": "auspicious",
    "生气": "auspicious",
    "延年": "auspicious",
    "伏位": "neutral",
    "绝命": "inauspicious",
    "祸害": "inauspicious",
    "五鬼": "inauspicious",
    "六煞": "inauspicious",
}
_LEVEL_LABELS = {
    "L1": "L1 · 较高权重",
    "L2": "L2 · 中高权重",
    "L3": "L3 · 中等权重",
    "L4": "L4 · 较低权重",
}
READING_VERSION = "eight_star_reading_v1"
_MODIFIER_GUIDANCE = {
    "hidden": ("隐藏", "传统象征是表达不直接或不显露，不能据此认定有隐瞒、破财或关系问题。", "若想借此自查，可把一件含糊的期待向对方确认，不凭猜测行事。"),
    "amplified": ("放大", "传统象征是突出基础组合的主题；本引擎不把它再加入八星数量，也不推算现实影响倍数。", "若想借此自查，可用一次小尝试验证基础主题对应的行动，先记录结果再决定是否继续。"),
    "edge_fu_wei": ("首尾延续", "当前规则把首尾的 0 或 5 单独记为伏位延续，不能据此判断停滞或未来结果。", "若想借此自查，可给一项长期习惯安排复盘，保留有用的部分。"),
}


class PhoneEnergyError(ValueError):
    """输入或规则配置不符合引擎契约。"""


def _rules_path() -> Path:
    return Path(__file__).resolve().parents[1] / "references" / "phone_energy_rules_v1.json"


def _load_profile(profile: str) -> Dict[str, Any]:
    if profile != RULE_PROFILE:
        raise PhoneEnergyError("未知规则版本：{}".format(profile))
    try:
        data = json.loads(_rules_path().read_text(encoding="utf-8"))
    except OSError as exc:
        raise PhoneEnergyError("八星规则文件不可读取：{}".format(_rules_path())) from exc
    if data.get("profile") != profile or not data.get("stars"):
        raise PhoneEnergyError("八星规则文件格式错误：{}".format(_rules_path()))
    return data


def normalize_number(value: Any) -> str:
    """只保留数字，拒绝不含数字的输入。"""
    if value is None:
        raise PhoneEnergyError("至少需要一个数字")
    digits = re.sub(r"\D", "", str(value))
    if not digits:
        raise PhoneEnergyError("至少需要一个数字")
    return digits


def mask_number(digits: str) -> str:
    if len(digits) <= 4:
        return "*" * len(digits)
    if len(digits) <= 7:
        return digits[:2] + ("*" * (len(digits) - 4)) + digits[-2:]
    return digits[:3] + ("*" * (len(digits) - 7)) + digits[-4:]


def _lookup_stars(profile_data: Dict[str, Any]) -> Dict[str, Tuple[str, str, Optional[str], str]]:
    lookup: Dict[str, Tuple[str, str, Optional[str], str]] = {}
    for star, details in profile_data["stars"].items():
        for pair, level in details["pairs"].items():
            lookup[pair] = (star, details["type"], level, details["domain"])
    return lookup


def _analysis_digits(digits: str, number_kind: str, exclude_leading_one: bool) -> str:
    if exclude_leading_one and number_kind == "mobile" and digits.startswith("1"):
        return digits[1:]
    return digits


def _masked_analysis_digits(digits: str) -> str:
    return mask_number(digits) if len(digits) > 4 else digits


def analyze_phone_number(
    value: Any,
    number_kind: str = "mobile",
    profile: str = RULE_PROFILE,
    exclude_leading_one: bool = False,
) -> Dict[str, Any]:
    """分析一个手机号或任意数字串，返回稳定的结构化结果。"""
    if number_kind not in {"mobile", "plate", "address", "general"}:
        raise PhoneEnergyError("未知号码类型：{}".format(number_kind))
    raw_digits = normalize_number(value)
    analysis_digits = _analysis_digits(raw_digits, number_kind, exclude_leading_one)
    if not analysis_digits:
        raise PhoneEnergyError("去除固定首位后没有可分析的数字")

    profile_data = _load_profile(profile)
    lookup = _lookup_stars(profile_data)
    pairs: List[Dict[str, Any]] = []
    star_counts: Dict[str, int] = {}
    star_strength: Dict[str, int] = {}
    for index in range(max(0, len(analysis_digits) - 1)):
        pair = analysis_digits[index:index + 2]
        match = lookup.get(pair)
        if match:
            star, star_type, level, domain = match
            star_counts[star] = star_counts.get(star, 0) + 1
            star_strength[star] = star_strength.get(star, 0) + _LEVEL_STRENGTH[level]
            pairs.append({
                "index": index,
                "digits": pair,
                "star": star,
                "type": star_type,
                "level": level,
                "domain": domain,
                "evidence": "{}组合属于{}".format(pair, star),
            })
        else:
            pairs.append({
                "index": index,
                "digits": pair,
                "star": None,
                "type": None,
                "level": None,
                "domain": None,
                "evidence": "该相邻组合在当前规则中不独立成星",
            })

    modifiers: List[Dict[str, Any]] = []
    for index, digit in enumerate(analysis_digits):
        if digit not in {"0", "5"}:
            continue
        if 0 < index < len(analysis_digits) - 1:
            base_pair = analysis_digits[index - 1] + analysis_digits[index + 1]
            match = lookup.get(base_pair)
            if match:
                star, star_type, level, domain = match
                effect = profile_data["modifiers"][digit]["middle"]
                modifiers.append({
                    "index": index,
                    "source": analysis_digits[index - 1:index + 2],
                    "modifier_digit": digit,
                    "base_pair": base_pair,
                    "star": star,
                    "type": star_type,
                    "level": level,
                    "domain": domain,
                    "effect": effect,
                    "evidence": "{}位于{}之间，对{}起{}作用".format(digit, base_pair, star, effect),
                })
        else:
            if len(analysis_digits) == 1:
                neighbor = analysis_digits[0]
            elif index == 0:
                neighbor = analysis_digits[1]
            else:
                neighbor = analysis_digits[-2]
            base_pair = neighbor + neighbor
            modifiers.append({
                "index": index,
                "source": analysis_digits[:2] if index == 0 else analysis_digits[-2:],
                "modifier_digit": digit,
                "base_pair": base_pair,
                "star": "伏位",
                "type": "neutral",
                "level": None,
                "domain": profile_data["stars"]["伏位"]["domain"],
                "effect": profile_data["modifiers"][digit]["edge"],
                "evidence": "{}位于号码首尾，按当前规则作为伏位延续".format(digit),
            })

    recognized_pairs = [item for item in pairs if item["star"] is not None]
    tail = recognized_pairs[-1] if recognized_pairs else None
    star_order = list(profile_data["stars"].keys())
    dominant = None
    if star_counts:
        dominant = sorted(
            star_counts,
            key=lambda star: (-star_counts[star], -star_strength[star], star_order.index(star)),
        )[0]
    auspicious_count = sum(1 for item in recognized_pairs if item["type"] == "auspicious")
    neutral_count = sum(1 for item in recognized_pairs if item["type"] == "neutral")
    inauspicious_count = sum(1 for item in recognized_pairs if item["type"] == "inauspicious")

    return {
        "engine": "phone_energy",
        "engine_version": __version__,
        "rules_profile": profile,
        "input": {
            "kind": number_kind,
            "digits_count": len(raw_digits),
            "analysis_digits": _masked_analysis_digits(analysis_digits),
            "masked": mask_number(raw_digits),
            "exclude_leading_one": exclude_leading_one,
        },
        "pairs": pairs,
        "modifiers": modifiers,
        "summary": {
            "total_pairs": len(pairs),
            "recognized_pairs": len(recognized_pairs),
            "unclassified_pairs": len(pairs) - len(recognized_pairs),
            "star_counts": star_counts,
            "dominant_star": dominant,
            "auspicious_count": auspicious_count,
            "neutral_count": neutral_count,
            "inauspicious_count": inauspicious_count,
            "tail_pair": tail["digits"] if tail else None,
            "tail_star": tail["star"] if tail else None,
        },
        "limitations": [
            "结果基于八星数字磁场规则，仅供文化研究和自我观察。",
            "八星流派对首位、0、5、尾号和混合评分存在差异，请以规则版本为准。",
            "结果不构成医疗、法律、投资或人生决策建议。",
        ],
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="八星手机号结构分析")
    parser.add_argument("number", help="手机号或数字串，可含空格、短横线和括号")
    parser.add_argument("--kind", choices=["mobile", "plate", "address", "general"], default="mobile")
    parser.add_argument("--profile", default=RULE_PROFILE)
    parser.add_argument("--exclude-leading-one", action="store_true", help="手机号分析时排除固定首位 1")
    parser.add_argument("--json", action="store_true", dest="as_json", help="输出 JSON")
    parser.add_argument("--pretty", action="store_true", help="JSON 缩进输出")
    parser.add_argument("--html", nargs="?", const="", metavar="PATH", help="生成项目统一风格的 HTML 报告，可选输出路径")
    return parser


def _print_text(result: Dict[str, Any]) -> None:
    summary = result["summary"]
    print("八星手机号结构分析")
    print("号码：{}".format(result["input"]["masked"]))
    print("规则：{}，引擎：{}".format(result["rules_profile"], result["engine_version"]))
    print("主导星：{}".format(summary["dominant_star"] or "无可识别星组"))
    print("吉星：{}，伏位：{}，凶星：{}".format(summary["auspicious_count"], summary["neutral_count"], summary["inauspicious_count"]))
    print("尾部：{} {}".format(summary["tail_pair"] or "无", summary["tail_star"] or ""))
    print("\n相邻组合：")
    for item in result["pairs"]:
        label = item["star"] or "未分类"
        level = item["level"] or ""
        print("  {}  {} {}".format(item["digits"], label, level))
    if result["modifiers"]:
        print("\n0/5 修饰：")
        for item in result["modifiers"]:
            print("  {} → {}，{}".format(item["source"], item["star"], item["effect"]))
    print("\n限制：{}".format(result["limitations"][0]))


def _esc(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _type_label(star_type: Optional[str]) -> str:
    return _STAR_TYPE_LABELS.get(star_type or "", "未分类")


def _star_class(star: Optional[str], star_type: Optional[str] = None) -> str:
    return _STAR_CLASSES.get(star or "", star_type or "neutral")


def build_phone_energy_reading(result: Dict[str, Any]) -> Dict[str, Any]:
    """把计算结果绑定到固定文案；不改计算结果，不推断真实人格或未来事件。"""
    path = _rules_path().with_name("phone_energy_readings_v1.json")
    try:
        library = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise PhoneEnergyError("八星解读文案不可读取：{}".format(path)) from exc
    if (not isinstance(library, dict)
            or library.get("version") != READING_VERSION
            or library.get("rules_profile") != result.get("rules_profile")
            or not isinstance(library.get("stars"), dict)
            or set(library.get("stars", {})) != set(_STAR_ORDER)):
        raise PhoneEnergyError("解读文案与当前规则版本不匹配")
    required = {"theme", "meaning", "strength", "watch", "scenario", "question",
                "action", "script", "metric", "headline", "short_action"}
    for entry in library["stars"].values():
        if not isinstance(entry, dict) or not all(isinstance(entry.get(key), str) and entry[key].strip() for key in required):
            raise PhoneEnergyError("八星解读文案缺少必要的解释或行动字段")

    pairs = result.get("pairs", [])
    present = []
    for star in _STAR_ORDER:
        evidence = [dict(item) for item in pairs if item.get("star") == star]
        if not evidence:
            continue
        entry = dict(library["stars"][star])
        entry.update(star=star, count=len(evidence), pairs=evidence,
                     weight=sum(_LEVEL_STRENGTH.get(item.get("level"), 1) for item in evidence))
        present.append(entry)
    present.sort(key=lambda item: (-item["count"], -item["weight"], _STAR_ORDER.index(item["star"])))
    by_star = {item["star"]: item for item in present}
    main = present[0] if present else None
    recognized = [item for item in pairs if item.get("star") in by_star]
    tail = recognized[-1] if recognized else None
    # 阅读顺序：主导主题、另一突出主题、末个有效组合；相同主题去重。
    focus = present[:2]
    if tail and by_star[tail["star"]] not in focus:
        focus = focus + [by_star[tail["star"]]]
    strengths = [item for item in present if _STAR_CLASSES[item["star"]] == "auspicious"]
    bridges = []
    for stars, title, reading, action in (
        (("六煞", "五鬼"), "先确认感受，再调整计划", "当关系与变化两个主题同时出现，可以自查一个场景：是否因为一次未确认的情绪，临时改变了原本的安排。", "先向对方确认事实，把新想法记下来，等约定的复盘时间再判断要不要调整。"),
        (("五鬼", "绝命"), "新点子落地前，留出检查", "变化与快速决定两个主题同时出现时，可以自查：是否一想到新方法，就在缺少验证的情况下作出较大的承诺。", "先写一个小实验，再写停止条件；只在结果支持时扩大行动。"),
        (("生气", "天医"), "把联系变成明确协作", "人缘与资源两个主题同时出现，可以作为一次协作练习的入口：把聊过的机会说清楚，看看双方实际能提供什么。", "从一个现有联系开始，确认一件小事、双方投入和下一次跟进时间。"),
        (("祸害", "六煞"), "少猜意思，多确认需要", "表达与关系两个主题同时出现，可以自查：是否因为不好意思问清楚，让一个小误会拖得更久。", "用事实、感受、请求表达，再邀请对方复述理解。"),
    ):
        if all(star in by_star for star in stars):
            bridges.append({"stars": list(stars), "title": title, "reading": reading, "action": action})

    primary = main or {"theme": "先观察一件真实小事", "headline": "当前组合不足，先从真实经历开始。",
                       "short_action": "记录一件想改善的小事，先找事实，不补写命理结论。",
                       "action": "写下事情经过、自己的做法和希望改变的一点。",
                       "metric": "有一条真实记录即可，不需要让经历符合某个星名。"}
    practice = [
        {"period": "第 1 天", "title": "先核对是否符合自己", "action": "选一个最近发生的具体事件。写下事实、自己的反应和结果；若报告场景不符合自己，就写不符合，不必对号入座。", "check": "留下一条真实记录，作为本周比较的起点。"},
        {"period": "第 2 至 3 天", "title": primary["theme"], "action": primary["action"], "check": primary["metric"]},
        {"period": "第 4 至 6 天", "title": focus[1]["theme"] if len(focus) > 1 else "重复一次，观察变化", "action": focus[1]["action"] if len(focus) > 1 else "在另一个相似的小场景里再试一次。记录做法和结果；若不适用，换一个由真实需要决定的小目标。", "check": focus[1]["metric"] if len(focus) > 1 else "有两次可比较的记录，而不是只靠当天的感觉。"},
        {"period": "第 7 天", "title": "决定什么值得留下", "action": "对照第一天，检查误会、返工或勉强承诺是否变化。保留有效做法；没有变化或不适用的建议可以停止。", "check": "写下继续做的一件事、停止做的一件事；结果由现实记录判断。"},
    ]
    if main:
        other_distribution = "、".join("{} {} 组".format(item["theme"], item["count"]) for item in present[1:3])
        summary = result.get("summary", {})
        overview = "这个号码按当前规则识别出 {} 组相邻数字，另有 {} 组暂不单独归类。最多的是「{}」，共 {} 组".format(
            summary.get("recognized_pairs", 0), summary.get("unclassified_pairs", 0), main["theme"], main["count"])
        if other_distribution:
            overview += "；另外还有「{}」。".format(other_distribution)
        else:
            overview += "。"
        overview += "这里的数量只是在数相邻数字出现了几次，不是在给你的人生、能力或风险打分。"
        if strengths:
            overview += "同时也能看到「{}」这类可以借鉴的主题。".format("、".join(item["theme"] for item in strengths))
        if len(present) > 3:
            overview += "其余主题会放在后面的详细解读里。"
        overview += "简单说，可以先从「{}」开始，用一周看看现实中有没有变化。".format(main["short_action"])
    else:
        overview = "这个号码里暂时没有能按当前规则独立识别的组合，所以不适合硬套某个星名。先从一件真实的小事开始记录，看看自己真正想改善什么，再决定要不要继续看后面的说明。"
    return {"version": library["version"], "basis": library["basis"], "present": present,
            "main": main, "focus": focus, "strengths": strengths, "tail": tail,
            "bridges": bridges, "headline": primary["headline"], "first_step": primary["short_action"],
            "overview": overview, "practice": practice}


def _reading_evidence(entry: Dict[str, Any]) -> str:
    groups = "、".join("{}（{}）".format(item["digits"], item.get("level") or "不分级") for item in entry["pairs"])
    return "{}：{}，共 {} 组".format(entry["star"], groups, entry["count"])


def _reading_cards(reading: Dict[str, Any]) -> str:
    if not reading["present"]:
        return '<p class="empty-state">当前没有可独立识别的八星组合，无法生成主导主题或个性解读。0 / 5 的修饰如有记录，会单独说明；不会补造缺失的结论。</p>'
    cards = []
    for index, entry in enumerate(reading["present"], 1):
        fields = "".join('<div class="reading-field"><h4>{}</h4><p>{}</p></div>'.format(label, _esc(entry[key]))
                         for label, key in (("简单说", "meaning"), ("可以借鉴的地方", "strength"),
                                            ("留意一下", "watch"), ("生活里可能是", "scenario")))
        cards.append('<article class="reading-chapter" id="reading-{index}"><div class="reading-heading"><span class="entry-no">{index:02d}</span><div><h3>{theme}</h3><p class="basis">{evidence}</p></div></div>{fields}<div class="self-check"><b>问问自己</b><p>{question}</p></div><div class="action-inset"><h4>如果符合自己，可以这样做</h4><p>{action}</p><h4>沟通句式</h4><blockquote>{script}</blockquote><p class="measure"><b>怎么检查：</b>{metric}</p></div></article>'.format(
            index=index, theme=_esc(entry["theme"]), evidence=_esc(_reading_evidence(entry)), fields=fields,
            question=_esc(entry["question"]), action=_esc(entry["action"]), script=_esc(entry["script"]), metric=_esc(entry["metric"])))
    return "".join(cards)


def _focus_cards(reading: Dict[str, Any]) -> str:
    if not reading["focus"]:
        return '<p class="empty-state">先使用下方的通用自查练习，不把无法归类的数字解释成好坏。</p>'
    return "".join('<article class="focus-item"><span class="entry-no">{index:02d}</span><div><h3>{theme}</h3><p>{action}</p><a href="#reading-{target}">出现 {count} 组 · 查看详细解读 ↗</a></div></article>'.format(
        index=index, theme=_esc(entry["theme"]), action=_esc(entry["short_action"]), count=entry["count"],
        target=reading["present"].index(entry) + 1) for index, entry in enumerate(reading["focus"], 1))


def _combination_cards(reading: Dict[str, Any]) -> str:
    by_star = {item["star"]: item for item in reading["present"]}
    if not reading["bridges"]:
        return '<p class="empty-state">本次没有触发文案库收录的组合观察。可以从单个主题开始，不额外叠加推断。</p>'
    return "".join('<article class="combination"><h3>{title}</h3><p class="basis">{evidence}</p><p>{reading}</p><p><b>试着这样做：</b>{action}</p></article>'.format(
        title=_esc(item["title"]), evidence=_esc("；".join(_reading_evidence(by_star[star]) for star in item["stars"])),
        reading=_esc(item["reading"]), action=_esc(item["action"])) for item in reading["bridges"])


def _practice_cards(reading: Dict[str, Any]) -> str:
    return "".join('<article class="practice-step"><div class="period">{period}</div><h3>{title}</h3><p>{action}</p><p class="measure"><b>完成标准：</b>{check}</p></article>'.format(
        **{key: _esc(value) for key, value in item.items()}) for item in reading["practice"])


def _pair_cards(result: Dict[str, Any], reading: Dict[str, Any]) -> str:
    cards: List[str] = []
    entries = {item["star"]: item for item in reading["present"]}
    for item in result.get("pairs", []):
        star = item.get("star")
        star_type = item.get("type")
        entry = entries.get(star)
        explanation = entry["theme"] if entry else "含 0 或 5 的相邻组合不独立归类，相关修饰另见下方；未归类不代表不吉利。"
        action = entry["short_action"] if entry else "不单独下好坏结论，也不把它计入八星数量。"
        level_label = _LEVEL_LABELS.get(item.get("level"), "伏位不分级" if star == "伏位" else "不独立成星")
        cards.append(
            '<article class="pair-card {cls}"><div class="pair-top">'
            '<span class="pair-digits">{digits}</span><span class="pair-level">{level}</span>'
            '</div><h3>{star}</h3><p class="pair-type">{type_label}</p>'
            '<p class="pair-domain">{explanation}</p><p class="pair-action"><b>行动提示：</b>{action}</p><p class="pair-evidence">{evidence}</p></article>'.format(
                cls=_esc(_star_class(star, star_type)),
                digits=_esc(item.get("digits")),
                level=_esc(level_label),
                star=_esc(star or "未分类"),
                type_label=_esc(_type_label(star_type)),
                explanation=_esc(explanation),
                action=_esc(action),
                evidence=_esc(item.get("evidence")),
            )
        )
    return "".join(cards)


def _star_rows(result: Dict[str, Any]) -> str:
    counts = result.get("summary", {}).get("star_counts", {})
    max_count = max([1] + [int(counts.get(star, 0)) for star in _STAR_ORDER])
    rows: List[str] = []
    for star in _STAR_ORDER:
        count = int(counts.get(star, 0))
        css_class = _STAR_CLASSES[star]
        width = round(count / max_count * 100)
        star_type = "auspicious" if css_class == "auspicious" else "neutral" if css_class == "neutral" else "inauspicious"
        rows.append(
            '<div class="star-row {cls}"><div class="star-name">{star}<small>{type_label}</small></div>'
            '<div class="star-track"><span style="width:{width}%"></span></div>'
            '<div class="star-count">{count}</div></div>'.format(
                cls=css_class,
                star=_esc(star),
                type_label=_esc(_type_label(star_type)),
                width=width,
                count=count,
            )
        )
    return "".join(rows)


def _modifier_cards(result: Dict[str, Any]) -> str:
    modifiers = result.get("modifiers", [])
    if not modifiers:
        return '<p class="empty-state">当前号码没有触发 0 或 5 的修饰记录。</p>'
    cards: List[str] = []
    for item in modifiers:
        label, meaning, action = _MODIFIER_GUIDANCE.get(item.get("effect"), ("未收录修饰", "当前解读库未收录此标记。", "保留原始记录，不补写结论。"))
        scope = "这里将 {} 两侧的数字合看为 {}，对应{}。这条修饰不额外增加该星的数量。".format(item.get("source"), item.get("base_pair"), item.get("star"))
        if item.get("effect") == "edge_fu_wei":
            scope = "这是首尾位置的单独标注，不等于出现了一个新的相邻数字对，也不加入主导星计算。"
        cards.append(
            '<article class="modifier-card"><div class="modifier-digit">{digit}</div><div>'
            '<h3>{source} · {label}</h3><p>{scope}</p><p>{meaning}</p>'
            '<p><b>怎么使用：</b>{action}</p><span class="basis">规则标记：{effect}；基础组合：{base_pair}</span></div></article>'.format(
                digit=_esc(item.get("modifier_digit")),
                source=_esc(item.get("source")),
                label=_esc(label), scope=_esc(scope), meaning=_esc(meaning), action=_esc(action),
                effect=_esc(item.get("effect")),
                base_pair=_esc(item.get("base_pair")),
            )
        )
    return "".join(cards)


def _result_sequence(result: Dict[str, Any]) -> str:
    """渲染首屏可核对的相邻组合结果，完整细节留在后面的证据区。"""
    items: List[str] = []
    for index, item in enumerate(result.get("pairs", []), 1):
        star = item.get("star") or "未分类"
        star_type = item.get("type") or "neutral"
        items.append(
            '<li class="result-pair {cls}"><span class="result-pair-index">{index:02d}</span>'
            '<span class="result-pair-digits">{digits}</span><span class="result-pair-star">{star}</span>'
            '<span class="result-pair-kind">{kind}</span></li>'.format(
                cls=_esc(_star_class(item.get("star"), star_type)),
                index=index,
                digits=_esc(item.get("digits")),
                star=_esc(star),
                kind=_esc(_type_label(item.get("type"))),
            )
        )
    return "".join(items) or '<li class="empty-state">当前没有可拆分的相邻数字。</li>'


def _result_distribution(result: Dict[str, Any]) -> str:
    counts = result.get("summary", {}).get("star_counts", {})
    rows: List[str] = []
    for star in _STAR_ORDER:
        star_class = _STAR_CLASSES[star]
        star_type = "auspicious" if star_class == "auspicious" else "neutral" if star_class == "neutral" else "inauspicious"
        rows.append(
            '<div class="result-distribution-item {cls}"><span class="result-distribution-name">{star}</span>'
            '<span class="result-distribution-kind">{kind}</span><strong>{count}</strong><small>组</small></div>'.format(
                cls=star_class,
                star=_esc(star),
                kind=_esc(_type_label(star_type)),
                count=int(counts.get(star, 0)),
            )
        )
    return "".join(rows)


def _default_html_path(result: Dict[str, Any]) -> Path:
    masked = str(result.get("input", {}).get("masked", "号码"))
    suffix = re.sub(r"[^0-9]", "", masked[-4:]) or "脱敏"
    return Path.cwd() / "手机号八星报告-{}.html".format(suffix)


def render_phone_energy_html(result: Dict[str, Any]) -> str:
    """将八星结构结果渲染为项目统一的 noir-vermilion 风格 HTML。"""
    input_data = result.get("input", {})
    summary = result.get("summary", {})
    masked = _esc(input_data.get("masked", "已脱敏号码"))
    dominant_raw = summary.get("dominant_star") or "无可识别星组"
    dominant = _esc(dominant_raw)
    tail_pair = _esc(summary.get("tail_pair") or "无")
    tail_star = _esc(summary.get("tail_star") or "无")
    total_pairs = int(summary.get("total_pairs", 0))
    recognized_pairs = int(summary.get("recognized_pairs", 0))
    recognized_rate = round(recognized_pairs / total_pairs * 100) if total_pairs else 0
    dominant_type = _type_label(next((item.get("type") for item in result.get("pairs", []) if item.get("star") == dominant_raw), None))
    limitations = "".join("<li>{}</li>".format(_esc(item)) for item in result.get("limitations", []))
    reading = build_phone_energy_reading(result)
    main = reading["main"]
    ranking = "；".join("{} {} 组、权重和 {}".format(item["star"], item["count"], item["weight"]) for item in reading["present"])
    main_explanation = ("本次{}出现 {} 组。主导星先比较出现次数，同次数再比较规则权重之和，仍相同则按规则文件顺序排列。完整排序：{}。权重只用于这一步排序，不是人的能力、运势或风险分数。".format(main["star"], main["count"], ranking)
                        if main else "本次没有可独立识别的星组，不生成主导星或号码专属结论。")
    if reading["tail"]:
        tail = reading["tail"]
        tail_explanation = "最后一个有效组合是第 {} 组 {}（{}）。".format(tail["index"] + 1, tail["digits"], tail["star"])
        if tail["index"] < total_pairs - 1:
            tail_explanation += "它后面还有 {} 组未分类组合，因此不是号码字面上的最后两位。".format(total_pairs - tail["index"] - 1)
        tail_explanation += "它仅作为另一阅读入口，不代表最终命运，也不额外加权。"
    else:
        tail_explanation = "当前没有有效组合，不能生成尾部星组结论。"
    resources = ("本次也出现了{}。可以从相关章节选择协作或资源整理的练习；这些标签不保证现实收益。".format(
        "；".join(_reading_evidence(item) for item in reading["strengths"])) if reading["strengths"] else
        "本次未出现传统吉星标签，不代表你没有优势、机会或人缘。先从报告里符合自身经历的场景开始，真实能力需要用实际表现判断。")
    kind_label = {"mobile": "手机号", "plate": "车牌", "address": "门牌", "general": "通用数字"}.get(input_data.get("kind"), "通用数字")
    result_line = "已按{}完成计算：共拆出 {} 组相邻数字，识别 {} 组，{} 组暂不单独归类。".format(
        kind_label, total_pairs, recognized_pairs, total_pairs - recognized_pairs)
    css = """
:root{--ink:#0c0b0e;--ink-2:#14121a;--paper:#ece3d2;--paper-dim:#a89e8a;--paper-faint:#6f6757;--gold:#c9a45c;--gold-bright:#e3c478;--gold-deep:#9a7b3e;--cinnabar:#bb4232;--cinnabar-bright:#d8543f;--jade:#5e8478;--jade-bright:#7da99a;--water:#3f6b86;--line:rgba(201,164,92,.20);--line-soft:rgba(201,164,92,.10);--serif:'Noto Serif SC','Songti SC','STSong','Songti TC',serif;--num:'Cormorant Garamond','Songti SC',Georgia,'Times New Roman',serif;--gutter:clamp(18px,4vw,40px)}
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:var(--serif);background:var(--ink);color:var(--paper);line-height:1.9;font-weight:300;letter-spacing:.02em;-webkit-font-smoothing:antialiased;position:relative}
body:before{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;background:radial-gradient(820px 620px at 80% -10%,rgba(217,115,51,.15),transparent 60%),radial-gradient(680px 680px at 10% 6%,rgba(187,66,50,.10),transparent 62%),radial-gradient(900px 900px at 50% 122%,rgba(63,107,134,.08),transparent 60%)}
body:after{content:'';position:fixed;inset:0;z-index:0;pointer-events:none;opacity:.04;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='160' height='160'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='.85' numOctaves='3'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E")}
.wrap{position:relative;z-index:1;max-width:920px;margin:0 auto;padding:0 var(--gutter)}
.hero{min-height:92vh;display:flex;flex-direction:column;justify-content:center;align-items:center;text-align:center;position:relative;padding:80px 30px 64px}
.hero:before{content:'';position:absolute;left:0;top:0;bottom:0;width:9px;background:linear-gradient(var(--cinnabar),#d97333 50%,var(--cinnabar));z-index:3}
.hero-frame{position:absolute;inset:34px;border:1px solid var(--line);pointer-events:none}.hero-frame:before,.hero-frame:after{content:'';position:absolute;width:18px;height:18px;border:1px solid var(--gold)}.hero-frame:before{top:-1px;left:-1px;border-right:0;border-bottom:0}.hero-frame:after{bottom:-1px;right:-1px;border-left:0;border-top:0}
.seal{width:76px;height:76px;border:2px solid var(--cinnabar);border-radius:6px;display:flex;align-items:center;justify-content:center;margin-bottom:34px;font-size:44px;font-weight:900;color:var(--cinnabar-bright);box-shadow:0 0 34px rgba(187,66,50,.3);transform:rotate(-3deg)}
.pre{font-size:15px;letter-spacing:.42em;color:var(--gold);margin-bottom:24px;padding-left:.42em}.hero h1{font-size:clamp(38px,13vw,118px);font-weight:900;line-height:.95;color:var(--paper);text-shadow:0 0 56px rgba(217,115,51,.32);white-space:nowrap;letter-spacing:.08em}.hero .name{font-size:clamp(20px,4vw,28px);letter-spacing:.28em;color:var(--gold-bright);margin:30px 0 10px;padding-left:.28em}.hero .meta{font-family:var(--num);font-size:16px;letter-spacing:.08em;color:var(--paper-dim);font-style:italic}.meta-tail{white-space:nowrap}.hero .verse{margin-top:40px;max-width:590px;font-size:clamp(16px,2.5vw,20px);color:var(--paper);line-height:2.15}.hero .verse b{color:#d97333;font-weight:500}.hero-links{display:flex;gap:12px;justify-content:center;flex-wrap:wrap;margin-top:34px}.hero-links a{font-size:13px;letter-spacing:.16em;color:var(--gold-bright);text-decoration:none;border:1px solid var(--gold-deep);padding:7px 16px;transition:background .2s ease,color .2s ease}.hero-links a:hover,.hero-links a:focus-visible{background:var(--gold);color:var(--ink)}.scroll-cue{position:absolute;bottom:46px;right:56px;font-size:12px;letter-spacing:.35em;color:var(--paper-faint);writing-mode:vertical-rl;text-decoration:none}.scroll-cue:after{content:'';display:block;width:1px;height:42px;background:linear-gradient(var(--gold),transparent);margin:14px auto 0}
.reading-index{margin:88px 0 48px;padding:72px 30px 30px;background:#edeae3;color:#17141a;position:relative;box-shadow:0 16px 50px rgba(0,0,0,.28)}.reading-index:before{content:'';position:absolute;top:0;left:0;right:0;height:8px;background:linear-gradient(90deg,var(--cinnabar),#d97333 50%,var(--cinnabar))}.reading-index .reading-number{font-family:var(--num);font-size:13px;letter-spacing:.25em;color:#8f3028;font-style:italic}.reading-index h2{font-size:clamp(26px,5vw,38px);font-weight:600;letter-spacing:.12em;margin-top:10px;color:#17141a}.reading-index>p{font-size:15px;line-height:1.9;color:#625e58;margin-top:10px}.reading-index ol{list-style:none;display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:1px;margin-top:34px;border:1px solid rgba(20,18,22,.12);background:rgba(20,18,22,.12)}.reading-index li{background:#edeae3;min-width:0}.reading-index a{display:block;padding:18px 15px 16px;color:#17141a;text-decoration:none;min-height:118px}.reading-index a:hover,.reading-index a:focus-visible{background:#e1d7c4}.reading-index li b{display:block;font-family:var(--num);font-size:26px;color:#a24a3e;font-style:italic}.reading-index li span{display:block;font-size:15px;font-weight:600;margin-top:8px;letter-spacing:.08em}.reading-index li small{display:block;font-family:var(--num);font-size:11px;letter-spacing:.08em;color:#8d8880;margin-top:4px}.reading-tip{font-size:13px!important;color:#8d8880!important;margin-top:24px!important}
section{padding:76px 0;position:relative}.sec-head{display:flex;align-items:baseline;gap:22px;margin-bottom:42px}.sec-no{font-size:clamp(46px,8vw,68px);color:var(--gold-deep);line-height:.9;opacity:.85;flex:none;font-weight:900}.sec-title{font-size:clamp(26px,5vw,38px);color:var(--paper);letter-spacing:.1em;line-height:1.4;font-weight:600}.sec-sub{font-family:var(--num);font-size:14px;color:var(--gold);letter-spacing:.28em;margin-top:6px;text-transform:uppercase;font-style:italic}.lead{font-size:clamp(19px,2.6vw,23px);border-left:2px solid var(--cinnabar);padding-left:22px;margin-bottom:32px;line-height:1.95}.lead strong{color:var(--gold-bright);font-weight:600}
.result-section{padding-top:54px}.result-summary{border:1px solid var(--line);background:linear-gradient(145deg,rgba(201,164,92,.08),rgba(12,11,14,.35));padding:28px;margin-top:8px}.result-summary-head{display:flex;align-items:flex-start;justify-content:space-between;gap:22px;border-bottom:1px solid var(--line-soft);padding-bottom:22px}.result-summary-number{font-family:var(--num);font-size:clamp(34px,7vw,62px);color:var(--paper);letter-spacing:.08em;font-style:italic;overflow-wrap:anywhere}.result-summary-label{font-size:13px;color:var(--gold);letter-spacing:.14em;margin-bottom:5px}.result-summary-meta{font-size:14px;color:var(--paper-dim);line-height:1.8}.result-summary-note{max-width:420px;font-size:15px;color:var(--paper-dim);line-height:1.9;text-align:right}.result-summary-note strong{display:block;color:var(--gold-bright);font-size:20px;font-weight:600}.result-stats{margin-top:22px}.result-subheading{font-size:20px;color:var(--gold-bright);font-weight:600;margin:30px 0 14px}.result-sequence{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:1px;list-style:none;background:var(--line-soft);border:1px solid var(--line)}.result-pair{background:var(--ink);padding:15px 12px;min-width:0;display:grid;grid-template-columns:30px 1fr;grid-template-areas:'index digits' 'index star' 'index kind';column-gap:9px;align-items:center}.result-pair-index{grid-area:index;font-family:var(--num);font-size:15px;color:var(--gold-deep);font-style:italic}.result-pair-digits{grid-area:digits;font-family:var(--num);font-size:26px;color:var(--gold-bright);font-style:italic;letter-spacing:.08em}.result-pair-star{grid-area:star;font-size:14px;color:var(--paper);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.result-pair-kind{grid-area:kind;font-size:11px;color:var(--paper-faint)}.result-pair.auspicious{border-top:2px solid var(--jade-bright)}.result-pair.neutral{border-top:2px solid var(--gold)}.result-pair.inauspicious{border-top:2px solid var(--cinnabar-bright)}.result-distribution{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line-soft);border:1px solid var(--line)}.result-distribution-item{background:var(--ink);padding:16px 14px;display:grid;grid-template-columns:1fr auto auto;grid-template-areas:'name count unit' 'kind count unit';column-gap:8px;align-items:center}.result-distribution-name{grid-area:name;font-size:16px;color:var(--paper)}.result-distribution-kind{grid-area:kind;font-size:12px;color:var(--paper-faint)}.result-distribution-item strong{grid-area:count;font-family:var(--num);font-size:30px;color:var(--gold-bright);font-weight:600}.result-distribution-item small{grid-area:unit;font-size:12px;color:var(--paper-faint);align-self:end;padding-bottom:5px}.result-distribution-item.auspicious{border-left:3px solid var(--jade-bright)}.result-distribution-item.neutral{border-left:3px solid var(--gold)}.result-distribution-item.inauspicious{border-left:3px solid var(--cinnabar-bright)}
.heige-read{margin-top:26px;padding:20px 22px 20px 24px;border-left:3px solid var(--cinnabar);background:rgba(187,66,50,.08);box-shadow:inset 0 0 0 1px rgba(187,66,50,.14)}.heige-read span{display:inline-block;font-size:13px;font-weight:600;letter-spacing:.16em;color:var(--paper);background:var(--cinnabar);border-radius:2px;padding:3px 10px}.heige-read p{margin:10px 0 0;font-size:15px;line-height:1.9;color:var(--paper-dim)}
.overview-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:1px;background:var(--line-soft);border:1px solid var(--line)}.stat{background:var(--ink);padding:26px 20px;min-height:148px}.stat-label{font-size:13px;color:var(--paper-faint);letter-spacing:.14em;margin-bottom:14px}.stat-value{font-size:clamp(25px,4vw,38px);color:var(--gold-bright);font-weight:700;line-height:1.15;overflow-wrap:anywhere}.stat-note{font-size:13px;color:var(--paper-dim);margin-top:9px}
.pair-grid{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1px;background:var(--line-soft);border:1px solid var(--line)}.pair-card{background:var(--ink);padding:24px 22px;min-width:0;border-top:2px solid var(--paper-faint)}.pair-card.auspicious{border-top-color:var(--jade-bright)}.pair-card.neutral{border-top-color:var(--gold)}.pair-card.inauspicious{border-top-color:var(--cinnabar-bright)}.pair-top{display:flex;align-items:center;justify-content:space-between;gap:12px}.pair-digits{font-family:var(--num);font-size:32px;letter-spacing:.12em;color:var(--gold-bright);font-style:italic}.pair-level{font-family:var(--num);font-size:12px;color:var(--paper-faint);border:1px solid var(--line-soft);padding:2px 8px;white-space:nowrap}.pair-card h3{font-size:22px;font-weight:600;margin-top:14px;color:var(--paper)}.pair-type{font-size:13px;color:var(--jade-bright);margin-top:2px}.pair-domain{font-size:15px;color:var(--paper-dim);margin-top:9px}.pair-action{font-size:14px;color:var(--jade-bright);margin-top:13px;line-height:1.85}.pair-action b{color:var(--gold-bright);font-weight:500}.pair-evidence{font-size:13px;color:var(--paper-faint);margin-top:14px;line-height:1.7}
.reading-chapters{display:grid;gap:1px;background:var(--line-soft);border:1px solid var(--line)}.reading-chapter{background:var(--ink);padding:32px 28px}.reading-heading{display:flex;gap:18px;align-items:flex-start;border-bottom:1px solid var(--line-soft);padding-bottom:20px;margin-bottom:20px}.entry-no{font-family:var(--num);font-size:28px;color:var(--gold-deep);font-style:italic;line-height:1}.reading-heading h3{font-size:25px;color:var(--gold-bright);font-weight:600;line-height:1.35}.reading-heading .basis{margin-top:8px}.reading-field{padding:15px 0;border-bottom:1px solid var(--line-soft)}.reading-field h4,.action-inset h4{font-size:15px;color:var(--gold);font-weight:600;letter-spacing:.08em;margin-bottom:6px}.reading-field p,.action-inset p,.self-check p{font-size:15px;color:var(--paper-dim);line-height:1.9;margin:0}.self-check{margin-top:18px;padding:16px 18px;background:rgba(201,164,92,.07);border-left:2px solid var(--gold)}.self-check b{font-size:13px;color:var(--gold-bright);letter-spacing:.1em}.self-check p{margin-top:6px;color:var(--paper)}.action-inset{margin-top:18px;padding:20px;background:rgba(187,66,50,.08);border-left:3px solid var(--cinnabar)}.action-inset h4{color:var(--cinnabar-bright)}.action-inset blockquote{margin:13px 0;padding:10px 14px;border-left:1px solid var(--gold-deep);color:var(--paper);font-size:15px;line-height:1.9}.measure{margin-top:10px!important;font-size:14px!important}.measure b{color:var(--gold-bright);font-weight:500}.focus-list,.combination-grid,.practice-grid{display:grid;gap:1px;background:var(--line-soft);border:1px solid var(--line)}.focus-item,.combination,.practice-step{background:var(--ink);padding:24px}.focus-item{display:grid;grid-template-columns:48px 1fr;gap:16px}.focus-item h3,.combination h3,.practice-step h3{font-size:20px;color:var(--paper);font-weight:600;margin-bottom:7px}.focus-item p,.combination p,.practice-step p{font-size:15px;color:var(--paper-dim);line-height:1.9;margin:0 0 10px}.focus-item a{font-size:13px;color:var(--jade-bright);text-decoration:none}.combination-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.combination{border-top:2px solid var(--cinnabar)}.combination p b{color:var(--gold-bright);font-weight:500}.practice-grid{grid-template-columns:repeat(4,minmax(0,1fr))}.practice-step{min-width:0}.period{font-family:var(--num);font-size:13px;color:var(--cinnabar-bright);letter-spacing:.12em;margin-bottom:12px}.practice-step .measure{padding-top:10px;border-top:1px solid var(--line-soft)}
.star-list{display:grid;gap:14px}.star-row{display:grid;grid-template-columns:120px 1fr 32px;align-items:center;gap:16px}.star-name{font-size:18px;color:var(--paper);display:flex;justify-content:space-between;gap:8px}.star-name small{font-size:12px;color:var(--paper-faint);align-self:center;white-space:nowrap}.star-track{height:12px;border:1px solid var(--line-soft);background:rgba(255,255,255,.04);border-radius:8px;overflow:hidden}.star-track span{display:block;height:100%;border-radius:8px;background:var(--gold)}.star-row.auspicious .star-track span{background:linear-gradient(90deg,#2f4a40,var(--jade-bright))}.star-row.inauspicious .star-track span{background:linear-gradient(90deg,#7a2018,var(--cinnabar-bright))}.star-count{font-family:var(--num);font-size:19px;color:var(--gold-bright);text-align:right}
.modifier-card{display:grid;grid-template-columns:72px 1fr;gap:20px;align-items:start;padding:24px 0;border-top:1px solid var(--line-soft)}.modifier-digit{width:64px;height:64px;display:flex;align-items:center;justify-content:center;border:1px solid var(--gold-deep);color:var(--gold-bright);font-family:var(--num);font-size:38px;font-style:italic}.modifier-card h3{font-size:20px;font-weight:600;color:var(--paper);margin-bottom:7px}.modifier-card p{font-size:15px;color:var(--paper-dim);margin-bottom:12px}.basis{display:inline-block;font-family:var(--num);font-size:12.5px;color:var(--jade-bright);background:rgba(94,132,120,.1);border:1px solid rgba(94,132,120,.28);border-radius:3px;padding:2px 10px;overflow-wrap:anywhere;max-width:100%}.empty-state{padding:25px;color:var(--paper-dim);border:1px solid var(--line-soft)}
.signature{min-height:82vh;display:flex;flex-direction:column;align-items:center;justify-content:center;padding:90px 28px;overflow:hidden;border-top:1px solid var(--line-soft);border-bottom:1px solid var(--line-soft);background:radial-gradient(58% 56% at 50% 40%,rgba(63,107,134,.12),transparent 70%)}.sig-word{font-size:clamp(150px,38vw,360px);font-weight:900;line-height:1;color:var(--paper);text-shadow:0 0 42px rgba(94,147,179,.6),0 0 96px rgba(63,107,134,.34)}.sig-caption{text-align:center;max-width:590px;margin-top:18px}.sig-caption h2{font-size:clamp(27px,5vw,44px);color:var(--gold-bright);letter-spacing:.14em;font-weight:600}.sig-caption p{font-size:clamp(16px,2.4vw,18px);color:var(--paper-dim);line-height:2.05;margin-top:13px}
.limits{border:1px solid var(--gold-deep);padding:36px 32px;background:radial-gradient(600px 300px at 50% 0,rgba(217,115,51,.09),transparent),linear-gradient(160deg,rgba(28,25,34,.7),rgba(12,11,14,.4))}.limits h3{font-size:22px;color:var(--gold-bright);font-weight:600;margin-bottom:18px}.limits ul{padding-left:22px;color:var(--paper-dim);font-size:15px;line-height:2}.limits p{color:var(--paper-dim);font-size:14px;margin-top:18px}
footer{text-align:center;padding:60px 28px 84px;border-top:1px solid var(--line-soft);margin-top:40px;position:relative;z-index:1}footer .disc{font-size:13px;color:var(--paper-faint);max-width:620px;margin:0 auto 26px;line-height:1.95;font-style:italic}footer .sig-stamp{font-size:26px;color:var(--gold-deep);font-weight:900}footer .date{font-family:var(--num);font-size:13px;color:var(--paper-faint);letter-spacing:.2em;margin-top:8px;font-style:italic}
.intro,.note{font-size:16px;line-height:1.95;color:var(--paper-dim);margin-bottom:24px}.note{font-size:14px}.hero h1{font-size:clamp(30px,9vw,90px);letter-spacing:.02em;max-width:100%;overflow-wrap:anywhere;white-space:normal}.hero .verse{max-width:610px}.text-link{display:inline-block;color:var(--gold-bright);padding:10px 0;font-size:15px;min-height:44px}.subheading{font-size:23px;font-weight:600;color:var(--gold-bright);margin:34px 0 18px}.practice-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.signature{min-height:40vh}.sig-caption h2{font-size:clamp(24px,5vw,40px);text-wrap:balance}.faq details,.method{border-top:1px solid var(--line);padding:16px 0}.faq summary,.method summary{cursor:pointer;min-height:44px;color:var(--gold-bright);font-size:17px}.faq p{font-size:16px;color:var(--paper-dim);padding:8px 0 12px}.reading-index a.rules-link{min-height:44px;padding:8px 0;font-size:14px;color:#8f3028}.pair-top{flex-wrap:wrap}.pair-level{white-space:normal;overflow-wrap:anywhere}.focus-item>div,.reading-heading>div,.modifier-card>div,.sec-head>div{min-width:0}a:focus-visible,summary:focus-visible{outline:2px solid var(--gold-bright);outline-offset:3px}.reading-field p,.action-inset p,.self-check p,.focus-item p,.practice-step p,.combination p{font-size:16px;color:#c6bdab}.action-inset h4:not(:first-child){margin-top:16px}
@media(max-width:680px){.hero{padding:56px 18px 40px}.hero h1{font-size:clamp(26px,8vw,48px);white-space:normal;overflow-wrap:anywhere}.hero .pre{font-size:13px;letter-spacing:.25em}.hero .meta{font-size:14px;line-height:1.65;max-width:320px}.hero-links{margin-top:26px}.scroll-cue{position:static;writing-mode:horizontal-tb;letter-spacing:.15em;margin-top:24px;min-height:44px;display:flex;align-items:center}.scroll-cue:after{display:none}.reading-index{margin:54px 0 22px;padding:52px 18px 18px}.reading-index ol{grid-template-columns:repeat(2,minmax(0,1fr));}.reading-index li:last-child{grid-column:auto}.reading-index a{min-height:100px;padding:14px 12px}.overview-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.result-summary{padding:22px 18px}.result-summary-head{display:block}.result-summary-note{text-align:left;margin-top:18px}.result-sequence{grid-template-columns:repeat(2,minmax(0,1fr))}.result-distribution{grid-template-columns:repeat(2,minmax(0,1fr))}.pair-grid{grid-template-columns:1fr}.reading-chapter{padding:24px 18px}.reading-heading h3{font-size:22px}.combination-grid,.practice-grid{grid-template-columns:1fr}.focus-item,.combination,.practice-step{padding:20px 18px}.star-row{grid-template-columns:92px 1fr 25px;gap:9px}.star-name{font-size:15px;display:block}.star-name small{display:block;margin-top:2px}.modifier-card{grid-template-columns:56px 1fr;gap:14px}.modifier-digit{width:52px;height:52px;font-size:30px}.limits{padding:28px 22px}}@media(max-width:360px){.overview-grid{grid-template-columns:1fr}.reading-index ol{grid-template-columns:1fr}.reading-index li:last-child{grid-column:auto}}@media(prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
@media print{@page{size:A4;margin:12mm}body{background:#fff!important;color:#111!important;font-size:11pt}body *{color:#111!important;text-shadow:none!important}body:before,body:after,.scroll-cue,.hero-links,.reading-index{display:none!important}.wrap{max-width:none;padding:0}.hero{min-height:auto;padding:24mm 12mm}section{padding:12mm 0}.hero h1,.hero .verse,.sec-title,.sig-word,.sig-caption h2,.limits h3{color:#111!important;text-shadow:none!important}.pair-card,.stat,.limits,.heige-read,.reading-chapter,.focus-item,.combination,.practice-step,.modifier-card{background:#fff!important;box-shadow:none!important}.pair-grid,.overview-grid,.limits,.heige-read,.reading-chapters,.focus-list,.combination-grid,.practice-grid{border-color:#777!important}.heige-read span{color:#111!important;background:#fff!important;border:1px solid #777}.signature{min-height:auto;background:#fff!important}.pair-card,.stat,.modifier-card,.limits,.heige-read,.focus-item,.combination,.practice-step{break-inside:avoid}.reading-field,.self-check,.action-inset{break-inside:avoid}.reading-chapter{break-inside:auto}.faq details{break-inside:avoid}.practice-grid,.combination-grid{display:block}.practice-step{margin-bottom:16px}.action-inset,.self-check{background:#fff!important}.hero h1{font-size:42pt}footer{margin-top:0;padding:4mm 0;break-inside:avoid}}
"""
    html_report = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8"><meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="robots" content="noindex,nofollow"><title>手机号八星 · 结构报告 · {masked}</title>
<link rel="icon" href="data:"><link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@300;400;500;600;700;900&family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;1,400;1,500&display=swap" rel="stylesheet">
<style>{css}</style>
</head>
<body id="top"><div class="wrap">
<header class="hero"><div class="hero-frame"></div><div class="seal">数</div><div class="pre">手机号八星 · 结果报告</div><h1>{masked}</h1><div class="name">号码计算与解读报告</div><div class="meta">先看结果 · 再看解读 · 最后做行动</div><div class="verse">{result_line}<br><b>先看计算结果，再读白话解读。</b></div><div class="hero-links"><a href="#result">查看计算结果</a><a href="#overview">看重点解读</a><a href="#actions">怎么改善</a><a href="#reading-index">选择章节</a></div><a class="scroll-cue" href="#result" aria-label="查看手机号八星计算结果">先看结果</a></header>
<main id="report">
<section id="result" class="result-section" aria-labelledby="result-title" tabindex="-1"><div class="sec-head"><div class="sec-no">01</div><div><h2 class="sec-title" id="result-title">计算结果</h2><div class="sec-sub">CALCULATION RESULT</div></div></div><p class="lead">先看这串号码实际算出了什么，再往下看这些结果可以怎样翻成日常语言。</p><div class="result-summary"><div class="result-summary-head"><div><div class="result-summary-label">{kind} · 已脱敏</div><div class="result-summary-number">{masked}</div><p class="result-summary-meta">{result_line}</p></div><p class="result-summary-note"><strong>出现最多的主题：{dominant}</strong>{dominant_type} · {dominant_count} 组<br>这是当前规则的出现次数，不是人生评分。</p></div><div class="overview-grid result-stats"><div class="stat"><div class="stat-label">可识别组合</div><div class="stat-value">{recognized_pairs} / {total_pairs}</div><div class="stat-note">其余暂不单独归类</div></div><div class="stat"><div class="stat-label">最后有效组合</div><div class="stat-value">{tail_pair}</div><div class="stat-note">{tail_star}</div></div><div class="stat"><div class="stat-label">吉星组合</div><div class="stat-value">{auspicious}</div><div class="stat-note">按当前规则统计</div></div><div class="stat"><div class="stat-label">凶星组合</div><div class="stat-value">{inauspicious}</div><div class="stat-note">按当前规则统计</div></div></div><h3 class="result-subheading">相邻数字拆解</h3><p class="intro">下面这一排就是本次计算保留下来的结果。数字按相邻两位拆开，暂未归类的组合也保留在里面。</p><ol class="result-sequence" aria-label="相邻数字计算结果">{result_sequence}</ol><h3 class="result-subheading">八星分布</h3><div class="result-distribution">{result_distribution}</div><div class="heige-read"><span>先记住这三点</span><p>一，数字组合是计算结果。二，八星名称是当前规则给它们贴的标签。三，后面的白话解读只帮助你对照生活，不会把这些标签当成确定结论。</p></div></div></section>
<section id="overview" aria-labelledby="overview-title" tabindex="-1"><div class="sec-head"><div class="sec-no">02</div><div><h2 class="sec-title" id="overview-title">先看重点</h2><div class="sec-sub">START HERE</div></div></div><p class="lead">{overview}</p><p class="intro">下面先把整体分布翻成日常语言，再给出几个可以对照的生活场景。符合自己的内容才继续看，不符合的内容直接跳过。</p><div class="focus-list">{focus_cards}</div><div class="heige-read"><span>今天先做一件事</span><p>{first_step}</p><a class="text-link" href="#actions">直接看七天行动计划 ↗</a></div><div class="heige-read"><span>也看看可以借鉴的地方</span><p>{resources}</p></div></section>
<nav class="reading-index" id="reading-index" aria-label="报告阅读索引"><span class="reading-number">READING INDEX</span><h2>从你关心的地方读起</h2><p>先看已经算出的结果，再选择一项白话解读和行动。想知道数字怎么算出来的，可以继续看后面的数字拆分。</p><ol><li><a href="#result"><b>01</b><span>计算结果</span><small>THE RESULT</small></a></li><li><a href="#overview"><b>02</b><span>先看重点</span><small>START HERE</small></a></li><li><a href="#interpretation"><b>03</b><span>详细解读</span><small>UNDERSTAND</small></a></li><li><a href="#actions"><b>04</b><span>具体改善</span><small>TAKE ACTION</small></a></li><li><a href="#pairs"><b>05</b><span>数字怎么拆分</span><small>PAIR EVIDENCE</small></a></li><li><a href="#stars"><b>06</b><span>八星分布</span><small>DISTRIBUTION</small></a></li><li><a href="#modifiers"><b>07</b><span>0 / 5 提示</span><small>POSITION NOTES</small></a></li></ol><p class="reading-tip">这是按传统数字标签组织的自查读物。请以真实经历判断是否适用，不必对号入座。<a class="rules-link" href="#limits">查看规则与边界 ↗</a></p></nav>
<section id="interpretation" aria-labelledby="interpretation-title" tabindex="-1"><div class="sec-head"><div class="sec-no">03</div><div><h2 class="sec-title" id="interpretation-title">详细解读</h2><div class="sec-sub">UNDERSTAND THE THEMES</div></div></div><p class="lead">一个术语，一段生活场景，一个可以尝试的改变。</p><p class="intro">下面会把每个主题分别说清楚：它大概在提醒什么，生活里可能怎么出现，以及你可以怎样小范围试一试。</p><p class="note">{reading_basis}</p><div class="reading-chapters">{reading_cards}</div><div class="heige-read"><span>黑哥解读</span><p>符合自身经历的内容才值得继续探索。不要用星名给自己或他人定性；未出现某颗星，也不表示缺少相应能力。</p><a class="text-link" href="#actions">读完了，接下来怎么做 ↗</a></div></section>
<section id="actions" aria-labelledby="actions-title" tabindex="-1"><div class="sec-head"><div class="sec-no">04</div><div><h2 class="sec-title" id="actions-title">具体改善</h2><div class="sec-sub">action plan</div></div></div><p class="lead">改善不是把号码标签当成结论，而是用七天时间验证一个小行为。先做最小改变，再根据沟通、返工、承诺和压力记录决定是否保留。</p><h3 class="subheading">先选一项，试七天</h3><div class="practice-grid">{practice_cards}</div><h3 class="subheading">组合放在一起，怎么理解</h3><p class="intro">以下是多个主题同时出现时的编辑观察，不是流派定式，也不推算它们会互相抵消或放大。</p><div class="combination-grid">{combination_cards}</div><div class="heige-read"><span>黑哥解读</span><p>如果你只想做一件事，请从第一项行动开始。七天后没有变化、或者发现主题不符合自己，就停止这套练习，不需要为了迎合报告继续解释。</p></div><div class="faq"><h3 class="subheading">你可能还想知道</h3><details open><summary>需要换手机号吗？</summary><p>本报告没有提供“换号能够改善现实结果”的验证证据，不能仅凭星名建议你换号。现号码若使用方便，可以先试上面的具体做法。确实因为资费、使用便利或隐私等现实原因需要更换时，再核对联系通知、账号绑定和迁移成本。</p></details><details open><summary>识别率高，等于算得准吗？</summary><p>不等于。识别率只是在全部相邻组合中，有多少能查到八星标签。本次是 {recognized_pairs} / {total_pairs}，即 {recognized_rate}%；它不是预测准确率或人生评分。</p></details><details open><summary>出现凶星，或者缺少吉星，该怎么办？</summary><p>吉凶是传统分类名称。它不能证明人的好坏、能力或未来结果。先找自己真正想改善的一件小事，选择对应的练习；没有实际问题时，不需要为了补齐星组而做改变。</p></details><details open><summary>做了七天，怎么知道有没有用？</summary><p>比较第一天和第七天的真实记录，例如误会次数、返工次数、是否勉强承诺。练习没有帮助可以停止；行为变化不能反过来证明号码造成了原来的问题。</p></details></div></section>
<section id="pairs" aria-labelledby="pairs-title" tabindex="-1"><div class="sec-head"><div class="sec-no">05</div><div><h2 class="sec-title" id="pairs-title">数字怎么拆分</h2><div class="sec-sub">overlapping pairs</div></div></div><p class="lead">号码会按前后相邻的两位重叠拆开。长度为 n 的号码会得到 n−1 组。每组都保留原始数字、对应主题和行动提示，暂时没有对应主题的组合也会列出来。</p><div class="pair-grid">{pair_cards}</div><div class="heige-read"><span>黑哥解读</span><p>每张卡是号码中的一段依据。L1 到 L4 只是当前规则里的排序标记，不是强弱百分比；含 0、5 或暂未归类的组合不会被强行解释成好坏。</p></div></section>
<section id="stars" aria-labelledby="stars-title" tabindex="-1"><div class="sec-head"><div class="sec-no">06</div><div><h2 class="sec-title" id="stars-title">八星分布</h2><div class="sec-sub">star distribution</div></div></div><div class="star-list">{star_rows}</div><div class="heige-read"><span>黑哥解读</span><p>条形长度只表示当前号码里各类组合出现的次数。先找出现次数较多的主题，再回到主导星解读和行动建议；不要把红色条形理解成现实危险。</p></div></section>
<section id="modifiers" aria-labelledby="modifiers-title" tabindex="-1"><div class="sec-head"><div class="sec-no">07</div><div><h2 class="sec-title" id="modifiers-title">0 / 5 提示</h2><div class="sec-sub">position notes</div></div></div><p class="lead">当前规则不会把 0 和 5 单独算成八星，而是看看它们出现在数字中间或号码首尾时，是否需要多留意一个位置提示。这不是现实影响的倍数。</p><div>{modifier_cards}</div><div class="heige-read"><span>黑哥解读</span><p>这里的 0 和 5 更像连接符或位置标记。先看它连接的基础组合，再决定是否有对应的现实场景；如果没有，就保留为未验证信息。</p></div></section>
<section class="signature" aria-label="报告寄语"><div class="sig-caption"><h2>让改变，落在行动里。</h2><p>从一个真实场景开始，保留有帮助的做法。<br>理解自己，比记住一个星名更重要。</p></div></section>
<section id="limits" aria-labelledby="limits-title" tabindex="-1"><div class="sec-head"><div class="sec-no">08</div><div><h2 class="sec-title" id="limits-title">规则与边界</h2><div class="sec-sub">rules and limits</div></div></div><div class="limits"><h3>计算口径与解读来源</h3><p>{profile} · 引擎 v{version} · {kind} · {digits_count} 位输入。{input_policy}</p><details open class="method"><summary>为什么优先读这些主题？</summary><p>{main_explanation}</p><p>{tail_explanation}</p><p>L1、L2、L3、L4 的排序权重依次为 4、3、2、1；伏位使用权重 1，但没有 L 等级。这些数字不测量现实能量。</p></details><ul>{limitations}</ul><p>解读文案版本：{reading_version}。{reading_basis}</p><p>号码标题已遮蔽中间位，但详细数字对及顺序可能用于还原号码，因此这不是匿名报告；公开分享前请移除详细依据。若进行八字交叉分析，应先独立运行八字排盘，再把「号码结构层」与「八字交叉层」分开说明。</p></div><div class="heige-read"><span>黑哥解读</span><p>规则版本决定了数字对如何归类，解读文案版本决定了怎么把术语翻成自查问题。换一个流派或 profile，结果可能不同；这份报告的价值在于口径固定、过程可复盘，而不是替你对人生做确定结论。</p></div></section>
</main></div><footer><p class="disc">本报告是传统文化研究与自我认知参考，非预言或保证，不承诺改运消灾。健康、财富、婚姻、事故和投资等现实问题，请结合事实与专业意见理性判断。</p><div class="sig-stamp">手机号八星 · 结构报告</div><div class="date">{profile} · 引擎 v{version}</div></footer>
</body></html>""".format(
        css=css,
        masked=masked,
        profile=_esc(result.get("rules_profile", RULE_PROFILE)),
        version=_esc(result.get("engine_version", __version__)),
        kind=_esc({"mobile": "手机号", "plate": "车牌", "address": "门牌", "general": "通用数字"}.get(input_data.get("kind"), "通用数字")),
        input_policy="已按设置排除固定首位 1。" if input_data.get("exclude_leading_one") else "本次保留输入的首位数字。",
        digits_count=_esc(input_data.get("digits_count", "")),
        result_line=_esc(result_line),
        dominant=dominant,
        dominant_type=_esc(dominant_type),
        dominant_count=main["count"] if main else 0,
        recognized_pairs=recognized_pairs,
        total_pairs=total_pairs,
        recognized_rate=recognized_rate,
        tail_pair=tail_pair,
        tail_star=tail_star,
        auspicious=_esc(summary.get("auspicious_count", 0)),
        neutral=_esc(summary.get("neutral_count", 0)),
        inauspicious=_esc(summary.get("inauspicious_count", 0)),
        pair_cards=_pair_cards(result, reading),
        star_rows=_star_rows(result),
        modifier_cards=_modifier_cards(result),
        result_sequence=_result_sequence(result),
        result_distribution=_result_distribution(result),
        limitations=limitations,
        reading_headline=_esc(reading["main"]["headline"] if reading["main"] else reading["headline"]),
        first_step=_esc(reading["first_step"]),
        overview=_esc(reading["overview"]),
        focus_cards=_focus_cards(reading),
        reading_cards=_reading_cards(reading),
        reading_basis=_esc(reading["basis"]),
        main_explanation=_esc(main_explanation),
        tail_explanation=_esc(tail_explanation),
        resources=_esc(resources),
        combination_cards=_combination_cards(reading),
        practice_cards=_practice_cards(reading),
        reading_version=_esc(reading["version"]),
    )
    return html_report


def write_phone_energy_html(result: Dict[str, Any], output_path: Any) -> Path:
    """将八星结果写入 HTML 文件，并返回绝对路径。"""
    path = Path(output_path).expanduser().resolve()
    rendered = render_phone_energy_html(result)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(rendered, encoding="utf-8")
    return path


def main(argv: Optional[List[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        result = analyze_phone_number(
            args.number,
            number_kind=args.kind,
            profile=args.profile,
            exclude_leading_one=args.exclude_leading_one,
        )
    except (PhoneEnergyError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    if args.html is not None:
        output_path = Path(args.html) if args.html else _default_html_path(result)
        try:
            report_path = write_phone_energy_html(result, output_path)
        except (OSError, PhoneEnergyError) as exc:
            print("HTML 报告生成失败：{}".format(exc), file=sys.stderr)
            return 2
        print("HTML 报告已生成：{}".format(report_path))
        return 0
    if args.as_json:
        indent = 2 if args.pretty else None
        print(json.dumps(result, ensure_ascii=False, indent=indent, sort_keys=bool(args.pretty)))
    else:
        _print_text(result)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
