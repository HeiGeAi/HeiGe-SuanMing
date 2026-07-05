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


class TestTianDe(unittest.TestCase):
    """天德贵人：按月支取所得既有天干（如寅月丁，查四干）也有地支
    （卯月申、午月亥、酉月寅、子月巳，查四支），references/06 古法定式。"""

    def test_mao_month_branch_shen(self):
        # 卯月天德=申(地支)，申在日支
        ss = paipan.compute_shensha([("甲", "子"), ("丙", "卯"), ("乙", "申"), ("丁", "丑")])
        self.assertIn("天德贵人", ss)
        self.assertIn("日", ss["天德贵人"])

    def test_wu_month_branch_hai(self):
        # 午月天德=亥(地支)，亥在年支
        ss = paipan.compute_shensha([("甲", "亥"), ("庚", "午"), ("乙", "丑"), ("丁", "辰")])
        self.assertIn("天德贵人", ss)
        self.assertIn("年", ss["天德贵人"])

    def test_you_month_branch_yin(self):
        # 酉月天德=寅(地支)，寅在年支
        ss = paipan.compute_shensha([("甲", "寅"), ("乙", "酉"), ("丙", "子"), ("丁", "丑")])
        self.assertIn("天德贵人", ss)
        self.assertIn("年", ss["天德贵人"])

    def test_zi_month_branch_si(self):
        # 子月天德=巳(地支)，巳在日支
        ss = paipan.compute_shensha([("甲", "辰"), ("丙", "子"), ("丁", "巳"), ("戊", "申")])
        self.assertIn("天德贵人", ss)
        self.assertIn("日", ss["天德贵人"])

    def test_yin_month_stem_ding_regression(self):
        # 寅月天德=丁(天干)，丁透年干——天干型查法回归
        ss = paipan.compute_shensha([("丁", "卯"), ("壬", "寅"), ("甲", "子"), ("乙", "丑")])
        self.assertIn("天德贵人", ss)
        self.assertIn("年", ss["天德贵人"])


class TestShenShaDeterminism(unittest.TestCase):
    """神煞输出确定性：固定传统次序（吉神→中性→凶煞），柱标按年月日时，
    不随哈希随机化漂移。"""

    def test_order_follows_tradition(self):
        ss = paipan.compute_shensha([("庚", "午"), ("辛", "巳"), ("庚", "辰"), ("癸", "未")])
        keys = list(ss.keys())
        idx = [paipan.SHENSHA_ORDER.index(k) for k in keys if k in paipan.SHENSHA_ORDER]
        self.assertEqual(idx, sorted(idx), "神煞键序未按 SHENSHA_ORDER 排列")

    def test_pillar_labels_sorted(self):
        ss = paipan.compute_shensha([("庚", "午"), ("辛", "巳"), ("庚", "辰"), ("癸", "未")])
        order = {"年": 0, "月": 1, "日": 2, "时": 3}
        for name, labs in ss.items():
            self.assertEqual(labs, sorted(labs, key=lambda x: order[x]),
                             f"{name} 柱标未按年月日时排序")

    def test_output_invariant_across_hash_seeds(self):
        # 子进程分别用不同 PYTHONHASHSEED 跑同一命盘，输出必须逐字节一致
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        cmd = [sys.executable, script, "1990", "6", "23", "0", "30",
               "--gender", "male", "--years", "2024", "12"]
        outs = []
        for seed in ("1", "99"):
            env = dict(os.environ, PYTHONHASHSEED=seed)
            r = subprocess.run(cmd, capture_output=True, text=True, env=env)
            self.assertEqual(r.returncode, 0, r.stderr)
            outs.append(r.stdout)
        self.assertEqual(outs[0], outs[1], "不同哈希种子下输出不一致")


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


