# tests/test_wrap_display.py
import unittest

from tkegexpat.i18n import display_width, wrap_display


class WrapDisplay(unittest.TestCase):
    def test_splits_spaceless_cjk_at_display_width(self):
        # 8 chars x 2 display columns = 16 wide; width 6 fits 3 chars per line
        self.assertEqual(
            wrap_display("公司注册服务协定", 6),
            ["公司注", "册服务", "协定"],
        )

    def test_splits_long_url_with_no_break_points(self):
        url = "https://tkegexpat.com/dynamic-project-contract/1748615227236x826011667164261400"
        self.assertEqual(len(url), 79)
        lines = wrap_display(url, 20)
        self.assertEqual(len(lines), 4)
        self.assertTrue(all(display_width(l) <= 20 for l in lines))
        self.assertEqual("".join(lines), url)

    def test_preserves_embedded_newlines_as_blank_lines(self):
        self.assertEqual(wrap_display("a\n\nb", 10), ["a", "", "b"])

    def test_never_exceeds_width_on_mixed_script(self):
        text = "QUOTE ID 報價單編號: 1111111126;"
        for line in wrap_display(text, 20):
            self.assertLessEqual(display_width(line), 20)

    def test_empty_and_dash_render_as_dash(self):
        self.assertEqual(wrap_display("", 10), ["-"])
        self.assertEqual(wrap_display(None, 10), ["-"])
        self.assertEqual(wrap_display("-", 10), ["-"])

    def test_width_smaller_than_a_wide_char_emits_one_char_per_line(self):
        # A 2-column char cannot be split; emit it rather than loop forever.
        self.assertEqual(wrap_display("報價", 1), ["報", "價"])

    def test_oversized_token_does_not_orphan_a_leading_bullet(self):
        # view-content's list rendering depends on this: flushing the line before
        # splitting an oversized token leaves "•" alone on its own line — the
        # exact defect fixed in v0.15.0.
        line = "• 客户及奕资环球双方经过友好协商，本着平等互利、友好合作的意愿达成本协议书"
        self.assertEqual(
            wrap_display(line, 30),
            ["• 客户及奕资环球双方经过友好协", "商，本着平等互利、友好合作的意", "愿达成本协议书"],
        )


if __name__ == "__main__":
    unittest.main()
