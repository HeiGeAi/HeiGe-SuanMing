#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
奇门遁甲排局引擎回归测试。

黄金基准来源（四源交叉，无单库全对、须拼装的教训见 references/21）：
- 用例 A（2026-07-09 10:30 阴遁二局）：kinqimen 与 qfdk/qimen 本机活体实跑
  逐宫一致，另有 qimenpaipan 与元亨利贞在线排盘四源一致，最强基准。
- 用例 B（2026-01-01 12:00 阳遁四局）：天禽入中 + 值使从真实宫数 5 起数 +
  全盘星反吟三重边界；「从宫 5 起数」为多方权威盘证伪 qfdk 少数派数法后
  钉死的口径。
- 定局边界：lunar_python getPrevJieQi 日粒度坑、23 点换日、拆补法节气内
  不混局，均按 references/21 实测结论钉死。
"""

import json
import os
import subprocess
import sys
import unittest

_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPTS = os.path.join(os.path.dirname(_HERE), "scripts")
sys.path.insert(0, _SCRIPTS)

import qimen  # noqa: E402

QIMEN_PY = os.path.join(_SCRIPTS, "qimen.py")


class TestGoldenCaseA(unittest.TestCase):
    """黄金用例 A：2026-07-09 10:30，阴遁二局中元（四源一致最强基准）。"""

    @classmethod
    def setUpClass(cls):
        cls.pan = qimen.build_pan(2026, 7, 9, 10, 30)

    def test_pillars(self):
        p = self.pan["四柱"]
        self.assertEqual(p["年柱"], "丙午")
        self.assertEqual(p["月柱"], "乙未")
        self.assertEqual(p["日柱"], "甲申")
        self.assertEqual(p["时柱"], "己巳")

    def test_jieqi(self):
        self.assertEqual(self.pan["节气"]["名"], "小暑")
        self.assertEqual(self.pan["节气"]["交气"], "2026-07-07 09:56:57")

    def test_ju(self):
        ju = self.pan["局"]
        self.assertEqual(ju["遁"], "阴")
        self.assertEqual(ju["局数"], 2)
        self.assertEqual(ju["元"], "中元")
        self.assertEqual(ju["符头"], "甲申")

    def test_xunshou(self):
        self.assertEqual(self.pan["旬首"]["名"], "甲子")
        self.assertEqual(self.pan["旬首"]["遁仪"], "戊")

    def test_zhifu_zhishi(self):
        self.assertEqual(self.pan["值符"]["星"], "天芮")
        self.assertEqual(self.pan["值符"]["落宫"], 1)
        self.assertEqual(self.pan["值使"]["门"], "死门")
        self.assertEqual(self.pan["值使"]["落宫"], 6)

    def test_kongwang_yima(self):
        self.assertEqual(self.pan["旬空"]["日柱空"], "午未")
        self.assertEqual(self.pan["旬空"]["时柱空"], "戌亥")
        self.assertEqual(self.pan["驿马"]["支"], "亥")
        self.assertEqual(self.pan["驿马"]["宫"], 6)
        self.assertIn("时空亡", self.pan["九宫"][6]["标注"])
        self.assertIn("驿马", self.pan["九宫"][6]["标注"])

    def test_no_fuyin_fanyin(self):
        self.assertEqual(self.pan["星steps"], 3)
        self.assertFalse(self.pan["伏吟"])
        self.assertFalse(self.pan["反吟"])

    def test_dipan(self):
        expect = {1: "己", 2: "戊", 3: "乙", 4: "丙", 5: "丁",
                  6: "癸", 7: "壬", 8: "辛", 9: "庚"}
        for gong, gan in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["地盘干"], gan,
                             f"宫{gong}地盘干")

    def test_tianpan_stars(self):
        expect = {1: ["天芮", "天禽"], 2: ["天冲"], 3: ["天心"], 4: ["天蓬"],
                  6: ["天英"], 7: ["天辅"], 8: ["天柱"], 9: ["天任"]}
        for gong, stars in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["天盘星"], stars,
                             f"宫{gong}天盘星")

    def test_tianpan_gans(self):
        # 芮禽同宫带双干：芮宫地盘干戊 + 中五寄干丁
        self.assertEqual(self.pan["九宫"][1]["天盘干"], ["戊", "丁"])
        expect = {2: ["乙"], 3: ["癸"], 4: ["己"], 6: ["庚"],
                  7: ["丙"], 8: ["壬"], 9: ["辛"]}
        for gong, gans in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["天盘干"], gans,
                             f"宫{gong}天盘干")

    def test_doors(self):
        expect = {1: "惊门", 2: "杜门", 3: "休门", 4: "生门",
                  6: "死门", 7: "景门", 8: "开门", 9: "伤门"}
        for gong, door in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["门"], door, f"宫{gong}门")

    def test_shens(self):
        expect = {1: "值符", 2: "六合", 3: "九地", 4: "玄武",
                  6: "螣蛇", 7: "太阴", 8: "九天", 9: "白虎"}
        for gong, shen in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["神"], shen, f"宫{gong}神")

    def test_zhong5(self):
        g5 = self.pan["九宫"][5]
        self.assertEqual(g5["地盘干"], "丁")
        self.assertEqual(g5["天盘星"], [])
        self.assertIsNone(g5["门"])
        self.assertIsNone(g5["神"])


class TestGoldenCaseB(unittest.TestCase):
    """黄金用例 B：2026-01-01 12:00，阳遁四局下元。
    三重边界：天禽入中、值使从真实宫数 5 起数、全盘星反吟。"""

    @classmethod
    def setUpClass(cls):
        cls.pan = qimen.build_pan(2026, 1, 1, 12, 0)

    def test_pillars(self):
        p = self.pan["四柱"]
        self.assertEqual(p["年柱"], "乙巳")
        self.assertEqual(p["月柱"], "戊子")
        self.assertEqual(p["日柱"], "乙亥")
        self.assertEqual(p["时柱"], "壬午")

    def test_ju(self):
        ju = self.pan["局"]
        self.assertEqual(self.pan["节气"]["名"], "冬至")
        self.assertEqual(self.pan["节气"]["交气"], "2025-12-21 23:03:05")
        self.assertEqual((ju["遁"], ju["局数"], ju["元"]), ("阳", 4, "下元"))
        self.assertEqual(ju["符头"], "甲戌")

    def test_xunshou_ru_zhong(self):
        # 旬首甲戌遁己，己落中五宫：值符=天禽（随芮）、值使=死门
        self.assertEqual(self.pan["旬首"]["名"], "甲戌")
        self.assertEqual(self.pan["旬首"]["遁仪"], "己")
        self.assertEqual(self.pan["九宫"][5]["地盘干"], "己")
        self.assertEqual(self.pan["值符"]["星"], "天禽")
        self.assertEqual(self.pan["值使"]["门"], "死门")

    def test_zhishi_counts_from_gong5(self):
        # 关键断言：值使飞宫从真实宫数 5 起数（壬 n=9 → ((5-1+8)%9)+1=4）。
        # 若误从寄宫坤 2 起数会得坎 1，此为已证伪的少数派数法。
        self.assertEqual(self.pan["值使"]["落宫"], 4)
        self.assertEqual(self.pan["值使"]["落宫原始"], 4)

    def test_fanyin(self):
        # 芮禽自坤 2 落对冲艮 8，steps=4，全盘星反吟
        self.assertEqual(self.pan["星steps"], 4)
        self.assertTrue(self.pan["反吟"])
        self.assertFalse(self.pan["伏吟"])
        self.assertEqual(self.pan["值符"]["落宫"], 8)

    def test_dipan(self):
        expect = {1: "丁", 2: "丙", 3: "乙", 4: "戊", 5: "己",
                  6: "庚", 7: "辛", 8: "壬", 9: "癸"}
        for gong, gan in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["地盘干"], gan,
                             f"宫{gong}地盘干")

    def test_tianpan_stars(self):
        expect = {1: ["天英"], 2: ["天任"], 3: ["天柱"], 4: ["天心"],
                  6: ["天辅"], 7: ["天冲"], 8: ["天芮", "天禽"], 9: ["天蓬"]}
        for gong, stars in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["天盘星"], stars,
                             f"宫{gong}天盘星")

    def test_tianpan_gans(self):
        # 艮 8 芮禽同宫：芮宫地盘干丙 + 中五寄干己
        self.assertEqual(self.pan["九宫"][8]["天盘干"], ["丙", "己"])
        expect = {1: ["癸"], 2: ["壬"], 3: ["辛"], 4: ["庚"],
                  6: ["戊"], 7: ["乙"], 9: ["丁"]}
        for gong, gans in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["天盘干"], gans,
                             f"宫{gong}天盘干")

    def test_doors(self):
        expect = {1: "伤门", 2: "开门", 3: "景门", 4: "死门",
                  6: "生门", 7: "休门", 8: "杜门", 9: "惊门"}
        for gong, door in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["门"], door, f"宫{gong}门")

    def test_shens(self):
        expect = {1: "九天", 2: "白虎", 3: "螣蛇", 4: "太阴",
                  6: "九地", 7: "玄武", 8: "值符", 9: "六合"}
        for gong, shen in expect.items():
            self.assertEqual(self.pan["九宫"][gong]["神"], shen, f"宫{gong}神")

    def test_kongwang(self):
        # 乙亥日、壬午时同属甲戌旬，空申酉，坤2兑7标空
        self.assertEqual(self.pan["旬空"]["日柱空"], "申酉")
        self.assertEqual(self.pan["旬空"]["时柱空"], "申酉")
        self.assertIn("时空亡", self.pan["九宫"][2]["标注"])
        self.assertIn("时空亡", self.pan["九宫"][7]["标注"])


class TestDingJuBoundary(unittest.TestCase):
    """定局边界：交气时刻粒度坑、23 点换日、拆补节气内不混局。"""

    def test_jieqi_exact_time(self):
        # 2025-12-21 冬至 23:03:05 才交气：当天 10:00 仍属大雪阴遁四局。
        # 防 lunar_python getPrevJieQi 日粒度坑（交气当日全天返回新节气）。
        pan = qimen.build_pan(2025, 12, 21, 10, 0)
        self.assertEqual(pan["节气"]["名"], "大雪")
        self.assertEqual((pan["局"]["遁"], pan["局"]["局数"]), ("阴", 4))

    def test_jieqi_after_exact_time(self):
        # 同日 23:30 已过交气，进冬至阳遁
        pan = qimen.build_pan(2025, 12, 21, 23, 30)
        self.assertEqual(pan["节气"]["名"], "冬至")
        self.assertEqual(pan["局"]["遁"], "阳")

    def test_zi_sect1_default(self):
        # 23 点换日（默认）：2025-12-20 23:30 日柱甲子 → 大雪上元阴遁四局
        pan = qimen.build_pan(2025, 12, 20, 23, 30)
        self.assertEqual(pan["四柱"]["日柱"], "甲子")
        self.assertEqual((pan["局"]["局数"], pan["局"]["元"]), (4, "上元"))

    def test_zi_sect2_optional(self):
        # 夜子时不换日：同一时刻日柱癸亥 → 大雪下元阴遁一局，局数直接不同
        pan = qimen.build_pan(2025, 12, 20, 23, 30, zi_sect=2)
        self.assertEqual(pan["四柱"]["日柱"], "癸亥")
        self.assertEqual((pan["局"]["局数"], pan["局"]["元"]), (1, "下元"))

    def test_chaibu_no_mixing(self):
        # 拆补法：2026-06-21 10:00 夏至未交气，仍用芒种阳遁六局上元
        pan = qimen.build_pan(2026, 6, 21, 10, 0)
        self.assertEqual(pan["节气"]["名"], "芒种")
        self.assertEqual((pan["局"]["遁"], pan["局"]["局数"], pan["局"]["元"]),
                         ("阳", 6, "上元"))

    def test_sanyuan_futou_formula(self):
        # 2004-09-01 癸未日：符头己卯（上元），处暑 → 阴遁一局上元。
        # 反例锚点：看当日日支（未=下元符头支）会错判，必须回溯符头。
        dun, ju, yuan, futou = qimen.ding_ju("处暑", "癸未")
        self.assertEqual((dun, ju, yuan, futou), ("阴", 1, "上元", "己卯"))


class TestJuTable(unittest.TestCase):
    def test_table_complete(self):
        self.assertEqual(len(qimen.JU_TABLE), 24)
        yang = [k for k, v in qimen.JU_TABLE.items() if v[0] == "阳"]
        self.assertEqual(len(yang), 12)

    def test_spot_values(self):
        # 歌诀锚点：冬至一七四、大雪四七一、夏至九三六、芒种六三九
        self.assertEqual(qimen.JU_TABLE["冬至"], ("阳", (1, 7, 4)))
        self.assertEqual(qimen.JU_TABLE["大雪"], ("阴", (4, 7, 1)))
        self.assertEqual(qimen.JU_TABLE["夏至"], ("阴", (9, 3, 6)))
        self.assertEqual(qimen.JU_TABLE["芒种"], ("阳", (6, 3, 9)))


class TestDiPan(unittest.TestCase):
    def test_yang1(self):
        # 阳遁一局：戊落坎1顺布，1戊2己3庚4辛5壬6癸7丁8丙9乙
        pan = qimen.di_pan("阳", 1)
        self.assertEqual(pan, {1: "戊", 2: "己", 3: "庚", 4: "辛", 5: "壬",
                               6: "癸", 7: "丁", 8: "丙", 9: "乙"})

    def test_yin9(self):
        # 阴遁九局：戊落离9逆布
        pan = qimen.di_pan("阴", 9)
        self.assertEqual(pan, {9: "戊", 8: "己", 7: "庚", 6: "辛", 5: "壬",
                               4: "癸", 3: "丁", 2: "丙", 1: "乙"})

    def test_yin2(self):
        # 阴遁二局（黄金用例 A 的地盘）
        pan = qimen.di_pan("阴", 2)
        self.assertEqual(pan, {2: "戊", 1: "己", 9: "庚", 8: "辛", 7: "壬",
                               6: "癸", 5: "丁", 4: "丙", 3: "乙"})


class TestXunShou(unittest.TestCase):
    def test_six_xun(self):
        # 甲子戊 甲戌己 甲申庚 甲午辛 甲辰壬 甲寅癸，各取一个代表时柱
        cases = [("己巳", "甲子", "戊"), ("壬午", "甲戌", "己"),
                 ("乙酉", "甲申", "庚"), ("丙申", "甲午", "辛"),
                 ("戊申", "甲辰", "壬"), ("丁巳", "甲寅", "癸")]
        for gz, name, yi in cases:
            self.assertEqual(qimen.xun_shou(gz), (name, yi), gz)


class TestJiaShiFuYin(unittest.TestCase):
    def test_jia_hour_all_fuyin(self):
        # 六甲之时门星符皆伏吟：2026-12-08 12:00 阴遁7局甲午时，
        # 值符天辅留巽4、值使杜门留巽4（环序固定顺时针的关键佐证）
        pan = qimen.build_pan(2026, 12, 8, 12, 0)
        self.assertEqual(pan["四柱"]["时柱"], "甲午")
        self.assertEqual((pan["局"]["遁"], pan["局"]["局数"]), ("阴", 7))
        self.assertEqual(pan["值符"]["星"], "天辅")
        self.assertEqual(pan["值符"]["落宫"], 4)
        self.assertEqual(pan["值使"]["落宫"], 4)
        self.assertTrue(pan["伏吟"])
        self.assertEqual(pan["星steps"], 0)
        self.assertEqual(pan["门steps"], 0)


class TestXunKongYima(unittest.TestCase):
    def test_xun_kong(self):
        self.assertEqual(qimen._xun_kong("甲子"), "戌亥")
        self.assertEqual(qimen._xun_kong("乙亥"), "申酉")
        self.assertEqual(qimen._xun_kong("甲申"), "午未")
        self.assertEqual(qimen._xun_kong("癸亥"), "子丑")

    def test_yima_four_wei(self):
        # 驿马只落四维宫：寅8 申2 亥6 巳4
        for zhi, ma in [("子", "寅"), ("午", "申"), ("酉", "亥"), ("卯", "巳")]:
            self.assertEqual(qimen.YIMA[zhi], ma)
        self.assertEqual({qimen.ZHI_GONG[m] for m in "寅申亥巳"}, {8, 2, 6, 4})


class TestZhiRun(unittest.TestCase):
    """置闰法定局（超神接气·符头分类法）。
    oracle=元亨利贞在线置闰排盘实测（qimenpaipan 有五类缺陷只可借思路，
    kinqimen 置闰分支有 bug，黄金值一律以元亨利贞为准，详见 references/21）。"""

    BATTERY = [
        # (公历日期, 期望遁, 期望局数)：35 项元亨利贞实测电池
        ("2004-09-01", "阴", 9), ("2025-12-21", "阳", 1), ("2026-06-21", "阴", 9),
        ("2024-06-07", "阳", 3), ("2024-06-15", "阴", 9), ("2024-11-30", "阴", 4),
        ("2024-12-10", "阴", 1), ("2024-12-15", "阴", 4), ("2024-12-23", "阴", 1),
        ("2024-12-27", "阳", 1), ("2023-12-25", "阳", 7), ("2025-06-11", "阳", 6),
        ("2026-03-15", "阳", 7), ("2025-08-08", "阴", 2),
        ("2025-12-06", "阴", 4), ("2019-12-10", "阴", 4), ("2016-06-15", "阳", 6),
        ("2016-06-23", "阳", 9), ("2016-06-27", "阴", 9), ("2020-06-10", "阳", 3),
        ("2022-12-10", "阴", 4), ("2018-12-15", "阴", 4), ("2018-12-25", "阴", 1),
        ("2013-06-15", "阳", 6), ("2024-09-17", "阴", 1), ("2024-10-02", "阴", 9),
        ("2024-10-17", "阴", 8), ("2024-11-01", "阴", 9), ("2024-11-21", "阴", 2),
        ("2022-12-22", "阳", 1), ("2014-06-21", "阳", 9), ("2010-06-15", "阳", 6),
        ("2010-12-15", "阴", 7), ("2013-12-15", "阴", 7), ("2012-12-18", "阳", 1),
    ]

    def test_golden_battery(self):
        for ds, edun, eju in self.BATTERY:
            y, m, d = map(int, ds.split("-"))
            p = qimen.build_pan(y, m, d, 12, 0, ju_fa="zhirun")
            self.assertEqual((p["局"]["遁"], p["局"]["局数"]), (edun, eju), ds)

    def test_leap_min_flip(self):
        # 两派阈值分歧窗口：2010 夏至 diff=8。派8（默认）闰芒种得阳6，
        # 派9（古籍）不闰进夏至得阴9，连阴阳遁都翻转。
        p8 = qimen.build_pan(2010, 6, 15, 10, 0, ju_fa="zhirun")
        self.assertEqual((p8["局"]["遁"], p8["局"]["局数"]), ("阳", 6))
        self.assertIn("闰芒种", p8["局"]["置闰状态"])
        p9 = qimen.build_pan(2010, 6, 15, 10, 0, ju_fa="zhirun", leap_min=9)
        self.assertEqual((p9["局"]["遁"], p9["局"]["局数"]), ("阴", 9))
        self.assertIn("超神8天", p9["局"]["置闰状态"])

    def test_status_labels(self):
        # 正授：2025-12-21 甲子日恰为冬至交气日符头
        p = qimen.build_pan(2025, 12, 21, 10, 0, ju_fa="zhirun")
        self.assertEqual(p["局"]["置闰状态"], "正授")
        self.assertEqual(p["局"]["节气归属"], "冬至")
        # 置闰重复段：2024-12-15 闰大雪上元
        p = qimen.build_pan(2024, 12, 15, 12, 0, ju_fa="zhirun")
        self.assertIn("闰大雪", p["局"]["置闰状态"])
        # 接气：2024-12-27 冬至上元（符头 12-26 甲子在交气 12-21 之后）
        p = qimen.build_pan(2024, 12, 27, 12, 0, ju_fa="zhirun")
        self.assertIn("接气", p["局"]["置闰状态"])
        self.assertEqual(p["局"]["节气归属"], "冬至")

    def test_no_leap_boundary(self):
        # diff=7 反例：2027 夏至不闰，仍超神进夏至
        p = qimen.build_pan(2027, 6, 18, 12, 0, ju_fa="zhirun")
        self.assertEqual((p["局"]["遁"], p["局"]["局数"]), ("阴", 9))
        self.assertIn("超神", p["局"]["置闰状态"])

    def test_midnight_convention(self):
        # 元亨利贞为午夜换日口径：2024-02-29 23:30 对拍须 zi_sect=2（日柱癸亥→阳3）
        p = qimen.build_pan(2024, 2, 29, 23, 30, zi_sect=2, ju_fa="zhirun")
        self.assertEqual(p["四柱"]["日柱"], "癸亥")
        self.assertEqual((p["局"]["遁"], p["局"]["局数"]), ("阳", 3))

    def test_chaibu_zhirun_disagree(self):
        # 两法分歧锚点：2004-09-01 拆补=阴1（处暑上元），置闰=阴9（超神进白露）
        pc = qimen.build_pan(2004, 9, 1, 10, 0)
        pz = qimen.build_pan(2004, 9, 1, 10, 0, ju_fa="zhirun")
        self.assertEqual((pc["局"]["遁"], pc["局"]["局数"]), ("阴", 1))
        self.assertEqual((pz["局"]["遁"], pz["局"]["局数"]), ("阴", 9))


class TestDuanJu(unittest.TestCase):
    """断局标注层：十干克应/四害/星旺衰/格局（表与判定条件双源核验，见 references/22）。"""

    @classmethod
    def setUpClass(cls):
        cls.a = qimen.build_pan(2026, 7, 9, 10, 30)   # 黄金用例 A
        cls.b = qimen.build_pan(2026, 1, 1, 12, 0)    # 黄金用例 B

    def test_keying_case_a(self):
        # 逐宫克应（天盘干+地盘干查表，取芮禽宫主干）
        expect = {1: "贵人入狱", 2: "利阴害阳", 3: "华盖逢星", 4: "火悖地户",
                  6: "大格", 7: "火入天罗", 8: "腾蛇相缠", 9: "白虎出力"}
        for gong, name in expect.items():
            self.assertEqual(self.a["九宫"][gong]["克应"], name, f"宫{gong}")

    def test_keying_case_b(self):
        # 宫9 天盘丁+地盘癸=朱雀投江（腾蛇夭矫是反向的癸+丁，勿混）
        expect = {2: "水蛇入火", 4: "太白伏宫", 6: "值符飞宫", 9: "朱雀投江"}
        for gong, name in expect.items():
            self.assertEqual(self.b["九宫"][gong]["克应"], name, f"宫{gong}")

    def test_sihai_marks(self):
        # 击刑：A 盘天盘辛落离9（午自刑）
        self.assertIn("击刑", self.a["九宫"][9]["标注"])
        # 门迫：A 盘杜门（木）落坤2（土）、景门（火）落兑7（金）
        self.assertIn("门迫", self.a["九宫"][2]["标注"])
        self.assertIn("门迫", self.a["九宫"][7]["标注"])
        # 门制：A 盘生门（土）落巽4（木）
        self.assertIn("门制", self.a["九宫"][4]["标注"])

    def test_star_wangshuai(self):
        # A 盘月支未（土）：天英（火）生土=旺；天蓬（水）被土克=囚
        self.assertEqual(self.a["九宫"][6]["星旺衰"], "旺")
        self.assertEqual(self.a["九宫"][4]["星旺衰"], "囚")

    def test_rumu(self):
        # B 盘天盘戊落乾6 = 入墓（乙丙戊墓乾）
        self.assertIn("入墓", self.b["九宫"][6]["标注"])

    def test_patterns_tiandun(self):
        # 2026-03-01 15:00：离9 生门+天盘丙+地盘丁=天遁，且丙落离9=三奇升殿
        p = qimen.build_pan(2026, 3, 1, 15, 0)
        self.assertTrue(any(x.startswith("天遁") for x in p["格局"]), p["格局"])
        self.assertTrue(any("三奇升殿·丙" in x for x in p["格局"]))

    def test_patterns_yunv_wubuyu(self):
        # 2026-03-01 11:00：值使落离9地盘丁=玉女守门；甲戌日庚午时=五不遇时
        p = qimen.build_pan(2026, 3, 1, 11, 0)
        self.assertTrue(any(x.startswith("玉女守门") for x in p["格局"]))
        self.assertTrue(p["五不遇时"])

    def test_patterns_sanqi_deshi(self):
        # 2026-03-01 03:00：巽4 天盘乙+地盘己=三奇得使
        p = qimen.build_pan(2026, 3, 1, 3, 0)
        self.assertTrue(any("三奇得使·乙加己" in x for x in p["格局"]))

    def test_geng_ge(self):
        # 2026-03-07 05:00：天盘庚+地盘日干=伏干格（兼日格）
        p = qimen.build_pan(2026, 3, 7, 5, 0)
        self.assertTrue(any(x.startswith("伏干格") for x in p["格局"]))

    def test_keying_table_complete(self):
        # 81 组克应表完备：9 天盘干 × 9 地盘干
        self.assertEqual(len(qimen.KEYING), 9)
        for tg, row in qimen.KEYING.items():
            self.assertEqual(len(row), 9, tg)


class TestValidation(unittest.TestCase):
    """非法输入须干净报错（非零退出、无 traceback）。"""

    def _run(self, *args):
        return subprocess.run([sys.executable, QIMEN_PY, *args],
                              capture_output=True, text=True)

    def test_invalid_date(self):
        r = self._run("2026", "2", "30", "12")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("非法日期时间", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_year_out_of_range(self):
        r = self._run("1500", "6", "1", "12")
        self.assertNotEqual(r.returncode, 0)
        self.assertIn("年份超出支持范围", r.stdout + r.stderr)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_invalid_hour(self):
        r = self._run("2026", "6", "1", "25")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stdout + r.stderr)

    def test_invalid_zi_sect(self):
        r = self._run("2026", "6", "1", "12", "--zi-sect", "3")
        self.assertNotEqual(r.returncode, 0)
        self.assertNotIn("Traceback", r.stdout + r.stderr)


class TestCli(unittest.TestCase):
    def _run(self, *args):
        return subprocess.run([sys.executable, QIMEN_PY, *args],
                              capture_output=True, text=True)

    def test_text_output(self):
        r = self._run("2026", "7", "9", "10", "30")
        self.assertEqual(r.returncode, 0)
        self.assertIn("阴遁2局", r.stdout)
        self.assertIn("值符：天芮", r.stdout)

    def test_json_output(self):
        r = self._run("2026", "1", "1", "12", "0", "--json")
        self.assertEqual(r.returncode, 0)
        pan = json.loads(r.stdout)
        self.assertEqual(pan["局"]["局数"], 4)
        self.assertEqual(pan["九宫"]["8"]["天盘星"], ["天芮", "天禽"])

    def test_version(self):
        r = self._run("--version")
        self.assertEqual(r.returncode, 0)
        self.assertIn("qimen.py", r.stdout)


if __name__ == "__main__":
    unittest.main()
