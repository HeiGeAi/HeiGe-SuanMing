#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
meihua.py 回归测试 · HeiGe-SuanMing / bazi-mingli skill

以梅花易数固定定式（先天八卦数、六十四卦名、互卦取 234/345 爻、变卦动爻互换、
体用取动者为用）为基准真值，并以《梅花易数》经典「观梅占」为黄金用例校验起卦全链路。

运行：
  python3 tests/test_meihua.py
  python3 -m unittest discover -s tests   # 连同 test_paipan 一起跑
"""

import json
import os
import sys
import unittest
from unittest.mock import patch

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)

import meihua  # noqa: E402


class TestGuanMei(unittest.TestCase):
    """经典观梅占黄金用例：辰年十二月十七日申时 → 泽火革，初爻动。"""

    def setUp(self):
        # 年支辰=5、月12、日17、时支申=9
        self.c = meihua.qigua_by_time_numbers(5, 12, 17, 9)

    def test_ben_gua(self):
        self.assertEqual(self.c["本卦"]["名"], "泽火革")

    def test_hu_gua(self):
        self.assertEqual(self.c["互卦"]["名"], "天风姤")

    def test_bian_gua(self):
        self.assertEqual(self.c["变卦"]["名"], "泽山咸")

    def test_dong_yao(self):
        self.assertEqual(self.c["起卦"]["动爻"], 1)

    def test_ti_yong(self):
        # 动爻初爻在下卦 → 用离(火)、体兑(金)
        self.assertEqual(self.c["体用"]["体卦"], "兑")
        self.assertEqual(self.c["体用"]["用卦"], "离")

    def test_yong_ke_ti(self):
        # 用离火 克 体兑金
        self.assertEqual(self.c["体用"]["用对体"], "克")

    def test_bian_saves_ti(self):
        # 变卦下艮土 生 体兑金（终局有救，对应经典「有救不致大凶」）
        self.assertIn("生 体", self.c["生克"]["变卦对体"])


class TestGua64Table(unittest.TestCase):
    """六十四卦名表抽检（上卦, 下卦）→ 卦名。"""

    def test_known_gua(self):
        cases = {(1, 1): "乾为天", (8, 8): "坤为地", (6, 3): "水火既济",
                 (3, 6): "火水未济", (1, 8): "天地否", (8, 1): "地天泰",
                 (7, 6): "山水蒙", (6, 4): "水雷屯", (4, 5): "雷风恒"}
        for (u, d), name in cases.items():
            self.assertEqual(meihua.build_gua(u, d, 1)["本卦"]["名"], name,
                             f"上{meihua.XIANTIAN[u]}下{meihua.XIANTIAN[d]} 应为 {name}")

    def test_table_complete_64(self):
        self.assertEqual(len(meihua.GUA64), 64)


class TestHuBian(unittest.TestCase):
    """互卦取 234/345 爻、变卦动爻互换的正确性。"""

    def test_hu_from_yao(self):
        # 泽火革 yao=离[1,0,1]+兑[1,1,0]=[1,0,1,1,1,0]，下互234=[0,1,1]巽、上互345=[1,1,1]乾 → 天风姤
        c = meihua.build_gua(2, 3, 1)
        self.assertEqual(c["互卦"]["下"], "巽")
        self.assertEqual(c["互卦"]["上"], "乾")

    def test_bian_flips_only_dong(self):
        # 乾为天 第3爻动 → 下卦乾[1,1,1] 第3爻变 → [1,1,0]=兑 → 变卦上乾下兑=天泽履
        c = meihua.build_gua(1, 1, 3)
        self.assertEqual(c["变卦"]["名"], "天泽履")

    def test_dong_upper_ti_yong(self):
        # 动爻在上卦(4-6)→上卦为用、下卦为体
        c = meihua.build_gua(2, 3, 5)
        self.assertEqual(c["体用"]["用卦"], "兑")
        self.assertEqual(c["体用"]["体卦"], "离")


class TestCasting(unittest.TestCase):
    """起卦法与取余规则。"""

    def test_mod_wrap(self):
        self.assertEqual(meihua._mod(8, 8), 8)
        self.assertEqual(meihua._mod(16, 8), 8)
        self.assertEqual(meihua._mod(6, 6), 6)
        self.assertEqual(meihua._mod(12, 6), 6)
        self.assertEqual(meihua._mod(3, 8), 3)

    def test_numbers_casting(self):
        # 上34%8=2兑，下43%8=3离 → 泽火革；动爻(34+43)%6=77%6=5
        c = meihua.qigua_by_numbers(34, 43)
        self.assertEqual(c["本卦"]["名"], "泽火革")
        self.assertEqual(c["起卦"]["动爻"], 5)

    def test_time_numbers_matches_gua(self):
        a = meihua.qigua_by_time_numbers(5, 12, 17, 9)
        b = meihua.build_gua(2, 3, 1)
        self.assertEqual(a["本卦"]["名"], b["本卦"]["名"])
        self.assertEqual(a["变卦"]["名"], b["变卦"]["名"])


class TestRelation(unittest.TestCase):
    """五行生克关系（from 对 to）。"""

    def test_relations(self):
        self.assertEqual(meihua._relation("火", "金"), "克")     # 火克金
        self.assertEqual(meihua._relation("土", "金"), "生")     # 土生金
        self.assertEqual(meihua._relation("金", "金"), "比和")
        self.assertEqual(meihua._relation("金", "火"), "被克")   # 火克金→金被克
        self.assertEqual(meihua._relation("金", "土"), "被生")   # 土生金→金被生


class TestValidation(unittest.TestCase):
    """非法输入。"""

    def test_bad_gua_num(self):
        with self.assertRaises(ValueError):
            meihua.build_gua(9, 3, 1)

    def test_bad_dong(self):
        with self.assertRaises(ValueError):
            meihua.build_gua(2, 3, 7)


class TestNoScoreNoVerdict(unittest.TestCase):
    """断语提示须趋势化，不打分、不铁口。"""

    def test_hint_trend_words(self):
        hint = meihua.build_gua(2, 3, 1)["断语提示"]
        self.assertTrue(any(w in hint for w in ("倾向", "需注意", "参考")))
        # 剔除合规免责声明本身（「非铁口」「不打分」），再查是否残留铁口/打分类措辞
        clean = hint.replace("非铁口", "").replace("不打分", "")
        for bad in ("必成", "必败", "评分", "铁口", "打分"):
            self.assertNotIn(bad, clean)


class TestCli(unittest.TestCase):
    """CLI 冒烟。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "meihua.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_gua_cli(self):
        r = self._run("--gua", "2", "3", "1", "--query", "测试")
        self.assertEqual(r.returncode, 0)
        self.assertIn("泽火革", r.stdout)

    def test_numbers_cli(self):
        r = self._run("--numbers", "34", "43")
        self.assertEqual(r.returncode, 0)
        self.assertIn("泽火革", r.stdout)

    def test_time_cli(self):
        r = self._run("--time", "2020", "3", "15", "14", "30")
        self.assertEqual(r.returncode, 0)
        self.assertIn("本卦", r.stdout)


