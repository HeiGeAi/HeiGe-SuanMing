import re
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class TestReleaseContractV1150(unittest.TestCase):
    def test_declared_minimum_dependency_matches_supported_runtime(self):
        requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")
        self.assertRegex(requirements, r"(?m)^lunar_python>=1\.4\.8$")

    def test_version_metadata_matches_engines(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        expected = {
            "version": "1.15.0",
            "engine-version": "1.4.0",
            "meihua-version": "1.1.0",
            "liuyao-version": "1.1.0",
            "ziwei-version": "1.2.0",
            "qimen-version": "1.2.0",
        }
        for key, version in expected.items():
            self.assertIn(f"  {key}: {version}", skill)

        scripts = {
            "paipan.py": "1.4.0",
            "meihua.py": "1.1.0",
            "liuyao.py": "1.1.0",
            "ziwei.py": "1.2.0",
            "qimen.py": "1.2.0",
        }
        for name, version in scripts.items():
            source = (ROOT / "scripts" / name).read_text(encoding="utf-8")
            self.assertIn(f'__version__ = "{version}"', source)

    def test_readme_describes_all_five_engines_and_unknown_hour_cli(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        test_count = unittest.defaultTestLoader.discover(str(ROOT / "tests")).countTestCases()
        self.assertNotIn("一层文本加三个脚本", readme)
        self.assertNotIn("text plus a script", readme)
        for script in ("paipan.py", "meihua.py", "liuyao.py", "ziwei.py", "qimen.py"):
            self.assertIn(f"scripts/{script}", readme)
        self.assertIn("paipan.py 1990 5 15 --gender male", readme)
        self.assertIn(f"`tests/` 共 {test_count} 个测试", readme)
        self.assertIn(f"suite contains {test_count} checks", readme)
        self.assertIn("必需信息：", skill)
        self.assertIn("可选信息：", skill)
        self.assertIn("**出生时间**", skill)
        self.assertIn("当前干支年（按立春分界）与出生年中较晚者开始排 10 年", skill)
        self.assertIn("--date <年> <月> <日> [时] [分]", skill)
        self.assertIn("--china-dst", skill)
        self.assertIn("--partner-china-dst", skill)
        self.assertIn("v1.15.0 结构化输出迁移说明", readme)
        self.assertIn("`六煞` 现只包含", readme)
        self.assertIn("`门伏吟`", readme)

        qimen = (ROOT / "references" / "21_qimen.md").read_text(encoding="utf-8")
        qimen_duanju = (ROOT / "references" / "22_qimen_duanju.md").read_text(encoding="utf-8")
        self.assertIn("scripts/qimen.py` v1.2.0", qimen)
        self.assertIn("scripts/qimen.py` v1.2.0", qimen_duanju)

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
        self.assertIn("排盘引擎 v1.4.0", html)


if __name__ == "__main__":
    unittest.main()
