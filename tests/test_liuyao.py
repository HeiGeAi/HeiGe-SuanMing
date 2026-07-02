#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
liuyao.py 回归测试 · HeiGe-SuanMing / bazi-mingli skill

以京房纳甲筮法固定定式为基准真值：纳甲干支（乾纳甲壬等）、八宫归属与世应
（纯卦世六、一至五世、游魂四、归魂三）、六亲以宫五行配、六神按日干起。

运行：
  python3 tests/test_liuyao.py
  python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)

import liuyao  # noqa: E402
from meihua import TRIGRAM_YAO  # noqa: E402


def pan_of(up, down, marks=None):
    """按上/下经卦名装静卦（或给定摇卦标记）。"""
    if marks is None:
        yao = TRIGRAM_YAO[down] + TRIGRAM_YAO[up]
        marks = [7 if b else 8 for b in yao]
    return liuyao.build_pan(marks)


class TestNaJia(unittest.TestCase):
    """纳甲干支定式。"""

    def test_qian_najia(self):
        p = liuyao.build_pan([7] * 6)
        self.assertEqual([l["干支"] for l in p["爻"]],
                         ["甲子", "甲寅", "甲辰", "壬午", "壬申", "壬戌"])

    def test_kun_najia(self):
        p = liuyao.build_pan([8] * 6)
        self.assertEqual([l["干支"] for l in p["爻"]],
                         ["乙未", "乙巳", "乙卯", "癸丑", "癸亥", "癸酉"])

    def test_kan_inner(self):
        # 坎为水：内卦戊寅、戊辰、戊午
        p = pan_of("坎", "坎")
        self.assertEqual([l["干支"] for l in p["爻"][:3]], ["戊寅", "戊辰", "戊午"])

    def test_dui_inner(self):
        # 兑为泽：初爻丁巳
        p = pan_of("兑", "兑")
        self.assertEqual(p["爻"][0]["干支"], "丁巳")


class TestGongShiYing(unittest.TestCase):
    """八宫归属与世应位。"""

    def test_pure_gua(self):
        p = liuyao.build_pan([7] * 6)
        self.assertIn("乾宫", p["本卦"]["宫"])
        self.assertEqual((p["本卦"]["世"], p["本卦"]["应"]), (6, 3))

    def test_yi_shi(self):
        # 天风姤 = 乾宫一世，世1应4
        p = pan_of("乾", "巽")
        self.assertIn("乾宫", p["本卦"]["宫"])
        self.assertEqual((p["本卦"]["世"], p["本卦"]["应"]), (1, 4))

    def test_san_shi(self):
        # 地天泰 = 坤宫三世，世3应6
        p = pan_of("坤", "乾")
        self.assertIn("坤宫", p["本卦"]["宫"])
        self.assertEqual((p["本卦"]["世"], p["本卦"]["应"]), (3, 6))

    def test_youhun(self):
        # 地火明夷 = 坎宫游魂，世4应1
        p = pan_of("坤", "离")
        self.assertIn("坎宫", p["本卦"]["宫"])
        self.assertEqual((p["本卦"]["世"], p["本卦"]["应"]), (4, 1))

    def test_guihun(self):
        # 火天大有 = 乾宫归魂，世3应6
        p = pan_of("离", "乾")
        self.assertIn("乾宫", p["本卦"]["宫"])
        self.assertEqual((p["本卦"]["世"], p["本卦"]["应"]), (3, 6))

    def test_palace_complete(self):
        self.assertEqual(len(liuyao.PALACE), 64)
        from collections import Counter
        c = Counter(g for g, _ in liuyao.PALACE.values())
        self.assertTrue(all(v == 8 for v in c.values()))


class TestLiuQin(unittest.TestCase):
    """六亲以宫五行配。"""

    def test_qian_liuqin(self):
        # 乾宫金：子水子孙、寅木妻财、辰土父母、午火官鬼、申金兄弟、戌土父母
        p = liuyao.build_pan([7] * 6)
        self.assertEqual([l["六亲"] for l in p["爻"]],
                         ["子孙", "妻财", "父母", "官鬼", "兄弟", "父母"])

    def test_liuqin_rule(self):
        self.assertEqual(liuyao._liuqin("金", "水"), "子孙")
        self.assertEqual(liuyao._liuqin("金", "木"), "妻财")
        self.assertEqual(liuyao._liuqin("金", "土"), "父母")
        self.assertEqual(liuyao._liuqin("金", "火"), "官鬼")
        self.assertEqual(liuyao._liuqin("金", "金"), "兄弟")