# ============================================================
# v1.0.1 审计修复回归（输入校验 / numbers 下限 / 晚子时口径）
# ============================================================
class TestInputValidationV101(unittest.TestCase):
    """M1/M2/M3/L2：非法输入干净拦截，不裸 traceback、不静默错果。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "meihua.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_numbers_below_one_rejected(self):
        with self.assertRaises(ValueError):
            meihua.qigua_by_numbers(0, 5)
        with self.assertRaises(ValueError):
            meihua.qigua_by_numbers(-3, 5)

    def test_cli_hour_25(self):
        r = self._run("--time", "2020", "3", "15", "25", "0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("时0-23", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_cli_day_32_rejected(self):
        # 上游 lunar_python 校验有笔误放行日32，引擎侧必须自己拦
        r = self._run("--time", "2020", "3", "32", "14", "0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("日期非法", r.stdout + r.stderr)

    def test_cli_year_gate(self):
        r = self._run("--time", "100", "6", "15", "14", "0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stdout + r.stderr)

    def test_cli_lunar_short_month(self):
        r = self._run("--time", "2020", "6", "30", "14", "0", "--lunar")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)


class TestZiSectV101(unittest.TestCase):
    """M4：晚子时取日口径可选，默认不换日。"""

    def test_default_no_advance(self):
        c = meihua.qigua_by_time(2026, 7, 4, 23, 30)
        self.assertIn("20日", c["起卦法"].replace(" ", ""))

    def test_sect1_advances_day(self):
        c = meihua.qigua_by_time(2026, 7, 4, 23, 30, zi_sect=1)
        self.assertIn("21日", c["起卦法"].replace(" ", ""))
        self.assertIn("晚子归次日", c["起卦法"])

    def test_non_zi_hour_unaffected(self):
        a = meihua.qigua_by_time(2026, 7, 4, 14, 30)
        b = meihua.qigua_by_time(2026, 7, 4, 14, 30, zi_sect=1)
        self.assertEqual(a["本卦"]["名"], b["本卦"]["名"])


class TestAuditFixesV110(unittest.TestCase):
    """v1.1.0：农历晚子、闰月身份、核心异常与 JSON 所占。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "meihua.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_lunar_sect1_advances_to_next_lunar_day(self):
        actual = meihua.qigua_by_time(2026, 5, 20, 23, 30, lunar=True, zi_sect=1)
        expected = meihua.qigua_by_time(2026, 5, 21, 23, 30, lunar=True, zi_sect=2)
        self.assertEqual(actual["本卦"]["名"], expected["本卦"]["名"])
        self.assertEqual(actual["起卦"]["动爻"], expected["起卦"]["动爻"])
        self.assertIn("晚子归次日", actual["起卦法"])
        self.assertIn("21日", actual["起卦法"].replace(" ", ""))

    def test_lunar_sect1_crosses_month_via_calendar(self):
        actual = meihua.qigua_by_time(2026, 5, 29, 23, 30, lunar=True, zi_sect=1)
        self.assertIn("6月1日", actual["起卦法"].replace(" ", ""))

    def test_leap_month_marker_is_preserved(self):
        chart = meihua.qigua_by_time(2025, -6, 1, 12, 0, lunar=True)
        self.assertIn("闰6月", chart["起卦法"].replace(" ", ""))

    def test_invalid_zi_sect_is_value_error(self):
        with self.assertRaises(ValueError):
            meihua.qigua_by_time(2026, 5, 20, 23, 30, lunar=True, zi_sect=3)

    def test_core_invalid_date_is_value_error(self):
        with self.assertRaises(ValueError):
            meihua.qigua_by_time(2026, 2, 30, 12, 0)

    def test_missing_dependency_is_runtime_error(self):
        with patch.dict(sys.modules, {"lunar_python": None}):
            with self.assertRaises(RuntimeError):
                meihua.qigua_by_time(2026, 5, 20, 12, 0)

    def test_json_keeps_query(self):
        r = self._run("--numbers", "34", "43", "--query", "问近期求职", "--json")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout)["query"], "问近期求职")


