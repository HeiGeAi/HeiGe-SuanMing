"""Run the commands printed in the teaching cases, not hand-copied test inputs."""
import html
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]


class TestDocumentedExamples(unittest.TestCase):
    def test_case_chart_blocks_match_their_printed_commands(self):
        cases = sorted((ROOT / 'cases').glob('[0-9]*.md'))
        self.assertEqual(4, len(cases))
        for path in cases:
            with self.subTest(case=path.name):
                text = path.read_text(encoding='utf-8')
                command = re.search(r'`python3 ../scripts/paipan.py ([^`]+)`', text)
                self.assertIsNotNone(command, 'The case needs a reproducible command.')
                chart_blocks = [block for block in re.findall(r'```\n([\s\S]*?)```', text)
                                if '八字命盘' in block]
                self.assertEqual(1, len(chart_blocks))
                result = subprocess.run(
                    [sys.executable, str(ROOT / 'scripts' / 'paipan.py'),
                     *shlex.split(command.group(1))],
                    capture_output=True, text=True,
                    env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
                )
                self.assertEqual(0, result.returncode, result.stderr)
                self.assertEqual(chart_blocks[0].strip('\n'), result.stdout.strip('\n'))

    @classmethod
    def setUpClass(cls):
        sys.path.insert(0, str(ROOT / 'scripts'))
        import paipan
        cls.engine = paipan
        cls.case_data = []
        for path in sorted((ROOT / 'cases').glob('[0-9]*.md')):
            text = path.read_text(encoding='utf-8')
            args = shlex.split(re.search(r'`python3 ../scripts/paipan.py ([^`]+)`', text).group(1))
            result = subprocess.run([sys.executable, str(ROOT / 'scripts' / 'paipan.py'),
                                     *args, '--json'], capture_output=True, text=True, check=True)
            # Deliberately exclude the already-tested chart block: assertions below
            # inspect the visible teaching prose that readers actually learn from.
            prose = re.sub(r'```[\s\S]*?```', '', text).replace('**', '')
            cls.case_data.append((path.name, prose, json.loads(result.stdout)))

    def test_case_prose_birth_and_luck_numbers(self):
        for name, prose, chart in self.case_data:
            with self.subTest(case=name, fact='birth'):
                birth = re.search(r'虚拟生辰：公历 (\d+) 年 (\d+) 月 (\d+) 日 (\d+) 时 (\d+) 分，([男女])', prose)
                self.assertIsNotNone(birth)
                y, mo, d, h, mi = map(int, birth.groups()[:5])
                self.assertEqual(f'{y:04}-{mo:02}-{d:02} {h:02}:{mi:02}', chart['input']['solar'])
                self.assertEqual(birth.group(6), chart['input']['gender'])
                self.assertIn('日主：' + chart['day_master'], prose)
            with self.subTest(case=name, fact='start_age'):
                start = re.search(r'大运(顺排|逆排)，(?:约 )?(\d+) 岁起', prose)
                self.assertIsNotNone(start)
                self.assertEqual((chart['yun_direction'], chart['start_age']),
                                 (start.group(1), int(start.group(2))))
            luck = {row['ganzhi']: row for row in chart['dayun'] if row['ganzhi']}
            for gz, start, end in re.findall(r'([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])（(\d+)-(\d+) 岁）', prose):
                with self.subTest(case=name, luck=gz):
                    self.assertEqual((luck[gz]['start_age'], luck[gz]['end_age']), (int(start), int(end)))
            current = re.search(r'当前 (\d+) 起[、的][^\n]*?([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])[^\n]*?运', prose)
            if current:
                with self.subTest(case=name, fact='current_luck_start'):
                    self.assertEqual(luck[current.group(2)]['start_year'], int(current.group(1)))

    def test_case_prose_stems_hidden_stems_and_lu(self):
        gods = '正财|偏财|正官|七杀|正印|偏印|食神|伤官|比肩|劫财'
        for name, prose, chart in self.case_data:
            day = chart['pillars']['日'][0]
            for gan, god in re.findall(r'([甲乙丙丁戊己庚辛壬癸])[木火土金水]?（?(' + gods + ')', prose):
                with self.subTest(case=name, stem=gan, god=god):
                    self.assertEqual(self.engine.ten_god(day, gan), god)
            for zhi, stems in re.findall(r'([子丑寅卯辰巳午未申酉戌亥])(?:中)?藏([甲乙丙丁戊己庚辛壬癸]+)', prose):
                with self.subTest(case=name, hidden=zhi + stems):
                    self.assertTrue(set(stems) <= set(self.engine.ZHI_CANGGAN[zhi]))
            for zhi in re.findall(r'(?:坐禄于|禄在)([子丑寅卯辰巳午申酉戌亥未])', prose):
                with self.subTest(case=name, lu=zhi):
                    self.assertEqual(self.engine.LUSHEN[day], zhi)
            for zhi, wx in re.findall(r'([子丑寅卯辰巳午未申酉戌亥])中含([木火土金水])气', prose):
                with self.subTest(case=name, hidden_element=zhi + wx):
                    self.assertIn(wx, [self.engine.GAN_WUXING[g] for g in self.engine.ZHI_CANGGAN[zhi]])

    def test_case_prose_explicit_absence_and_percentage(self):
        for name, prose, chart in self.case_data:
            for wx in re.findall(r'([木火土金水])原局全无', prose):
                with self.subTest(case=name, absent=wx):
                    self.assertEqual(0, chart['wuxing_score'][wx])
            for number in re.findall(r'异党近([一二三四五六七八九十])成', prose):
                with self.subTest(case=name, opposing_fraction=number):
                    score = chart['wuxing_score']; day_wx = chart['day_master'][1]
                    support = score[day_wx] + sum(value for wx, value in score.items()
                        if self.engine.WUXING_SHENG[wx] == day_wx)
                    fraction = 1 - support / sum(score.values())
                    self.assertLess(abs(fraction - ('一二三四五六七八九十'.index(number) + 1) / 10), 0.05)

    def test_case_prose_life_stages_and_years(self):
        for name, prose, chart in self.case_data:
            with self.subTest(case=name):
                start_date = re.search(r'大运(?:顺排|逆排)，\d+ 岁起（虚岁，([0-9-]+)）', prose)
                self.assertIsNotNone(start_date)
                self.assertEqual(chart['start_solar'], start_date.group(1))
            day = chart['pillars']['日'][0]
            for zhi, stage in re.findall(r'坐([子丑寅卯辰巳午未申酉戌亥])为(长生|沐浴|冠带|临官|帝旺|衰|病|死|墓|绝|胎|养)', prose):
                with self.subTest(case=name, stage=zhi):
                    self.assertEqual(self.engine._dishi_of(day, zhi), stage)
            luck = {row['ganzhi']: row for row in chart['dayun'] if row['ganzhi']}
            for paragraph in prose.split('\n'):
                match = re.match(r'- ([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])（', paragraph)
                stage = re.search(r'星运逢「([^」]+)」', paragraph)
                if match and stage:
                    with self.subTest(case=name, luck_stage=match.group(1)):
                        self.assertEqual(luck[match.group(1)]['dishi'], stage.group(1))
            years = {row['year']: row['ganzhi'] for row in chart['liunian']}
            for year, gz in re.findall(r'(20\d{2}) ([甲乙丙丁戊己庚辛壬癸][子丑寅卯辰巳午未申酉戌亥])', prose):
                if int(year) in years:
                    with self.subTest(case=name, year=year):
                        self.assertEqual(years[int(year)], gz)

    def test_case_fire_and_water_prose_includes_hidden_stems(self):
        data = {name: (prose, chart) for name, prose, chart in self.case_data}
        prose, chart = data['03_tiaohou.md']
        fire = re.search(r'原局火仅 ([0-9.]+)', prose)
        self.assertIsNotNone(fire)
        self.assertEqual(chart['wuxing_score']['火'], float(fire.group(1)))
        self.assertGreater(chart['wuxing_score']['火'], 0)
        self.assertIn('丁', chart['zhi_canggan']['日'])
        for path in ['cases/README.md', 'references/00_gainian_suoyin.md',
                     'references/16_secai_fushi.md']:
            with self.subTest(reference=path):
                text = (ROOT / path).read_text(encoding='utf-8')
                self.assertIn('微火', text)
                self.assertNotRegex(text, r'乙木[^\n]*(?:独缺火|无火)')
        prose, chart = data['02_shenruo_yinbi.md']
        water = re.search(r'水虽不透，藏干计权为 ([0-9.]+)', prose)
        self.assertIsNotNone(water)
        self.assertEqual(chart['wuxing_score']['水'], float(water.group(1)))

    def test_candidate_case_discloses_missing_water_combination(self):
        prose, chart = next((prose, chart) for name, prose, chart in self.case_data
                            if name == '04_conge.md')
        branches = {pillar[1] for pillar in chart['pillars'].values()}
        self.assertFalse(set('亥子丑') <= branches)
        self.assertFalse(set('申子辰') <= branches)
        self.assertIn('不成亥子丑三会', prose)
        self.assertIn('不成申子辰三合', prose)
        self.assertIn('候选', prose.splitlines()[0])
        self.assertIn('返回身旺常格复核', prose)
        for section in ['五、', '八、', '九、']:
            self.assertRegex(prose, r'## ' + section + r'[^\n]*候选分支')

        # 2033 crosses a luck-cycle boundary and adds the branch missing from
        # the natal water meeting; it cannot inherit the previous two years' summary.
        new_luck = next(row for row in chart['dayun'] if row['ganzhi'] == '乙巳')
        self.assertIn(f"{new_luck['start_year']} 年交入乙巳运", prose)
        year = next(row for row in chart['liunian'] if row['year'] == new_luck['start_year'])
        yearly_note = re.search(r'^- ' + str(year['year']) + ' ' + year['ganzhi'] + r'：([^\n]+)',
                               prose, re.MULTILINE)
        self.assertIsNotNone(yearly_note, 'The transition year needs a separate explanation.')
        note = yearly_note.group(1)
        self.assertIn(year['ganzhi'][1] + '藏' + ''.join(self.engine.ZHI_CANGGAN[year['ganzhi'][1]]), note)
        self.assertTrue(set('亥子丑') <= branches | {year['ganzhi'][1]})
        self.assertIn('亥子丑', note)
        self.assertIn(frozenset((new_luck['ganzhi'][1], '亥')), self.engine.ZHI_CHONG)
        self.assertIn('巳亥冲', note)
        self.assertIn('不自动确认成格', note)

    def test_visual_report_facts_match_its_chart(self):
        # The published fictional report says 1986-06-22 at noon, male.
        report = (ROOT / 'examples' / '示例-八字命书.html').read_text(encoding='utf-8')
        result = subprocess.run(
            [sys.executable, str(ROOT / 'scripts' / 'paipan.py'),
             '1986', '6', '22', '12', '--gender', 'male', '--years', '2026', '10', '--json'],
            capture_output=True, text=True,
        )
        self.assertEqual(0, result.returncode, result.stderr)
        chart = json.loads(result.stdout)
        columns = ['年', '月', '日', '时']
        expected = {
            '天干十神': [chart['gan_shen'][c] for c in columns],
            '天干': [chart['pillars'][c][0] for c in columns],
            '地支': [chart['pillars'][c][1] for c in columns],
            '藏干': [''.join(chart['zhi_canggan'][c]) for c in columns],
            '藏干十神': ['·'.join(chart['zhi_shen'][c]) for c in columns],
            '星运': [chart['dishi'][c] for c in columns],
            '纳音': [chart['nayin'][c] for c in columns],
            '旬空': [chart['xunkong'][c] for c in columns],
        }
        table = re.search(r'<tbody>([\s\S]*?)</tbody>', report)
        self.assertIsNotNone(table)
        actual = {}
        for row in re.findall(r'<tr>(.*?)</tr>', table.group(1)):
            cells = [re.sub(r'\s+', '', html.unescape(re.sub(r'<[^>]+>', '', cell)))
                     for cell in re.findall(r'<td[^>]*>(.*?)</td>', row)]
            actual[cells[0]] = cells[1:]
        self.assertEqual(expected, actual)

        # Compare the visible luck-cycle prose, not a hidden metadata copy.
        stages = re.findall(
            r'<span class="gz">([^<]+)</span>(?:(?!<span class="gz">)[\s\S])*?星运逢「([^」]+)」',
            report,
        )
        self.assertTrue(stages, 'The report should retain its explicit life-stage annotation.')
        luck = {row['ganzhi']: row for row in chart['dayun']}
        for ganzhi, stage in stages:
            with self.subTest(luck=ganzhi):
                self.assertEqual(luck[ganzhi]['dishi'], stage)


if __name__ == '__main__':
    unittest.main()