class TestDongBian(unittest.TestCase):
    """动爻与变卦。"""

    def test_all_moving(self):
        p = liuyao.build_pan([9] * 6)
        self.assertEqual(p["本卦"]["名"], "乾为天")
        self.assertEqual(p["变卦"]["名"], "坤为地")
        self.assertEqual(p["动爻"], [1, 2, 3, 4, 5, 6])

    def test_single_moving_bian(self):
        # 987888：下兑上坤=地泽临，初爻老阳动 → 变地水师；变爻按本宫(坤土)配六亲
        p = liuyao.build_pan([9, 7, 8, 8, 8, 8])
        self.assertEqual(p["本卦"]["名"], "地泽临")
        self.assertEqual(p["变卦"]["名"], "地水师")
        self.assertIn("官鬼", p["爻"][0]["变"])   # 戊寅木克坤宫土=官鬼

    def test_static_no_bian(self):
        p = liuyao.build_pan([7, 8, 7, 8, 7, 8])
        self.assertEqual(p["动爻"], [])
        self.assertNotIn("变卦", p)


class TestLiuShen(unittest.TestCase):
    """六神按日干起。"""

    def test_jia_day_qinglong(self):
        # 2026-06-19 为甲子日：初爻青龙，顺排
        p = liuyao.build_pan([7] * 6, date=(2026, 6, 19))
        self.assertEqual([l["六神"] for l in p["爻"]],
                         ["青龙", "朱雀", "勾陈", "螣蛇", "白虎", "玄武"])
        self.assertEqual(p["日月"]["日辰"], "甲子")

    def test_start_table(self):
        self.assertEqual(liuyao.LIUSHEN_START["戊"], 2)   # 戊起勾陈
        self.assertEqual(liuyao.LIUSHEN_START["己"], 3)   # 己起螣蛇
        self.assertEqual(liuyao.LIUSHEN_START["壬"], 5)   # 壬癸起玄武

    def test_no_date_no_liushen(self):
        p = liuyao.build_pan([7] * 6)
        self.assertNotIn("六神", p["爻"][0])
        self.assertNotIn("日月", p)


class TestFromGua(unittest.TestCase):
    """--gua 直接指定转摇卦标记。"""

    def test_static(self):
        marks = liuyao.from_gua(1, 1, 0)
        self.assertEqual(marks, [7] * 6)

    def test_with_dong(self):
        # 乾卦第 3 爻动：阳爻动=老阳9
        marks = liuyao.from_gua(1, 1, 3)
        self.assertEqual(marks, [7, 7, 9, 7, 7, 7])

    def test_bad_input(self):
        with self.assertRaises(ValueError):
            liuyao.from_gua(9, 1, 0)
        with self.assertRaises(ValueError):
            liuyao.from_gua(1, 1, 7)


class TestValidation(unittest.TestCase):
    def test_bad_marks(self):
        with self.assertRaises(ValueError):
            liuyao.build_pan([7, 7, 7])          # 少于六位
        with self.assertRaises(ValueError):
            liuyao.build_pan([5, 7, 8, 8, 8, 8])  # 非 6789


class TestCli(unittest.TestCase):
    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "liuyao.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_yao_cli(self):
        r = self._run("--yao", "787888", "--date", "2026", "6", "15")
        self.assertEqual(r.returncode, 0)
        self.assertIn("本卦", r.stdout)
        self.assertIn("日辰", r.stdout)

    def test_gua_cli_static(self):
        r = self._run("--gua", "1", "1", "0")
        self.assertEqual(r.returncode, 0)
        self.assertIn("乾为天", r.stdout)
        self.assertIn("静卦", r.stdout)

    def test_bad_date(self):
        r = self._run("--yao", "787888", "--date", "2026", "2", "30")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("日期非法", r.stdout + r.stderr)


if __name__ == "__main__":
    unittest.main(verbosity=2)