class TestAuditRemediation(unittest.TestCase):
    """审计回归：农历月份、转换后年份闸门与 CLI 参数语义。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "meihua.py")
        return subprocess.run(
            [sys.executable, script, *extra], capture_output=True, text=True, check=False
        )

    def test_lunar_short_month_has_chinese_error(self):
        with self.assertRaises(ValueError) as cm:
            meihua.qigua_by_time(1990, 4, 30, 12, 0, lunar=True)
        message = str(cm.exception)
        self.assertIn("小月，只有 29 天", message)
        self.assertNotIn("only", message.lower())

    def test_nonexistent_leap_month_has_chinese_error(self):
        with self.assertRaises(ValueError) as cm:
            meihua.qigua_by_time(2023, -3, 1, 12, 0, lunar=True)
        message = str(cm.exception)
        self.assertIn("没有闰3月", message)
        self.assertNotIn("wrong lunar year", message.lower())

    def test_lunar_conversion_cannot_cross_supported_solar_year(self):
        with self.assertRaisesRegex(ValueError, "有效公历年份超出支持范围"):
            meihua.qigua_by_time(2200, 12, 29, 12, 0, lunar=True)

    def test_late_zi_advance_cannot_cross_supported_solar_year(self):
        with self.assertRaisesRegex(ValueError, "有效公历年份超出支持范围"):
            meihua.qigua_by_time(2200, 12, 31, 23, 30, zi_sect=1)

    def test_lunar_flag_is_rejected_outside_time_mode(self):
        for args in (("--numbers", "34", "43"), ("--gua", "2", "3", "1")):
            with self.subTest(args=args):
                r = self._run(*args, "--lunar")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("仅能与 --time 同用", r.stdout + r.stderr)

    def test_explicit_zi_sect_is_rejected_outside_time_mode(self):
        for args in (("--numbers", "34", "43"), ("--gua", "2", "3", "1")):
            with self.subTest(args=args):
                r = self._run(*args, "--zi-sect", "1")
                self.assertNotEqual(r.returncode, 0)
                self.assertIn("仅能与 --time 同用", r.stdout + r.stderr)

    def test_time_cli_default_zi_sect_remains_two(self):
        default = self._run("--time", "2026", "7", "4", "23", "30", "--json")
        explicit = self._run("--time", "2026", "7", "4", "23", "30", "--zi-sect", "2", "--json")
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertEqual(explicit.returncode, 0, explicit.stderr)
        self.assertEqual(json.loads(default.stdout), json.loads(explicit.stdout))


class TestGregorianRangeCalendarEquivalence(unittest.TestCase):
    """农历年可以早一年，实际公历日期和晚子推进均须守住边界。"""

    def test_supported_boundary_dates_match_lunar_input(self):
        cases = [((1600, 1, 1), (1599, 11, 16)),
                 ((1600, 1, 16), (1599, 12, 1)),
                 ((2200, 12, 31), (2200, 11, 25))]
        for solar, lunar in cases:
            for hour, sect in ((12, 2), (23, 2), (12, 1)):
                with self.subTest(solar=solar, hour=hour, sect=sect):
                    expected = meihua.qigua_by_time(*solar, hour, 30, zi_sect=sect)
                    actual = meihua.qigua_by_time(*lunar, hour, 30, lunar=True, zi_sect=sect)
                    self.assertEqual(actual, expected)

    def test_lower_boundary_late_zi_matches_solar(self):
        actual = meihua.qigua_by_time(1599, 11, 16, 23, 30, lunar=True, zi_sect=1)
        expected = meihua.qigua_by_time(1600, 1, 1, 23, 30, zi_sect=1)
        self.assertEqual(actual, expected)
        self.assertIn("17日", actual["起卦法"].replace(" ", ""))

    def test_outside_solar_dates_rejected_in_both_calendars(self):
        cases = [((1599, 12, 31), (1599, 11, 15)),
                 ((2201, 1, 1), (2200, 11, 26))]
        for solar, lunar in cases:
            for ymd, is_lunar in ((solar, False), (lunar, True)):
                for hour, sect in ((12, 2), (23, 1)):
                    with self.subTest(ymd=ymd, lunar=is_lunar, sect=sect):
                        with self.assertRaisesRegex(ValueError, "公历.*(1600|2200)|支持.*1600"):
                            meihua.qigua_by_time(*ymd, hour, 30, lunar=is_lunar, zi_sect=sect)

    def test_upper_boundary_late_zi_rejected_in_both_calendars(self):
        for ymd, is_lunar in (((2200, 12, 31), False), ((2200, 11, 25), True)):
            with self.subTest(lunar=is_lunar):
                with self.assertRaisesRegex(ValueError, "有效公历年份超出支持范围"):
                    meihua.qigua_by_time(*ymd, 23, 30, lunar=is_lunar, zi_sect=1)

    def test_lower_boundary_lunar_cli_succeeds(self):
        import subprocess
        result = subprocess.run(
            [sys.executable, os.path.join(_SCRIPTS, "meihua.py"),
             "--time", "1599", "12", "1", "12", "0", "--lunar", "--json"],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("本卦", json.loads(result.stdout))


if __name__ == "__main__":
    unittest.main(verbosity=2)
