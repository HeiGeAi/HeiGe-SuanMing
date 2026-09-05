import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestReleaseContractV1160(unittest.TestCase):
    def test_declared_minimum_dependency_matches_supported_runtime(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertRegex(requirements, r"(?m)^lunar_python==1\.4\.8$")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertIn("Python 3.7 to 3.13", readme)
        self.assertIn("'3.7'", workflow)
        self.assertIn("'3.13'", workflow)

    def test_version_tags_trigger_the_same_ci_matrix(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"(?m)^  push:\n    branches: \[main\]\n    tags: \['v\*'\]$")

    def test_actions_are_pinned_to_immutable_commits(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        self.assertRegex(workflow, r"actions/checkout@[0-9a-f]{40} # v4\.4\.0")
        self.assertRegex(workflow, r"actions/setup-python@[0-9a-f]{40} # v5\.6\.0")

    def test_version_metadata_matches_engines(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        expected = {
            "version": "1.16.0",
            "engine-version": "1.5.0",
            "meihua-version": "1.2.0",
            "liuyao-version": "1.2.0",
            "ziwei-version": "1.3.0",
            "qimen-version": "1.2.1",
        }
        for key, version in expected.items():
            self.assertIn(f"  {key}: {version}", skill)

        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
        self.assertIn("skill-1.16.0", readme)
        self.assertIn("engine-1.5.0", readme)
        self.assertRegex(changelog, r"(?m)^## \[1\.16\.0\] - 2026-09-06$")

        scripts = {
            "paipan.py": "1.5.0",
            "meihua.py": "1.2.0",
            "liuyao.py": "1.2.0",
            "ziwei.py": "1.3.0",
            "qimen.py": "1.2.1",
        }
        for name, version in scripts.items():
            source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn(f'__version__ = "{version}"', source)

    def test_readme_describes_all_five_engines_and_unknown_hour_cli(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        test_count = unittest.defaultTestLoader.discover(str(ROOT / "tests")).countTestCases()
        component_counts = {
            "八字": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_paipan.py").countTestCases(),
            "梅花": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_meihua.py").countTestCases(),
            "六爻": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_liuyao.py").countTestCases(),
            "紫微": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_ziwei.py").countTestCases(),
            "奇门": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_qimen.py").countTestCases(),
            "命例复现": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_documented_examples.py").countTestCases(),
            "发布契约": unittest.defaultTestLoader.discover(str(ROOT / "tests"), pattern="test_release_contract.py").countTestCases(),
        }
        self.assertNotIn("一层文本加三个脚本", readme)
        self.assertNotIn("text plus a script", readme)
        for script in ("paipan.py", "meihua.py", "liuyao.py", "ziwei.py", "qimen.py"):
            self.assertIn(f"scripts/{script}", readme)
        self.assertIn("paipan.py 2000 8 16 --gender female", readme)
        self.assertIn(f"`tests/` 共 {test_count} 个测试", readme)
        self.assertIn(f"suite contains {test_count} checks", readme)
        chinese_counts = " + ".join(f"{name} {count}" for name, count in component_counts.items())
        english_counts = (
            f"Bazi {component_counts['八字']}, Meihua {component_counts['梅花']}, "
            f"Liu Yao {component_counts['六爻']}, Zi Wei Dou Shu {component_counts['紫微']}, "
            f"Qi Men Dun Jia {component_counts['奇门']}, documented examples {component_counts['命例复现']}, "
            f"and release contracts {component_counts['发布契约']}"
        )
        self.assertIn(chinese_counts, readme)
        self.assertIn(english_counts, readme)
        self.assertIn("八字／紫微必需", skill)
        self.assertIn("出生地与记录时区", skill)
        self.assertIn("出生时分及准确程度", skill)
        self.assertIn("当前干支年（按立春分界）与出生年中较晚者开始排 10 年", skill)
        self.assertIn("--date <年> <月> <日> [时] [分]", skill)
        self.assertIn("--china-dst", skill)
        self.assertIn("--partner-china-dst", skill)
        self.assertIn("--partner-lng", skill)
        self.assertIn("--partner-tz", skill)
        self.assertIn("--no-fix-leap", skill)
        self.assertIn("--year-divide", skill)
        self.assertIn("v1.16.0 口径与输入契约说明", readme)
        self.assertIn("源码可用的非商业许可", readme)
        self.assertIn("不是 OSI 定义的开源许可证", readme)
        self.assertNotIn('"开源 + 限定非商业用途"', readme)
        self.assertIn("`六煞` 现只包含", readme)
        self.assertIn("`门伏吟`", readme)

        qimen = (ROOT / "references" / "21_qimen.md").read_text(encoding="utf-8")
        qimen_duanju = (ROOT / "references" / "22_qimen_duanju.md").read_text(encoding="utf-8")
        self.assertIn("scripts/qimen.py` v1.2.1", qimen)
        self.assertIn("scripts/qimen.py` v1.2.1", qimen_duanju)

    def test_visual_report_is_print_safe_and_has_plain_language_boxes(self):
        html = (ROOT / "examples" / "示例-八字命书.html").read_text(encoding="utf-8")
        self.assertIn("@media print", html)
        self.assertRegex(
            html,
            r"@media print[^}]*\{[\s\S]*?body\{[^}]*background:#fff!important;"
            r"color:#111!important;font-size:11pt",
        )
        self.assertEqual(19, len(re.findall(r'<div class="heige-read reveal">', html)))
        self.assertEqual(19, html.count("<span>黑哥解读</span>"))
        self.assertNotIn("IntersectionObserver", html)
        self.assertNotRegex(html, r"(?i)@keyframes\b")
        self.assertNotRegex(html, r"(?i)\banimation(?:-[\w-]+)?\s*:")
        self.assertNotRegex(html, r"(?is)<script\b")
        self.assertNotRegex(
            html,
            r"(?is)\.reveal\s*\{[^}]*(?:opacity\s*:\s*0|visibility\s*:\s*hidden|display\s*:\s*none)",
        )
        self.assertIn("排盘引擎 v1.5.0", html)


if __name__ == "__main__":
    unittest.main()
