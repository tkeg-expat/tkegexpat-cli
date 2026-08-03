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


import contextlib
import io
import re

from tkegexpat import cit

_ANSI = re.compile(r"\033\[[0-9;]*m")


def _render(rows, labels, **kwargs):
    """Capture _print_detail_table output as plain (ANSI-stripped) lines."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        cit._print_detail_table(rows, labels, **kwargs)
    return [_ANSI.sub("", l) for l in buf.getvalue().splitlines()]


class PrintDetailTableCharWrap(unittest.TestCase):
    def setUp(self):
        # Pin the terminal width: os.get_terminal_size() reads the real fd 1 and
        # is not affected by redirect_stdout, so it is not deterministic here.
        self._real_term_width = cit._term_width
        cit._term_width = lambda: 80

    def tearDown(self):
        cit._term_width = self._real_term_width

    def test_char_wrap_column_never_overflows(self):
        # 64 chars = 128 display columns, no spaces. At a pinned 80-column
        # terminal the Text column tops out at 70, so this must wrap to 2 lines.
        cell = "公司注册服务协定" * 8
        lines = _render([{"#": "1", "Text": cell}], ["#", "Text"], char_wrap=["Text"])
        body = lines[2:]  # skip header + separator
        self.assertEqual(len(body), 2)
        for line in lines:
            self.assertLessEqual(display_width(line), 80)

    def test_default_behaviour_is_unchanged(self):
        # Without char_wrap the spaceless cell stays on one 136-column line that
        # runs past the table border, exactly as it does today. This is the
        # regression guard for every existing table.
        cell = "公司注册服务协定" * 8
        lines = _render([{"#": "1", "Text": cell}], ["#", "Text"])
        body = lines[2:]
        self.assertEqual(len(body), 1)
        self.assertIn(cell, body[0])
        self.assertGreater(display_width(body[0]), 80)

    def test_space_separated_column_still_wraps_on_words(self):
        lines = _render(
            [{"#": "1", "Text": "alpha beta gamma delta epsilon"}],
            ["#", "Text"],
        )
        body = "\n".join(lines[2:])
        self.assertIn("alpha", body)
        self.assertNotIn("alph\na", body)


if __name__ == "__main__":
    unittest.main()
