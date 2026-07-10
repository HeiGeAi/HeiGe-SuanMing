#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ziwei.py 回归测试 · HeiGe-SuanMing / bazi-mingli skill

以开源紫微斗数实现 iztro（github.com/SylarLong/iztro，MIT，官方测试用例
astro.bySolar('2000-8-16', 2, '女', true)）的真实运算结果为基准真值：
十二宫、十四主星、四化、六吉六煞、大限、小限共 40+ 项数值经逐一核对全部吻合，
是本库四门术数里第一个用第三方可复现开源实现（不依赖网站转述或古籍孤例）
交叉核验过的黄金案例。

运行：
  python3 tests/test_ziwei.py
  python3 -m unittest discover -s tests
"""

import os
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)

import ziwei  # noqa: E402


class TestGoldenCase(unittest.TestCase):
    """黄金案例：公历2000-8-16 寅时(3:30) 女命，对齐 iztro 官方测试用例。"""

    @classmethod
    def setUpClass(cls):
        cls.c = ziwei.build_chart(2000, 8, 16, 3, 30, "female")

    def test_lunar_conversion(self):
        lu = self.c["lunar"]
        self.assertEqual(lu["年干支"], "庚辰")
        self.assertEqual(lu["月"], 7)
        self.assertEqual(lu["日"], 17)
        self.assertEqual(lu["时支"], "寅")

    def test_ming_shen_gong(self):
        self.assertEqual(self.c["命宫"]["干支"], "壬午")
        self.assertEqual(self.c["身宫"]["地支"], "戌")
        self.assertEqual(self.c["身宫"]["所在宫"], "官禄")

    def test_wuxing_ju(self):
        self.assertEqual(self.c["五行局"], "木3局")

    def test_ziwei_tianfu_position(self):
        self.assertEqual(self.c["紫微"], "午")
        self.assertEqual(self.c["天府"], "戌")

    def test_all_12_palace_ganzhi(self):
        # 五虎遁通排十二宫，与 iztro 输出逐宫干支完全一致
        expect = {"命宫": "壬午", "兄弟": "辛巳", "夫妻": "庚辰", "子女": "己卯",
                 "财帛": "戊寅", "疾厄": "己丑", "迁移": "戊子", "交友": "丁亥",
                 "官禄": "丙戌", "田宅": "乙酉", "福德": "甲申", "父母": "癸未"}
        for name, gz in expect.items():
            self.assertEqual(self.c["十二宫"][name]["干支"], gz, name)

    def test_all_14_major_stars(self):
        expect = {"命宫": ["紫微"], "兄弟": ["天机"], "夫妻": ["七杀"],
                 "子女": ["太阳", "天梁"], "财帛": ["武曲", "天相"],
                 "疾厄": ["天同", "巨门"], "迁移": ["贪狼"], "交友": ["太阴"],
                 "官禄": ["廉贞", "天府"], "田宅": [], "福德": ["破军"], "父母": []}
        for name, stars in expect.items():
            self.assertEqual(sorted(self.c["十二宫"][name]["主星"]), sorted(stars), name)

    def test_sihua(self):
        expect = {"子女": "太阳化禄", "财帛": "武曲化权",
                 "交友": "太阴化科", "疾厄": "天同化忌"}
        for name, hua in expect.items():
            self.assertIn(hua, self.c["十二宫"][name]["四化"], name)

    def test_liuji_stars(self):
        expect = {"命宫": "文曲", "夫妻": "右弼", "疾厄": "天魁",
                 "官禄": "左辅", "福德": "文昌", "父母": "天钺"}
        for name, star in expect.items():
            self.assertIn(star, self.c["十二宫"][name]["六吉"], name)

    def test_liusha_stars(self):
        expect = {"夫妻": "火星", "疾厄": "地劫", "迁移": "铃星",
                 "田宅": ["擎羊", "地空"], "福德": "禄存", "父母": "陀罗"}
        for name, star in expect.items():
            want = star if isinstance(star, list) else [star]
            for w in want:
                self.assertIn(w, self.c["十二宫"][name]["六煞"], name)

    def test_shen_gong_marked(self):
        self.assertTrue(self.c["十二宫"]["官禄"]["身宫"])
        for name in self.c["十二宫"]:
            if name != "官禄":
                self.assertFalse(self.c["十二宫"][name]["身宫"], name)

    def test_daxian_first_three(self):
        d = self.c["大限"]
        self.assertEqual((d[0]["起"], d[0]["止"], d[0]["宫"]), (3, 12, "命宫"))
        self.assertEqual((d[1]["起"], d[1]["止"], d[1]["宫"]), (13, 22, "兄弟"))
        self.assertEqual((d[2]["起"], d[2]["止"], d[2]["宫"]), (23, 32, "夫妻"))

    def test_xiaoxian_first_three(self):
        x = self.c["小限(1-12岁)"]
        self.assertEqual((x[1], x[2], x[3]), ("官禄", "田宅", "福德"))


class TestPalaceOrder(unittest.TestCase):
    """十二宫固定逆时针排列（不因命宫位置而改变相对顺序）。"""

    def test_order_is_counterclockwise(self):
        for ming_idx in range(12):
            order = ziwei.palace_order_from(ming_idx)
            self.assertEqual(order["命宫"], ming_idx)
            self.assertEqual(order["兄弟"], (ming_idx - 1) % 12)
            self.assertEqual(order["父母"], (ming_idx - 11) % 12)

    def test_12_names_unique_and_complete(self):
        order = ziwei.palace_order_from(0)
        self.assertEqual(len(set(order.values())), 12)
        self.assertEqual(set(order.keys()), set(ziwei.PALACE_NAMES))


class TestMingShenGongFormula(unittest.TestCase):
    """命宫身宫诀：寅起正月顺数生月，命宫逆数生时、身宫顺数生时。"""

    def test_zhengyue_zishi(self):
        # 正月子时：命宫身宫同落寅（原书「正月生子时就在寅宫安身命」）
        ming, shen = ziwei.locate_ming_shen_gong(1, 0)
        self.assertEqual(ziwei.ZHI[ming], "寅")
        self.assertEqual(ziwei.ZHI[shen], "寅")

    def test_zhengyue_yinshi(self):
        # 正月寅时：命宫逆数到子（原书「寅时逆转子安命」），身宫顺数到辰（「顺至辰安身」）
        ming, shen = ziwei.locate_ming_shen_gong(1, 2)
        self.assertEqual(ziwei.ZHI[ming], "子")
        self.assertEqual(ziwei.ZHI[shen], "辰")

    def test_wuyue_zishi(self):
        ming, _ = ziwei.locate_ming_shen_gong(5, 0)
        self.assertEqual(ziwei.ZHI[ming], "午")


class TestWuhuDun(unittest.TestCase):
    """五虎遁诀：甲己丙寅、乙庚戊寅、丙辛庚寅、丁壬壬寅、戊癸甲寅。"""

    def test_full_table(self):
        expect = {"甲": "丙", "己": "丙", "乙": "戊", "庚": "戊",
                 "丙": "庚", "辛": "庚", "丁": "壬", "壬": "壬", "戊": "甲", "癸": "甲"}
        for gan, yin_gan in expect.items():
            idx = ziwei._WUHU[ziwei.GAN_IDX[gan]]
            self.assertEqual(ziwei.GAN[idx], yin_gan, gan)


class TestWuxingJu(unittest.TestCase):
    """五行局数字诀：干支数相加>5减5，1-5对应木三/金四/水二/火六/土五局。"""

    def test_known_examples(self):
        cases = [("丙", "寅", "火", 6), ("甲", "子", "金", 4), ("丙", "子", "水", 2),
                 ("辛", "未", "土", 5), ("庚", "申", "木", 3), ("壬", "午", "木", 3)]
        for gan, zhi, wx, ju in cases:
            got_wx, got_ju = ziwei.wuxing_ju(ziwei.GAN_IDX[gan], ziwei.ZHI_IDX[zhi])
            self.assertEqual((got_wx, got_ju), (wx, ju), f"{gan}{zhi}")


class TestZiweiPosition(unittest.TestCase):
    """紫微星定位公式：局数除生日，商顺移、余查起点表，余0借位。"""

    def test_golden_case(self):
        self.assertEqual(ziwei.ZHI[ziwei.ziwei_position(3, 17)], "午")

    def test_day_less_than_ju(self):
        # 日数小于局数：商=0，余=日数，直接查起点表（原书「日数小于局，还直宫中守」）
        self.assertEqual(ziwei.ziwei_position(3, 2), ziwei._ZIWEI_TABLE[3][2])

    def test_zero_remainder_borrows(self):
        # 局数整除生日：商减1、余数补足局数
        pos_normal = ziwei.ziwei_position(3, 6)  # 6%3==0
        q, r = divmod(6, 3)
        expect = (ziwei._ZIWEI_TABLE[3][3] + (q - 1)) % 12
        self.assertEqual(pos_normal, expect)

    def test_all_ju_tables_have_correct_key_range(self):
        for ju in (2, 3, 4, 5, 6):
            self.assertEqual(set(ziwei._ZIWEI_TABLE[ju].keys()), set(range(1, ju + 1)))


class TestStarGroups(unittest.TestCase):
    """紫微星系逆时针、天府星系顺时针，方向相反是最易写反的一处。"""

    def test_ziwei_group_direction(self):
        g = ziwei.ziwei_star_group(6)  # 紫微在午(6)
        self.assertEqual(ziwei.ZHI[g["天机"]], "巳")
        self.assertEqual(ziwei.ZHI[g["太阳"]], "卯")
        self.assertEqual(ziwei.ZHI[g["武曲"]], "寅")
        self.assertEqual(ziwei.ZHI[g["天同"]], "丑")
        self.assertEqual(ziwei.ZHI[g["廉贞"]], "戌")

    def test_tianfu_group_direction(self):
        g = ziwei.tianfu_star_group(10)  # 天府在戌(10)
        self.assertEqual(ziwei.ZHI[g["太阴"]], "亥")
        self.assertEqual(ziwei.ZHI[g["贪狼"]], "子")
        self.assertEqual(ziwei.ZHI[g["破军"]], "申")

    def test_tianfu_position_formula(self):
        # (4 - 紫微序数) mod 12；纠正网传"永远对宫"的错误说法（紫微午→天府戌，相隔4非6）
        self.assertEqual(ziwei.tianfu_position(6), 10)
        self.assertNotEqual(ziwei.tianfu_position(6), (6 + 6) % 12)


class TestSihuaTable(unittest.TestCase):
    """四化表：十干各配四化星，禄权无分歧、科忌部分存疑但须给出确定值。"""

    def test_all_10_gans_have_4_hua(self):
        for gan in "甲乙丙丁戊己庚辛壬癸":
            self.assertEqual(set(ziwei.SIHUA[gan].keys()), {"化禄", "化权", "化科", "化忌"})

    def test_lu_quan_no_dispute(self):
        self.assertEqual(ziwei.SIHUA["甲"]["化禄"], "廉贞")
        self.assertEqual(ziwei.SIHUA["庚"]["化禄"], "太阳")
        self.assertEqual(ziwei.SIHUA["庚"]["化权"], "武曲")

    def test_geng_ke_ji_matches_verified_case(self):
        # 庚年化科化忌用 iztro 黄金案例实测过的版本（另说见 references/20 存疑标注）
        self.assertEqual(ziwei.SIHUA["庚"]["化科"], "太阴")
        self.assertEqual(ziwei.SIHUA["庚"]["化忌"], "天同")


class TestDaxianXiaoxianDirection(unittest.TestCase):
    """大限方向=年干阴阳+性别；小限方向=仅性别。两套独立逻辑不可共用一个变量。"""

    def test_daxian_yang_year_male_forward(self):
        self.assertEqual(ziwei.daxian_direction("甲", "male"), 1)

    def test_daxian_yang_year_female_backward(self):
        self.assertEqual(ziwei.daxian_direction("庚", "female"), -1)

    def test_daxian_yin_year_male_backward(self):
        self.assertEqual(ziwei.daxian_direction("乙", "male"), -1)

    def test_daxian_yin_year_female_forward(self):
        self.assertEqual(ziwei.daxian_direction("丁", "female"), 1)

    def test_xiaoxian_direction_gender_only(self):
        self.assertEqual(ziwei.xiaoxian_direction("male"), 1)
        self.assertEqual(ziwei.xiaoxian_direction("female"), -1)


class TestMingShenZhu(unittest.TestCase):
    """命主（命宫地支）身主（生年支六星循环）。
    iztro 本机实测三例对拍全中（astrolabe.soul/body 字段），命主取命宫地支
    （非生年支）由官方用例实证：2000 庚辰年命宫午 → 破军（若按年支辰应为廉贞）。"""

    def test_golden_case(self):
        c = ziwei.build_chart(2000, 8, 16, 3, 30, "female")
        self.assertEqual(c["命主"], "破军")   # 命宫午
        self.assertEqual(c["身主"], "文昌")   # 年支辰

    def test_second_case(self):
        c = ziwei.build_chart(1990, 1, 1, 0, 30, "male")
        self.assertEqual(c["命主"], "巨门")   # 命宫丑
        self.assertEqual(c["身主"], "天机")   # 年支巳（己巳年）

    def test_tables(self):
        # 命主表对称结构：子午轴镜像（丑=亥、寅=戌、卯=酉、辰=申、巳=未）
        self.assertEqual(len(ziwei.MINGZHU), 12)
        for i in range(1, 6):
            self.assertEqual(ziwei.MINGZHU[i], ziwei.MINGZHU[(12 - i) % 12], i)
        # 身主六星循环：火相梁同昌机，子午皆火星（主流；子铃午火为存疑另说）
        self.assertEqual(ziwei.SHENZHU_CYCLE[0], "火星")
        self.assertEqual(ziwei.SHENZHU_CYCLE[ziwei.ZHI_IDX["午"] % 6], "火星")


class TestFeiHua(unittest.TestCase):
    """宫干飞化与自化（同一张四化表按宫干起；iztro mutagedPlaces/selfMutaged 逐项对拍）。"""

    @classmethod
    def setUpClass(cls):
        cls.c = ziwei.build_chart(2000, 8, 16, 3, 30, "female")
        cls.g = cls.c["十二宫"]

    def test_minggong_feihua(self):
        # 命宫壬午：禄→天梁(子女) 权→紫微(命宫,自化权) 科→左辅(官禄) 忌→武曲(财帛)
        fh = self.g["命宫"]["飞化"]
        self.assertEqual((fh["化禄"]["星"], fh["化禄"]["入"]), ("天梁", "子女"))
        self.assertEqual((fh["化权"]["星"], fh["化权"]["入"]), ("紫微", "命宫"))
        self.assertEqual((fh["化科"]["星"], fh["化科"]["入"]), ("左辅", "官禄"))
        self.assertEqual((fh["化忌"]["星"], fh["化忌"]["入"]), ("武曲", "财帛"))

    def test_fuxing_located(self):
        # 四化星含辅星（左辅/文昌/文曲/右弼），定位函数必须覆盖（终审钉过的坑）
        fh = self.g["兄弟"]["飞化"]  # 辛巳：科文曲、忌文昌，均为辅星
        self.assertEqual((fh["化科"]["星"], fh["化科"]["入"]), ("文曲", "命宫"))
        self.assertEqual((fh["化忌"]["星"], fh["化忌"]["入"]), ("文昌", "福德"))

    def test_zihua_lixin(self):
        # 官禄宫丙戌坐廉贞，丙忌=廉贞 → 自化忌（离心，iztro selfMutaged('忌')=true）
        self.assertIn("化忌", self.g["官禄"]["自化"]["离心"])
        # 命宫壬午坐紫微，壬权=紫微 → 自化权
        self.assertIn("化权", self.g["命宫"]["自化"]["离心"])

    def test_zihua_xiangxin(self):
        # 向心自化：对宫干化入本宫。子女宫（卯）对宫田宅（乙酉），乙权=天梁在子女
        self.assertIn("化权", self.g["子女"]["自化"]["向心"])

    def test_daxian_sihua(self):
        # 大限四化=大限宫干查同表：第3限夫妻宫庚辰 → 庚干四化
        dx3 = self.c["大限"][2]
        self.assertEqual(dx3["宫干"], "庚")
        self.assertEqual(dx3["四化"], ziwei.SIHUA["庚"])


class TestValidation(unittest.TestCase):
    """输入校验：非法输入干净报错，不裸 traceback、不静默错果。"""

    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "ziwei.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_hour_out_of_range(self):
        r = self._run("2000", "8", "16", "24", "0", "--gender", "female")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("时0-23", r.stdout + r.stderr)

    def test_solar_invalid_date(self):
        r = self._run("2000", "2", "30", "3", "30", "--gender", "female")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("日期非法", r.stdout + r.stderr)

    def test_year_out_of_range(self):
        r = self._run("100", "8", "16", "3", "30", "--gender", "female")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stdout + r.stderr)

    def test_lunar_bad_month(self):
        r = self._run("2000", "13", "16", "3", "30", "--gender", "female", "--lunar")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("农历月须为", r.stdout + r.stderr)


class TestCli(unittest.TestCase):
    def _run(self, *extra):
        import subprocess
        script = os.path.join(_SCRIPTS, "ziwei.py")
        return subprocess.run([sys.executable, script, *extra], capture_output=True, text=True)

    def test_solar_cli(self):
        r = self._run("2000", "8", "16", "3", "30", "--gender", "female")
        self.assertEqual(r.returncode, 0)
        self.assertIn("命宫：壬午", r.stdout)

    def test_lunar_cli(self):
        r = self._run("2000", "7", "17", "3", "30", "--gender", "female", "--lunar")
        self.assertEqual(r.returncode, 0)
        self.assertIn("命宫：壬午", r.stdout)

    def test_json_cli(self):
        r = self._run("2000", "8", "16", "3", "30", "--gender", "female", "--json")
        self.assertEqual(r.returncode, 0)
        self.assertIn("\"命宫\"", r.stdout)

    def test_version(self):
        r = self._run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("ziwei v", r.stdout)


if __name__ == "__main__":
    unittest.main(verbosity=2)
