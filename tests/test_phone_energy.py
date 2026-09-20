import json
import copy
import io
import subprocess
import sys
import unittest
from contextlib import redirect_stderr
from unittest.mock import patch
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "phone_energy.py"

sys.path.insert(0, str(ROOT / "scripts"))
try:
    from phone_energy import (  # noqa: E402
        RULE_PROFILE,
        analyze_phone_number,
        build_phone_energy_reading,
        main,
        normalize_number,
        render_phone_energy_html,
    )
    MODULE_AVAILABLE = True
except ModuleNotFoundError:
    MODULE_AVAILABLE = False
    RULE_PROFILE = None
    analyze_phone_number = None
    build_phone_energy_reading = None
    normalize_number = None
    render_phone_energy_html = None


class TestPhoneEnergyEngine(unittest.TestCase):
    def test_engine_module_exists(self):
        self.assertTrue(MODULE_AVAILABLE, "scripts/phone_energy.py must exist")

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_normalizes_separators_and_masks_original_number(self):
        self.assertEqual("13812345678", normalize_number("138-123 45678"))
        result = analyze_phone_number("138-123 45678")
        self.assertEqual("138****5678", result["input"]["masked"])
        self.assertEqual(11, result["input"]["digits_count"])
        self.assertNotIn("13812345678", json.dumps(result, ensure_ascii=False))

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_rejects_input_without_digits(self):
        with self.assertRaises(ValueError):
            normalize_number("手机号")

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_maps_adjacent_pairs_and_preserves_unclassified_pairs(self):
        result = analyze_phone_number("1319")
        self.assertEqual(RULE_PROFILE, result["rules_profile"])
        self.assertEqual(["13", "31", "19"], [item["digits"] for item in result["pairs"]])
        self.assertEqual(["天医", "天医", "延年"], [item["star"] for item in result["pairs"]])
        self.assertEqual(["L1", "L1", "L1"], [item["level"] for item in result["pairs"]])
        self.assertEqual(3, result["summary"]["recognized_pairs"])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_counts_stars_and_uses_strength_for_dominant_star(self):
        result = analyze_phone_number("131188")
        self.assertEqual({"天医": 2, "五鬼": 1, "伏位": 2}, result["summary"]["star_counts"])
        self.assertEqual("天医", result["summary"]["dominant_star"])
        self.assertEqual("88", result["summary"]["tail_pair"])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_zero_and_five_are_modifiers_and_do_not_become_stars(self):
        result = analyze_phone_number("103153")
        self.assertEqual(["10", "03", "31", "15", "53"], [item["digits"] for item in result["pairs"]])
        self.assertTrue(all(item["star"] is None for item in result["pairs"] if "0" in item["digits"] or "5" in item["digits"]))
        modifiers = {(item["source"], item["effect"], item["base_pair"]) for item in result["modifiers"]}
        self.assertIn(("103", "hidden", "13"), modifiers)
        self.assertIn(("153", "amplified", "13"), modifiers)
        self.assertEqual(1, result["summary"]["recognized_pairs"])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_edge_zero_or_five_is_reported_as_fu_wei_modifier(self):
        result = analyze_phone_number("0130")
        edge = [item for item in result["modifiers"] if item["effect"] == "edge_fu_wei"]
        self.assertEqual(2, len(edge))
        self.assertTrue(all(item["star"] == "伏位" for item in edge))

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_single_edge_modifier_does_not_require_a_neighbor(self):
        result = analyze_phone_number("0", number_kind="address")
        self.assertEqual([], result["pairs"])
        self.assertEqual(1, len(result["modifiers"]))
        self.assertEqual("伏位", result["modifiers"][0]["star"])
        self.assertEqual("00", result["modifiers"][0]["base_pair"])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_short_numbers_are_masked_without_leaking_the_input(self):
        result = analyze_phone_number("1234567", number_kind="general")
        self.assertEqual("12***67", result["input"]["masked"])
        self.assertNotIn("1234567", json.dumps(result, ensure_ascii=False))

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_analysis_digits_also_masks_five_or_six_digit_inputs(self):
        result = analyze_phone_number("123456", number_kind="general")
        self.assertEqual("12**56", result["input"]["analysis_digits"])
        self.assertNotIn("123456", json.dumps(result, ensure_ascii=False))

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_mobile_leading_one_can_be_explicitly_excluded(self):
        full = analyze_phone_number("1131", number_kind="mobile")
        excluded = analyze_phone_number("1131", number_kind="mobile", exclude_leading_one=True)
        self.assertEqual("1131", full["input"]["analysis_digits"])
        self.assertEqual("131", excluded["input"]["analysis_digits"])
        self.assertEqual(["13", "31"], [item["digits"] for item in excluded["pairs"]])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_invalid_profile_is_rejected(self):
        with self.assertRaises(ValueError):
            analyze_phone_number("1319", profile="unknown")

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_cli_json_is_deterministic_and_reports_version(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "1319", "--json"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        )
        result = json.loads(completed.stdout)
        self.assertEqual("phone_energy", result["engine"])
        self.assertEqual("0.2.0", result["engine_version"])
        self.assertEqual("eight_star_v1", result["rules_profile"])
        self.assertEqual("1319", result["input"]["analysis_digits"])

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_cli_rejects_invalid_input_with_nonzero_exit(self):
        completed = subprocess.run(
            [sys.executable, str(SCRIPT), "abc", "--json"],
            cwd=ROOT,
            capture_output=True,
            text=True,
        )
        self.assertNotEqual(0, completed.returncode)
        self.assertIn("至少需要一个数字", completed.stderr)

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_html_report_uses_project_visual_contract_and_masks_number(self):
        result = analyze_phone_number("16654633612")
        html = render_phone_energy_html(result)
        self.assertIn("手机号八星 · 结构报告", html)
        self.assertIn("166****3612", html)
        self.assertNotIn("16654633612", html)
        self.assertIn("#bb4232", html)
        self.assertIn("#c9a45c", html)
        self.assertIn("黑哥解读", html)
        self.assertIn("reading-index", html)
        self.assertIn("选择章节", html)
        self.assertIn("计算结果", html)
        self.assertIn("相邻数字拆解", html)
        self.assertIn("详细解读", html)
        self.assertIn("简单说", html)
        self.assertIn("这个号码按当前规则识别出", html)
        self.assertIn("数字怎么拆分", html)
        self.assertIn("L1 · 较高权重", html)
        self.assertIn("问问自己", html)
        self.assertIn("具体改善", html)
        self.assertIn("七天", html)
        self.assertIn("如果符合自己，可以这样做", html)
        self.assertIn("沟通句式", html)
        self.assertIn("@media print", html)
        self.assertNotIn("<script", html.lower())

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_reading_library_binds_evidence_to_actionable_guidance(self):
        result = analyze_phone_number("16654633612")
        original = copy.deepcopy(result)
        reading = build_phone_energy_reading(result)
        self.assertEqual("eight_star_reading_v1", reading["version"])
        self.assertEqual("六煞", reading["main"]["star"])
        self.assertEqual(["六煞", "五鬼", "绝命"], [item["star"] for item in reading["focus"]])
        self.assertEqual(4, len(reading["practice"]))
        self.assertTrue(all(item["metric"] for item in reading["present"]))
        self.assertEqual(["16", "61"], [item["digits"] for item in reading["main"]["pairs"]])
        self.assertEqual(8, reading["main"]["weight"])
        self.assertIn("按当前规则识别出", reading["overview"])
        self.assertIn("用事实、感受、请求三句话", reading["overview"])
        self.assertEqual(result, original)
        self.assertEqual(reading, build_phone_energy_reading(result))

    def test_each_star_has_its_own_reading_and_action(self):
        for number, star in (("13", "天医"), ("14", "生气"), ("19", "延年"), ("11", "伏位"),
                             ("12", "绝命"), ("17", "祸害"), ("18", "五鬼"), ("16", "六煞")):
            with self.subTest(star=star):
                result = analyze_phone_number(number, number_kind="general")
                reading = build_phone_energy_reading(result)
                self.assertEqual([star], [item["star"] for item in reading["present"]])
                self.assertEqual([star], [item["star"] for item in reading["focus"]])
                self.assertEqual([], reading["bridges"])
                self.assertEqual(reading["main"]["action"], reading["practice"][1]["action"])
                html = render_phone_energy_html(result)
                self.assertIn(reading["main"]["script"], html)
                if star == "伏位":
                    self.assertIn("伏位不分级", html)
                    self.assertNotIn('class="pair-level">不独立成星', html)

    def test_unclassified_inputs_do_not_invent_personal_readings(self):
        for number in ("1", "0", "5", "050", "103"):
            with self.subTest(number=number):
                result = analyze_phone_number(number, number_kind="general")
                reading = build_phone_energy_reading(result)
                self.assertIsNone(reading["main"])
                self.assertIsNone(reading["tail"])
                self.assertEqual([], reading["present"])
                html = render_phone_energy_html(result)
                self.assertIn("无法生成主导主题或个性解读", html)
                self.assertNotIn('class="reading-chapter"', html)
                self.assertEqual(4, html.count('class="practice-step"'))

    def test_tail_and_modifiers_preserve_calculation_boundaries(self):
        result = analyze_phone_number("13150", number_kind="general")
        reading = build_phone_energy_reading(result)
        self.assertEqual("31", reading["tail"]["digits"])
        self.assertEqual(2, reading["main"]["count"])
        html = render_phone_energy_html(result)
        self.assertIn("它后面还有 2 组未分类组合", html)
        self.assertIn("不是号码字面上的最后两位", html)
        for number, label in (("103", "隐藏"), ("153", "放大"), ("013", "首尾延续")):
            with self.subTest(number=number):
                self.assertIn(label, render_phone_energy_html(analyze_phone_number(number)))

    def test_report_prioritizes_understanding_and_actions_before_evidence(self):
        html = render_phone_energy_html(analyze_phone_number("1319"))
        positions = [html.index('<section id="{}"'.format(name)) for name in
                     ("overview", "interpretation", "actions", "pairs", "stars", "modifiers", "limits")]
        self.assertEqual(sorted(positions), positions)
        self.assertLess(html.index('<section id="result"'), html.index('<section id="overview"'))
        self.assertLess(html.index('<section id="overview"'), html.index('<nav class="reading-index"'))
        for text in ("需要换手机号吗", "它不是预测准确率", "未出现某颗星", "不是匿名报告"):
            self.assertIn(text, html)

    def test_reading_fields_are_escaped_in_html(self):
        result = analyze_phone_number("1319")
        result["input"]["masked"] = '<img src=x onerror="alert(1)">'
        result["pairs"][0]["digits"] = "<script>alert(1)</script>"
        html = render_phone_energy_html(result)
        self.assertNotIn("<script>", html)
        self.assertNotIn("<img src=x", html)
        self.assertIn("&lt;script&gt;", html)

    def test_reading_version_mismatch_and_missing_library_fail_cleanly(self):
        result = analyze_phone_number("1319")
        result["rules_profile"] = "unknown"
        with self.assertRaisesRegex(ValueError, "不匹配"):
            build_phone_energy_reading(result)
        with patch("phone_energy.Path.read_text", side_effect=FileNotFoundError()):
            with self.assertRaisesRegex(ValueError, "解读文案不可读取"):
                build_phone_energy_reading(analyze_phone_number.__globals__.get("unused", result))
        from phone_energy import PhoneEnergyError
        stderr = io.StringIO()
        with patch("phone_energy.write_phone_energy_html", side_effect=PhoneEnergyError("文案缺失")), redirect_stderr(stderr):
            self.assertEqual(2, main(["1319", "--html", "unused.html"]))
        self.assertIn("文案缺失", stderr.getvalue())
        self.assertNotIn("Traceback", stderr.getvalue())

    @unittest.skipUnless(MODULE_AVAILABLE, "phone energy engine not implemented yet")
    def test_cli_can_write_html_report_to_requested_path(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "phone-report.html"
            completed = subprocess.run(
                [sys.executable, str(SCRIPT), "16654633612", "--html", str(output)],
                cwd=ROOT,
                check=True,
                capture_output=True,
                text=True,
            )
            self.assertTrue(output.exists())
            self.assertIn(str(output), completed.stdout)
            self.assertIn("166****3612", output.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
