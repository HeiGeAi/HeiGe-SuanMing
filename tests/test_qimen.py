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