class TestIntegrationLiuNianLiChun(unittest.TestCase):
    """流年与年柱同一套立春分界逻辑。"""

    def test_liunian_ganzhi_matches_year_pillar(self):
        self.assertEqual(paipan.liunian_ganzhi(2024), "甲辰")
        self.assertEqual(paipan.liunian_ganzhi(2025), "乙巳")
        self.assertEqual(paipan.liunian_ganzhi(1990), "庚午")

    def test_default_start_year_before_lichun(self):
        from datetime import datetime
        # 2024 立春为 2/4：立春前仍属癸卯年，流年起始年应取 2023
        self.assertEqual(paipan.liunian_start_year(datetime(2024, 2, 3, 12, 0)), 2023)

    def test_default_start_year_after_lichun(self):
        from datetime import datetime
        self.assertEqual(paipan.liunian_start_year(datetime(2024, 2, 5, 12, 0)), 2024)

    def test_build_chart_liunian_ganzhi(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", years=[2024, 2]))
        self.assertEqual(c["liunian"][0]["ganzhi"], "甲辰")
        self.assertEqual(c["liunian"][1]["ganzhi"], "乙巳")


class TestIntegrationLunarLng(unittest.TestCase):
    """--lunar 与 --lng 同传：农历先转公历，再做真太阳时校正，两者叠加生效。"""

    def test_lunar_with_lng_applies_correction(self):
        c = paipan.build_chart(make_args(1990, 4, 21, 14, 30, "male", lunar=True, lng=113.3))
        self.assertIsNotNone(c["input"]["correction"], "农历输入时真太阳时校正被丢弃")
        self.assertIsNotNone(c["input"]["true_solar"])
        # 与等价的公历输入+经度校正结果完全一致
        c2 = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=113.3))
        self.assertEqual(c["pillars"], c2["pillars"])
        self.assertEqual(c["input"]["true_solar"], c2["input"]["true_solar"])


class TestIntegrationLeapMonth(unittest.TestCase):
    """闰月输入：负数月表示闰月（lunar_python 约定），-2=闰二月。"""

    def test_leap_2nd_month_2023(self):
        # 2023 闰二月初一 = 公历 2023-03-22
        c = paipan.build_chart(make_args(2023, -2, 1, 12, 0, "male", lunar=True))
        self.assertEqual(c["input"]["solar"], "2023-03-22 12:00")
        self.assertIn("闰二月", c["input"]["lunar"])


class TestIntegrationSolarDisplay(unittest.TestCase):
    """真太阳时校正后：公历行保留原始输入，校正时刻另起 true_solar。"""

    def test_solar_keeps_original_true_solar_separate(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=113.3))
        self.assertEqual(c["input"]["solar"], "1990-05-15 14:30")
        self.assertTrue(c["input"]["true_solar"].startswith("1990-05-15 14:0"))
        self.assertNotEqual(c["input"]["solar"], c["input"]["true_solar"])

    def test_no_lng_no_true_solar(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))
        self.assertIsNone(c["input"]["true_solar"])


class TestIntegrationCorrectionDisplay(unittest.TestCase):
    """时区显示与大幅校正强提示。"""

    def test_negative_tz_display(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=-75.0, tz=-5.0))
        self.assertIn("UTC-5.0", c["input"]["correction"])
        self.assertNotIn("UTC+-", c["input"]["correction"])

    def test_large_correction_warning(self):
        # 经度 0、时区 +8 → 校正约 -480 分钟，须出强提示
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=0.0))
        self.assertIn("强提示", c["input"]["correction"])

    def test_normal_correction_no_warning(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male", lng=113.3))
        self.assertNotIn("强提示", c["input"]["correction"])


class TestIntegrationQiYunXuSui(unittest.TestCase):
    """起运岁数统一虚岁口径（references/11：三日折一岁得起运虚岁），与大运列表一致。"""

    def test_start_age_is_xusui(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))
        # 1990 年生、1997-08-04 起运 → 虚岁 8（1997-1990+1），与首步大运 start_age 一致
        self.assertEqual(c["start_age"], 8)
        first = next(d for d in c["dayun"] if d["ganzhi"])
        self.assertEqual(c["start_age"], first["start_age"])


class TestIntegrationJsonDisclaimer(unittest.TestCase):
    def test_disclaimer_in_chart(self):
        c = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))
        self.assertIn("disclaimer", c)
        self.assertIn("仅供", c["disclaimer"])


