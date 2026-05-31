#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paipan.py 回归测试 · HeiGe-SuanMing / bazi-mingli skill

测试分两层，互不循环：
  1. 纯函数单元测试：以「命理古法定式」为基准真值（十神生成规则、地支藏干、
     长生十二宫阳顺阴逆、刑冲合会、神煞起例），校验本项目自写的胶水逻辑。
     这些定式在《渊海子平》《三命通会》等典籍中固定不变，不依赖排盘结果，
     因此能真正抓出本项目代码里的 bug。
  2. 集成测试：以已知节气/边界行为为基准（立春换年柱、节气换月柱、子时流派、
     大运顺逆、真太阳时方向），校验 lunar_python 委托链与本项目的整合是否正确。
     集成测试需要 lunar_python；纯函数测试不需要。

运行：
  python3 tests/test_paipan.py            # 直接跑
  python3 -m unittest discover -s tests   # 或用 unittest discover
"""

import argparse
import os
import sys
import unittest

# 把 scripts/ 加入 import 路径（paipan.py 有 __main__ 守卫，import 不会触发 main）
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)

import paipan  # noqa: E402


def make_args(year, month, day, hour, minute, gender="male",
              lunar=False, lng=None, tz=8.0, zi_sect=None, years=None):
    """构造 build_chart 所需的 argparse.Namespace。"""
    return argparse.Namespace(
        year=year, month=month, day=day, hour=hour, minute=minute,
        gender=gender, lunar=lunar, lng=lng, tz=tz, zi_sect=zi_sect, years=years,
    )


# ============================================================
# 第 1 层 · 纯函数单元测试（古法定式为基准）
# ============================================================
class TestTenGod(unittest.TestCase):
    """十神生成规则：同我比劫、我生食伤、我克财、克我官杀、生我印。
    阴阳同为偏（比/食/财/杀/枭），阴阳异为正（劫/伤/正财/正官/正印）。"""

    def test_jia_day_all_ten_gods(self):
        # 甲=阳木，对十干的十神（古法定式）
        expect = {
            "甲": "比肩", "乙": "劫财",      # 同类木
            "丙": "食神", "丁": "伤官",      # 木生火
            "戊": "偏财", "己": "正财",      # 木克土
            "庚": "七杀", "辛": "正官",      # 金克木
            "壬": "偏印", "癸": "正印",      # 水生木
        }
        for g, want in expect.items():
            self.assertEqual(paipan.ten_god("甲", g), want, f"甲见{g}应为{want}")

    def test_geng_day_all_ten_gods(self):
        # 庚=阳金
        expect = {
            "庚": "比肩", "辛": "劫财",      # 同类金
            "壬": "食神", "癸": "伤官",      # 金生水
            "甲": "偏财", "乙": "正财",      # 金克木
            "丙": "七杀", "丁": "正官",      # 火克金
            "戊": "偏印", "己": "正印",      # 土生金
        }
        for g, want in expect.items():
            self.assertEqual(paipan.ten_god("庚", g), want, f"庚见{g}应为{want}")

    def test_yi_day_yinyang_flip(self):
        # 乙=阴木，与甲日同五行关系但阴阳相反，正偏互换
        self.assertEqual(paipan.ten_god("乙", "庚"), "正官")   # 阴木见阳金，克我异性
        self.assertEqual(paipan.ten_god("乙", "辛"), "七杀")   # 阴木见阴金，克我同性
        self.assertEqual(paipan.ten_god("乙", "丙"), "伤官")   # 我生异性
        self.assertEqual(paipan.ten_god("乙", "丁"), "食神")   # 我生同性
        self.assertEqual(paipan.ten_god("乙", "壬"), "正印")   # 生我异性
        self.assertEqual(paipan.ten_god("乙", "癸"), "偏印")   # 生我同性

    def test_self_is_bijian(self):
        for g in paipan.GAN:
            self.assertEqual(paipan.ten_god(g, g), "比肩", f"{g}见{g}应为比肩")


class TestCangGan(unittest.TestCase):
    """地支藏干本气/中气/余气，古法固定表。"""

    def test_full_canggan_table(self):
        expect = {
            "子": ["癸"], "丑": ["己", "癸", "辛"], "寅": ["甲", "丙", "戊"], "卯": ["乙"],
            "辰": ["戊", "乙", "癸"], "巳": ["丙", "戊", "庚"], "午": ["丁", "己"],
            "未": ["己", "丁", "乙"], "申": ["庚", "壬", "戊"], "酉": ["辛"],
            "戌": ["戊", "辛", "丁"], "亥": ["壬", "甲"],
        }
        self.assertEqual(paipan.ZHI_CANGGAN, expect)

    def test_zhi_ten_gods_uses_benqi_first(self):
        # 甲日见午，午藏丁己 → 伤官(丁)/正财(己)
        self.assertEqual(paipan.zhi_ten_gods("甲", "午"), ["伤官", "正财"])
        # 庚日见寅，寅藏甲丙戊 → 偏财/七杀/偏印
        self.assertEqual(paipan.zhi_ten_gods("庚", "寅"), ["偏财", "七杀", "偏印"])


class TestDiShi(unittest.TestCase):
    """长生十二宫：阳干顺行、阴干逆行，长生位古法固定。"""

    def test_changsheng_positions(self):
        # 各干长生支（《渊海子平》长生定式）
        self.assertEqual(paipan._dishi_of("甲", "亥"), "长生")
        self.assertEqual(paipan._dishi_of("丙", "寅"), "长生")
        self.assertEqual(paipan._dishi_of("戊", "寅"), "长生")
        self.assertEqual(paipan._dishi_of("庚", "巳"), "长生")
        self.assertEqual(paipan._dishi_of("壬", "申"), "长生")
        self.assertEqual(paipan._dishi_of("乙", "午"), "长生")
        self.assertEqual(paipan._dishi_of("丁", "酉"), "长生")
        self.assertEqual(paipan._dishi_of("己", "酉"), "长生")
        self.assertEqual(paipan._dishi_of("辛", "子"), "长生")
        self.assertEqual(paipan._dishi_of("癸", "卯"), "长生")

    def test_diwang_positions(self):
        # 阳干帝旺（临官后一位顺行），阴干帝旺逆行
        self.assertEqual(paipan._dishi_of("甲", "卯"), "帝旺")   # 阳木顺行：亥子丑寅卯=帝旺
        self.assertEqual(paipan._dishi_of("乙", "寅"), "帝旺")   # 阴木逆行：午巳辰卯寅=帝旺
        self.assertEqual(paipan._dishi_of("庚", "酉"), "帝旺")
        self.assertEqual(paipan._dishi_of("壬", "子"), "帝旺")

    def test_yang_forward_yin_backward(self):
        # 甲(阳)长生亥，下一步顺行子=沐浴
        self.assertEqual(paipan._dishi_of("甲", "子"), "沐浴")
        # 乙(阴)长生午，下一步逆行巳=沐浴
        self.assertEqual(paipan._dishi_of("乙", "巳"), "沐浴")


class TestZhiRelations(unittest.TestCase):
    """地支刑冲合会，古法定式。"""

    def test_liuchong(self):
        rel = paipan.detect_zhi_relations([("甲", "子"), ("甲", "午"), ("甲", "辰"), ("甲", "申")])
        self.assertIn("六冲", rel)
        self.assertTrue(any("子" in s and "午" in s for s in rel["六冲"]))

    def test_sanhe_water(self):
        # 申子辰三合水局
        rel = paipan.detect_zhi_relations([("甲", "申"), ("甲", "子"), ("甲", "辰"), ("甲", "寅")])
        self.assertIn("三合", rel)
        self.assertTrue(any("水" in s for s in rel["三合"]))

    def test_banhe_needs_zhongshen(self):
        # 申子(含中神子) 半合水
        rel = paipan.detect_zhi_relations([("甲", "申"), ("甲", "子"), ("甲", "寅"), ("甲", "戌")])
        self.assertIn("半合", rel)
        # 申辰(无中神子) 不成半合
        rel2 = paipan.detect_zhi_relations([("甲", "申"), ("甲", "辰"), ("甲", "寅"), ("甲", "戌")])
        self.assertNotIn("半合", rel2)

    def test_sanhui_wood(self):
        # 寅卯辰三会东方木
        rel = paipan.detect_zhi_relations([("甲", "寅"), ("甲", "卯"), ("甲", "辰"), ("甲", "申")])
        self.assertIn("三会", rel)
        self.assertTrue(any("木" in s for s in rel["三会"]))

    def test_sanxing_wuen(self):
        # 寅巳申三刑全（无恩之刑）
        rel = paipan.detect_zhi_relations([("甲", "寅"), ("甲", "巳"), ("甲", "申"), ("甲", "子")])
        self.assertIn("相刑", rel)
        self.assertTrue(any("无恩" in s and "三刑全" in s for s in rel["相刑"]))

    def test_zixing(self):
        # 辰辰自刑
        rel = paipan.detect_zhi_relations([("甲", "辰"), ("甲", "辰"), ("甲", "子"), ("甲", "申")])
        self.assertIn("自刑", rel)
        self.assertTrue(any("辰辰" in s for s in rel["自刑"]))

    def test_zimao_xing(self):
        # 子卯无礼之刑
        rel = paipan.detect_zhi_relations([("甲", "子"), ("甲", "卯"), ("甲", "巳"), ("甲", "未")])
        self.assertIn("相刑", rel)
        self.assertTrue(any("子卯" in s for s in rel["相刑"]))

    def test_liuhai(self):
        # 子未六害
        rel = paipan.detect_zhi_relations([("甲", "子"), ("甲", "未"), ("甲", "寅"), ("甲", "酉")])
        self.assertIn("六害", rel)

    def test_liuhe(self):
        # 子丑六合化土
        rel = paipan.detect_zhi_relations([("甲", "子"), ("甲", "丑"), ("甲", "寅"), ("甲", "酉")])
        self.assertIn("六合", rel)
        self.assertTrue(any("子" in s and "丑" in s for s in rel["六合"]))


class TestGanRelations(unittest.TestCase):
    def test_gan_he(self):
        rel = paipan.detect_gan_relations([("甲", "子"), ("己", "丑"), ("丙", "寅"), ("戊", "辰")])
        self.assertIn("天干五合", rel)
        self.assertTrue(any("甲" in s and "己" in s for s in rel["天干五合"]))

    def test_gan_chong(self):
        rel = paipan.detect_gan_relations([("甲", "子"), ("庚", "丑"), ("丙", "寅"), ("戊", "辰")])
        self.assertIn("天干相冲", rel)
        self.assertTrue(any("甲" in s and "庚" in s for s in rel["天干相冲"]))


class TestShenSha(unittest.TestCase):
    """神煞起例，古法定式。"""

    def test_tianyi_guiren(self):
        # 甲日干，天乙贵人在丑未
        ss = paipan.compute_shensha([("甲", "丑"), ("甲", "未"), ("甲", "寅"), ("甲", "卯")])
        self.assertIn("天乙贵人", ss)

    def test_yangren(self):
        # 甲日羊刃在卯
        ss = paipan.compute_shensha([("甲", "子"), ("甲", "寅"), ("甲", "卯"), ("甲", "巳")])
        self.assertIn("羊刃", ss)

    def test_kuigang(self):
        # 庚辰日柱为魁罡
        ss = paipan.compute_shensha([("甲", "子"), ("甲", "寅"), ("庚", "辰"), ("甲", "巳")])
        self.assertIn("魁罡", ss)
        self.assertEqual(ss["魁罡"], ["日"])

    def test_taohua_by_sanhe(self):
        # 年支申(申子辰局)，桃花在酉
        ss = paipan.compute_shensha([("甲", "申"), ("甲", "丑"), ("甲", "寅"), ("甲", "酉")])
        self.assertIn("桃花", ss)


class TestWuXingCount(unittest.TestCase):
    def test_count_and_lack(self):
        # 年庚午 月辛巳 日庚辰 时癸未（1990 样例四柱）
        pillars = [("庚", "午"), ("辛", "巳"), ("庚", "辰"), ("癸", "未")]
        cnt, lack = paipan.wuxing_count(pillars)
        # 天干 庚辛庚癸=金金金水；地支 午巳辰未=火火土土
        self.assertEqual(cnt["金"], 3)
        self.assertEqual(cnt["水"], 1)
        self.assertEqual(cnt["火"], 2)
        self.assertEqual(cnt["土"], 2)
        self.assertEqual(cnt["木"], 0)
        self.assertEqual(lack, ["木"])

    def test_count_sums_to_eight(self):
        pillars = [("甲", "子"), ("乙", "丑"), ("丙", "寅"), ("丁", "卯")]
        cnt, _ = paipan.wuxing_count(pillars)
        self.assertEqual(sum(cnt.values()), 8)


class TestWuXingStrength(unittest.TestCase):
    def test_month_branch_doubled(self):
        # 全甲子四柱：四干甲=木+4；四子各藏癸(水本气1.0)，月支(idx1)×2
        # 水 = 1.0 + 2.0 + 1.0 + 1.0 = 5.0；木 = 4.0
        pillars = [("甲", "子"), ("甲", "子"), ("甲", "子"), ("甲", "子")]
        score, tong, yi, _, _ = paipan.wuxing_strength(pillars, "甲")
        self.assertAlmostEqual(score["木"], 4.0, places=2)
        self.assertAlmostEqual(score["水"], 5.0, places=2)
        # 甲日：同党=比劫(木)+印(水)=9.0，异党(食伤财官)=0
        self.assertAlmostEqual(tong, 9.0, places=2)
        self.assertAlmostEqual(yi, 0.0, places=2)


class TestTrueSolarTime(unittest.TestCase):
    def test_negative_correction_west_of_meridian(self):
        from datetime import datetime
        # 广州经度 113.3 < 标准子午线 120，校正应为负（钟表快于真太阳时）
        _, delta = paipan.true_solar_time(datetime(1990, 5, 15, 14, 30), 113.3, 8.0)
        self.assertLess(delta, 0)
        # 独立验算：(113.3-120)*4 = -26.8 分；加 5 月中旬均时差约 +3.7 → 约 -23
        self.assertAlmostEqual(delta, -23.0, delta=0.5)

    def test_positive_correction_east_of_meridian(self):
        from datetime import datetime
        # 经度 130 > 120，校正应为正
        _, delta = paipan.true_solar_time(datetime(1990, 5, 15, 14, 30), 130.0, 8.0)
        self.assertGreater(delta, 0)


# ============================================================
# 第 2 层 · 集成测试（节气/边界行为为基准）
# ============================================================
class TestIntegrationSample(unittest.TestCase):
    """1990-05-15 14:30 男（README 样例），核对四柱/月令/五行/大运方向。"""

    @classmethod
    def setUpClass(cls):
        cls.c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))

    def test_four_pillars(self):
        p = self.c["pillars"]
        self.assertEqual(p["年"], "庚午")
        self.assertEqual(p["月"], "辛巳")
        self.assertEqual(p["日"], "庚辰")
        self.assertEqual(p["时"], "癸未")

    def test_day_master_and_month_ling(self):
        self.assertTrue(self.c["day_master"].startswith("庚"))
        self.assertTrue(self.c["month_ling"].startswith("巳"))

    def test_wuxing_lack_wood(self):
        self.assertEqual(self.c["wuxing_lack"], ["木"])

    def test_dayun_forward_yang_male(self):
        # 庚午阳年男命 → 顺排
        self.assertEqual(self.c["yun_direction"], "顺排")

    def test_consistency_invariants(self):
        # 五行个数总和=8
        self.assertEqual(sum(self.c["wuxing_count"].values()), 8)
        # 同党+异党 ≈ 全盘五行力量总和
        total = round(sum(self.c["wuxing_score"].values()), 2)
        self.assertAlmostEqual(self.c["tong_dang"] + self.c["yi_dang"], total, places=1)


class TestIntegrationLiChunBoundary(unittest.TestCase):
    """立春换年柱：手推最易错处。2000 立春在 2/4。"""

    def test_before_lichun_uses_prev_year_pillar(self):
        # 2000-02-03（立春前）年柱应为 己卯（1999 干支），月柱丁丑
        c = paipan.build_chart(make_args(2000, 2, 3, 12, 0, "male"))
        self.assertEqual(c["pillars"]["年"], "己卯")
        self.assertEqual(c["pillars"]["月"], "丁丑")

    def test_after_lichun_uses_new_year_pillar(self):
        # 2000-02-05（立春后）年柱应为 庚辰，月柱戊寅
        c = paipan.build_chart(make_args(2000, 2, 5, 12, 0, "male"))
        self.assertEqual(c["pillars"]["年"], "庚辰")
        self.assertEqual(c["pillars"]["月"], "戊寅")


class TestIntegrationZiSect(unittest.TestCase):
    """子时流派：23:30 出生，晚子换日 vs 不换日影响日柱，时支恒为子。"""

    def test_default_sect(self):
        c = paipan.build_chart(make_args(2000, 6, 1, 23, 30, "male"))
        self.assertEqual(c["pillars"]["日"], "庚寅")
        self.assertEqual(c["pillars"]["时"][1], "子")

    def test_sect1_late_zi_switches_day(self):
        # 晚子(23点)换日 → 日柱进位为辛卯
        c = paipan.build_chart(make_args(2000, 6, 1, 23, 30, "male", zi_sect=1))
        self.assertEqual(c["pillars"]["日"], "辛卯")
        self.assertEqual(c["pillars"]["时"][1], "子")

    def test_sect2_no_switch(self):
        # 不换日 → 日柱仍为庚寅
        c = paipan.build_chart(make_args(2000, 6, 1, 23, 30, "male", zi_sect=2))
        self.assertEqual(c["pillars"]["日"], "庚寅")
        self.assertEqual(c["pillars"]["时"][1], "子")


class TestIntegrationDaYunDirection(unittest.TestCase):
    """大运顺逆：阳年男顺/女逆，阴年男逆/女顺。"""

    def test_yang_year_male_forward(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))   # 庚午阳年
        self.assertEqual(c["yun_direction"], "顺排")

    def test_yang_year_female_backward(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "female"))  # 庚午阳年女
        self.assertEqual(c["yun_direction"], "逆排")


class TestIntegrationTrueSolar(unittest.TestCase):
    """真太阳时校正：广州 113.3 应使时刻提前，可能改变时柱。"""

    def test_correction_applied(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=113.3))
        self.assertIsNotNone(c["input"]["correction"])
        # 14:30 校正约 -23 分 → 14:07 左右，仍在未时(13-15)，时支未
        self.assertEqual(c["pillars"]["时"][1], "未")


if __name__ == "__main__":
    unittest.main(verbosity=2)
