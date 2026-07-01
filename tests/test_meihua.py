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

import os
import sys
import unittest

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


if __name__ == "__main__":
    unittest.main(verbosity=2)