class TestCliValidation(unittest.TestCase):
    """命令行输入校验：越界经度 / 非法流年区间 / 年份范围 / 农历小月与不存在的闰月。"""

    @classmethod
    def setUpClass(cls):
        cls.script = os.path.join(_SCRIPTS, "paipan.py")

    def _run(self, *argv):
        import subprocess
        return subprocess.run([sys.executable, self.script, *argv],
                              capture_output=True, text=True)

    def test_lng_out_of_range(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male", "--lng", "200")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("经度超出范围", r.stderr + r.stdout)

    def test_years_span_zero(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male", "--years", "2024", "0")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("≥1", r.stderr + r.stdout)

    def test_year_out_of_range(self):
        r = self._run("1500", "5", "15", "14", "30", "--gender", "male")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stderr + r.stdout)

    def test_lunar_short_month_day30(self):
        # 农历 1990 年四月为小月（29 天），30 日应友好报错而非裸 traceback
        r = self._run("1990", "4", "30", "12", "0", "--gender", "male", "--lunar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("只有 29 天", r.stderr + r.stdout)
        self.assertNotIn("Traceback", r.stderr)

    def test_nonexistent_leap_month(self):
        # 2023 年只有闰二月，闰三月应友好报错
        r = self._run("2023", "-3", "1", "12", "0", "--gender", "male", "--lunar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("没有闰3月", r.stderr + r.stdout)
        self.assertNotIn("Traceback", r.stderr)


class TestIntegrationRobustness(unittest.TestCase):
    """多样输入的鲁棒性：不崩溃 + 命盘不变量恒成立 + 可 JSON 序列化。
    把子时双流派、真太阳东西经、立春边界、农历(含闰年)、极早/未来年、
    自定义流年、阴阳年男女大运顺逆等边界场景固化进回归基准，
    保证排盘引擎在异常边界上仍输出结构完整、自洽、可序列化的命盘。"""

    SCENARIOS = {
        "基准男命":        dict(year=1990, month=6, day=23, hour=0, minute=30, gender="male"),
        "女命逆排":        dict(year=1990, month=6, day=23, hour=0, minute=30, gender="female"),
        "子时流派1换日":   dict(year=1988, month=12, day=31, hour=23, minute=30, gender="male", zi_sect=1),
        "子时流派2不换日": dict(year=1988, month=12, day=31, hour=23, minute=30, gender="male", zi_sect=2),
        "真太阳东经121.5": dict(year=1990, month=6, day=23, hour=10, minute=49, gender="male", lng=121.5),
        "真太阳西经75":    dict(year=1990, month=6, day=23, hour=10, minute=49, gender="male", lng=75.0),
        "立春当天":        dict(year=2000, month=2, day=4, hour=12, minute=0, gender="male"),
        "立春前夜":        dict(year=2000, month=2, day=3, hour=23, minute=0, gender="female"),
        "农历输入":        dict(year=1990, month=9, day=1, hour=10, minute=0, gender="male", lunar=True),
        "农历闰年":        dict(year=2023, month=4, day=15, hour=8, minute=0, gender="female", lunar=True),
        "农历闰月负数月":  dict(year=2023, month=-2, day=15, hour=8, minute=0, gender="female", lunar=True),
        "农历加真太阳时":  dict(year=1990, month=4, day=21, hour=14, minute=30, gender="male", lunar=True, lng=113.3),
        "极早年1920":      dict(year=1920, month=1, day=1, hour=0, minute=0, gender="male"),
        "未来年2050":      dict(year=2050, month=12, day=31, hour=23, minute=59, gender="female"),
        "自定义流年":      dict(year=1990, month=6, day=23, hour=0, minute=30, gender="male", years=[2030, 5]),
    }

    def _assert_invariants(self, name, c):
        # 1) 四柱齐全，每柱两字
        for k in ("年", "月", "日", "时"):
            self.assertIn(k, c["pillars"], f"{name}: 缺{k}柱")
            self.assertEqual(len(c["pillars"][k]), 2, f"{name}: {k}柱非两字")
        # 2) 五行个数总和=8（四干四支）
        self.assertEqual(sum(c["wuxing_count"].values()), 8, f"{name}: 五行个数非8")
        # 3) 同党+异党 ≈ 全盘五行力量总和（每个五行非同党即异党）
        total = round(sum(c["wuxing_score"].values()), 2)
        self.assertAlmostEqual(c["tong_dang"] + c["yi_dang"], total, places=1,
                               msg=f"{name}: 同党+异党≠总力量")
        # 4) 大运方向二选一
        self.assertIn(c["yun_direction"], ("顺排", "逆排"), f"{name}: 大运方向异常")
        # 5) 日主非空且首字为十干
        self.assertTrue(c["day_master"] and c["day_master"][0] in paipan.GAN,
                        f"{name}: 日主异常")

    def test_all_scenarios_no_crash_and_invariants(self):
        for name, kw in self.SCENARIOS.items():
            with self.subTest(scenario=name):
                c = paipan.build_chart(make_args(**kw))
                self._assert_invariants(name, c)

    def test_chart_is_json_serializable(self):
        # --json 即 json.dumps(chart)；逐场景确认可序列化且可无损回读
        import json
        for name, kw in self.SCENARIOS.items():
            with self.subTest(scenario=name):
                c = paipan.build_chart(make_args(**kw))
                s = json.dumps(c, ensure_ascii=False)
                self.assertIn(c["pillars"]["日"], s, f"{name}: 日柱未出现在 JSON")
                self.assertEqual(json.loads(s)["pillars"], c["pillars"],
                                 f"{name}: JSON 回读四柱不一致")


# ============================================================
# v1.3.0 新增：流月流日 / 合婚 / 夏令时 / 半合去重 / 子时钉死 / 校验补强
# ============================================================
class TestLiuYueLiuRi(unittest.TestCase):
    """流月流日数据层（断语止于月，引擎只出干支事实）。"""

    def test_liunian_matches_engine(self):
        td = paipan.target_date_analysis(2027, 3, 15, "丁", ["午", "巳", "辰", "未"])
        self.assertEqual(td["流年"]["ganzhi"], paipan.liunian_ganzhi(2027))

    def test_liuri_matches_day_pillar(self):
        c = paipan.build_chart(make_args(2027, 3, 15, 12, 0))
        natal = [c["pillars"][k][1] for k in ["年", "月", "日", "时"]]
        td = paipan.target_date_analysis(2027, 3, 15, c["pillars"]["日"][0], natal)
        self.assertEqual(td["流日"]["ganzhi"], c["pillars"]["日"])

    def test_liuyue_by_jieqi_not_lunar_month(self):
        before = paipan.target_date_analysis(2027, 3, 4, "丁", ["午"])
        after = paipan.target_date_analysis(2027, 3, 6, "丁", ["午"])
        self.assertEqual(before["流月"]["ganzhi"], "壬寅")
        self.assertEqual(after["流月"]["ganzhi"], "癸卯")

    def test_ten_god_vs_daymaster(self):
        td = paipan.target_date_analysis(2027, 3, 15, "丁", ["午"])
        gz = td["流年"]["ganzhi"]
        self.assertEqual(td["流年"]["gan_shen"], paipan.ten_god("丁", gz[0]))

    def test_vs_natal_chong(self):
        hits = paipan._zhi_vs_natal("子", ["午", "辰", "寅", "申"])
        self.assertIn("冲年午", hits)


class TestHeHun(unittest.TestCase):
    """合婚双盘对照：只出关系事实，不打分、不下合不合判词。"""

    def setUp(self):
        self.a = paipan.build_chart(make_args(1990, 5, 15, 14, 30, "male"))
        self.b = paipan.build_chart(make_args(1992, 8, 15, 10, 0, "female"))

    def test_keys_present(self):
        r = paipan.compatibility(self.a, self.b)
        for k in ("日干", "夫妻宫(日支)", "生肖(年支)", "五行缺", "五行个数"):
            self.assertIn(k, r)

    def test_no_score_no_verdict(self):
        r = paipan.compatibility(self.a, self.b)
        for v in r.values():
            for bad in ("不合", "打分", "评分", "合婚煞"):
                self.assertNotIn(bad, v)

    def test_self_pair_baseline(self):
        r = paipan.compatibility(self.a, self.a)
        self.assertIn("同为", r["日干"])
        self.assertNotIn("相冲", r["夫妻宫(日支)"])

    def test_zhi_pair_relation_symmetric(self):
        self.assertIn("六合", paipan._zhi_pair_desc("子", "丑"))
        self.assertIn("六合", paipan._zhi_pair_desc("丑", "子"))
        self.assertIn("相冲", paipan._zhi_pair_desc("子", "午"))
        self.assertIn("相冲", paipan._zhi_pair_desc("午", "子"))

    def test_cli_partner_year_range(self):
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        r = subprocess.run([sys.executable, script, "1990", "5", "15", "14", "30",
                            "--gender", "male", "--partner", "1500", "8", "15", "10", "0",
                            "--partner-gender", "female"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stdout + r.stderr)


class TestBanHeDedup(unittest.TestCase):
    """ENG-1 回归：半合遇重复地支不把重复柱误列成三方。"""

    def test_duplicate_branch_not_three_pillars(self):
        r = paipan.detect_zhi_relations([("庚", "申"), ("甲", "子"), ("丙", "子"), ("戊", "寅")])
        self.assertIn("半合", r)
        entry = r["半合"][0]
        inner = entry[entry.index("(") + 1:entry.index(")")]
        self.assertEqual(len(inner.split("·")), 2, f"半合应只列两支，实为 {entry}")
        self.assertNotIn("日子", entry)


class TestZiShiPin(unittest.TestCase):
    """ENG-3：子时时干按流派钉死，防 lunar_python 升级或流派改动悄改。"""

    def test_zi_sect_1_late_advances_day(self):
        c = paipan.build_chart(make_args(2000, 6, 1, 23, 30, zi_sect=1))
        self.assertEqual(c["pillars"]["日"], "辛卯")
        self.assertEqual(c["pillars"]["时"], "戊子")

    def test_zi_sect_2_no_advance(self):
        c = paipan.build_chart(make_args(2000, 6, 1, 23, 30, zi_sect=2))
        self.assertEqual(c["pillars"]["日"], "庚寅")
        self.assertEqual(c["pillars"]["时"], "戊子")


class TestDstNote(unittest.TestCase):
    """TST-4：中国 1986-1991 夏令时核时提示。"""

    def test_in_window(self):
        n = paipan.china_dst_note(1988, 7, 1)
        self.assertIsNotNone(n)
        self.assertIn("夏令时", n)

    def test_window_start_boundary(self):
        self.assertIsNotNone(paipan.china_dst_note(1988, 4, 10))

    def test_out_of_window_month(self):
        self.assertIsNone(paipan.china_dst_note(1988, 2, 1))

    def test_non_dst_year(self):
        self.assertIsNone(paipan.china_dst_note(1995, 7, 1))


class TestCliMore(unittest.TestCase):
    """TST-5：输入校验补强（子进程跑 CLI）。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_hour_out_of_range(self):
        r = self._run("1990", "5", "15", "24", "30", "--gender", "male")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("时0-23", r.stdout + r.stderr)

    def test_solar_invalid_date(self):
        r = self._run("1990", "2", "30", "14", "30", "--gender", "male")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("日期非法", r.stdout + r.stderr)

    def test_target_date_invalid(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--target-date", "2027", "2", "30")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("日期非法", r.stdout + r.stderr)

    def test_tz_without_lng_note(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male", "--tz", "9")
        self.assertEqual(r.returncode, 0)
        self.assertIn("--tz 需与 --lng 配合", r.stdout)


class TestShenShaMore(unittest.TestCase):
    """TST-6：补神煞分支测试（古法起例为真值）。"""

    def test_yuede_wu_month(self):
        r = paipan.compute_shensha([("丙", "午"), ("甲", "午"), ("庚", "子"), ("戊", "寅")])
        self.assertEqual(r.get("月德贵人"), ["年"])

    def test_jiangxing_yima_huagai_sanhe(self):
        r = paipan.compute_shensha([("庚", "申"), ("甲", "子"), ("丙", "辰"), ("戊", "寅")])
        self.assertIn("将星", r)
        self.assertIn("驿马", r)
        self.assertIn("华盖", r)

    def test_wenchang_lushen(self):
        r = paipan.compute_shensha([("壬", "子"), ("丙", "午"), ("甲", "巳"), ("丙", "寅")])
        self.assertIn("文昌贵人", r)
        self.assertIn("禄神", r)


class TestYearBoundary(unittest.TestCase):
    """TST-7：年份边界端点与越界。"""

    def test_min_max_year_ok(self):
        for y in (1600, 2200):
            c = paipan.build_chart(make_args(y, 6, 15, 12, 0))
            self.assertEqual(len(c["pillars"]), 4)
            self.assertTrue(all(c["pillars"][k] for k in ["年", "月", "日", "时"]))

    def test_cli_above_max(self):
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        r = subprocess.run([sys.executable, script, "2201", "5", "15", "14", "30",
                            "--gender", "male"], capture_output=True, text=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stdout + r.stderr)

    def test_cli_min_endpoint_ok(self):
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        r = subprocess.run([sys.executable, script, "1600", "6", "15", "12", "0",
                            "--gender", "male"], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0)


# ============================================================
# v1.3.1 审计修复回归（partner 校验/历法开关、刑口径、DST 边界、交节提示）
# ============================================================
class TestPartnerValidation(unittest.TestCase):
    """B1/B2/B3：合婚第二人输入校验与独立历法开关。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "paipan.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_partner_invalid_solar_date(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--partner", "1992", "2", "30", "10")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("合婚第二人日期非法", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stderr)

    def test_partner_invalid_month(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--partner", "1990", "13", "40", "10")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stderr)

    def test_partner_hour_range(self):
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--partner", "1992", "8", "15", "25")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("时0-23", r.stdout + r.stderr)

    def test_partner_defaults_solar_even_if_main_lunar(self):
        # B2：主盘农历时，乙方默认仍按公历解释（1992-08-15 公历日柱癸亥）
        r = self._run("1990", "4", "21", "14", "30", "--gender", "male", "--lunar",
                      "--partner", "1992", "8", "15", "10")
        self.assertEqual(r.returncode, 0)
        self.assertIn("癸亥", r.stdout)
        self.assertIn("公历输入", r.stdout)

    def test_partner_lunar_flag(self):
        # --partner-lunar 时乙方按农历解释（农历 1992-08-15 = 公历 1992-09-11，日柱庚寅）
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--partner", "1992", "8", "15", "10", "--partner-lunar")
        self.assertEqual(r.returncode, 0)
        self.assertIn("农历输入", r.stdout)

    def test_partner_dst_note_passthrough(self):
        # B8：乙方生于夏令时期须提示
        r = self._run("1990", "5", "15", "14", "30", "--gender", "male",
                      "--partner", "1988", "7", "1", "10")
        self.assertEqual(r.returncode, 0)
        self.assertIn("乙方夏令时", r.stdout)


class TestZhiPairDescV131(unittest.TestCase):
    """B4/B5：合婚地支关系口径与原局引擎对齐。"""

    def test_banhe_requires_zhongshen(self):
        self.assertIn("拱", paipan._zhi_pair_desc("申", "辰"))
        self.assertNotIn("半合", paipan._zhi_pair_desc("申", "辰"))
        self.assertIn("半合", paipan._zhi_pair_desc("申", "子"))

    def test_xing_pairs(self):
        self.assertIn("相刑", paipan._zhi_pair_desc("丑", "戌"))
        self.assertIn("相刑", paipan._zhi_pair_desc("戌", "未"))
        self.assertIn("相刑兼相害", paipan._zhi_pair_desc("寅", "巳"))

    def test_self_xing(self):
        self.assertIn("自刑", paipan._zhi_pair_desc("午", "午"))
        self.assertNotIn("自刑", paipan._zhi_pair_desc("子", "子"))


class TestVsNatalXingV131(unittest.TestCase):
    """B6：流年流月流日对原局的刑与自刑不漏报。"""

    def test_xing_reported(self):
        hits = paipan._zhi_vs_natal("戌", ["丑", "巳", "丑", "巳"])
        self.assertIn("刑年丑", hits)
        self.assertIn("刑日丑", hits)

    def test_self_xing_reported(self):
        hits = paipan._zhi_vs_natal("午", ["午", "戌", "寅", "子"])
        self.assertIn("自刑年午", hits)

    def test_non_zixing_equal_skipped(self):
        hits = paipan._zhi_vs_natal("子", ["子", "戌", "寅", "申"])
        self.assertFalse(any("自刑" in h for h in hits))


class TestDstBoundaryV131(unittest.TestCase):
    """B10：夏令时起止边界日按凌晨 2 时切换提示。"""

    def test_start_day_wording(self):
        n = paipan.china_dst_note(1986, 5, 4)
        self.assertIn("开始日", n)
        self.assertIn("2 时", n)

    def test_end_day_wording(self):
        n = paipan.china_dst_note(1986, 9, 14)
        self.assertIn("结束日", n)
        self.assertIn("回拨", n)

    def test_mid_window_wording(self):
        n = paipan.china_dst_note(1988, 7, 1)
        self.assertIn("实施期", n)


class TestTargetDateBoundaryV131(unittest.TestCase):
    """B7：交节/立春当日输出边界提示。"""

    def test_lichun_day_has_note(self):
        td = paipan.target_date_analysis(2024, 2, 4, "丁", ["午"])
        self.assertIn("边界提示", td)

    def test_normal_day_no_note(self):
        td = paipan.target_date_analysis(2024, 2, 20, "丁", ["午"])
        self.assertNotIn("边界提示", td)


if __name__ == "__main__":
    unittest.main(verbosity=2)
