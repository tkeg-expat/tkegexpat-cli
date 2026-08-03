# tests/test_log.py
import contextlib
import io
import unittest

from tkegexpat import cit, log


INVOICE_ENTRIES = [
    {   # deliberately out of chronological order, as Bubble returns them
        "_id": "e3", "date-logged": "2025-06-24T03:11:19.845Z",
        "invoice-status": "VOIDED", "text": "===== INVOICE VOID 帳單已作廢 =====",
        "Created By": "u1",
    },
    {
        "_id": "e1", "date-logged": "2025-06-19T09:32:45.859Z",
        "invoice-status": "QUOTE", "text": "===== QUOTE ISSUED 報價單已簽發 =====",
        "file-s3": "f1", "Created By": "u1",
    },
    {
        "_id": "e2", "date-logged": "2025-06-19T09:35:12.908Z",
        "invoice-status": "INVOICE", "text": "===== INVOICE ISSUED 帳單已簽發 =====",
        "file-s3": "f2", "Created By": "u2",
    },
]

CONTRACT_ENTRIES = [
    {"_id": "c2", "record-date": "2025-06-02T12:12:09.737Z", "status": "Live",
     "text": "Contract signed. 協約已簽署。", "Created By": "u1"},
    {"_id": "c1", "record-date": "2025-05-31T21:41:45.270Z", "status": "Needs Update",
     "text": "", "Created By": "u2"},
]


class LogBase(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._real_api_list = log.api_list
        self._real_author = log._author
        self._real_term_width = cit._term_width
        # Pin the width: os.get_terminal_size() reads the real fd 1 regardless of
        # redirect_stdout, so a narrow window would wrap "Needs Update" and break
        # the assertions below.
        cit._term_width = lambda: 200
        log._author = lambda uid: {"u1": "Zhang Shuer", "u2": "Tony Chu"}.get(uid, "-")
        log._ctx.update(kind=None, id=None, label=None)

    def tearDown(self):
        log.api_list = self._real_api_list
        log._author = self._real_author
        cit._term_width = self._real_term_width
        log._user_cache.clear()

    def stub(self, rows):
        def _api_list(typename, constraints=None, **kwargs):
            self.calls.append((typename, constraints))
            return list(rows)
        log.api_list = _api_list

    def run_log(self):
        out, err = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            log.cmd_log([])
        return out.getvalue(), err.getvalue()


class NoContext(LogBase):
    def test_errors_without_a_detail_in_view(self):
        self.stub([])
        out, err = self.run_log()
        self.assertIn("No invoice or contract in view", err)
        self.assertEqual(self.calls, [])


class InvoiceLog(LogBase):
    def setUp(self):
        super().setUp()
        self.stub(INVOICE_ENTRIES)
        log.set_context("invoice", "inv1", "1111111126")

    def test_queries_the_invoice_log_type_by_its_link_field(self):
        self.run_log()
        self.assertEqual(self.calls, [(
            "invoice:log",
            [{"key": "invoice", "constraint_type": "equals", "value": "inv1"}],
        )])

    def test_renders_oldest_first(self):
        out, _ = self.run_log()
        self.assertLess(out.index("QUOTE"), out.index("VOIDED"))
        self.assertLess(out.index("INVOICE ISSUED"), out.index("INVOICE VOID"))

    def test_heading_shows_label_and_count(self):
        out, _ = self.run_log()
        self.assertIn("Invoice Log 1111111126 (3)", out)

    def test_doc_column_marks_entries_with_a_file(self):
        out, _ = self.run_log()
        self.assertIn("Doc", out)
        self.assertEqual(out.count("yes"), 2)

    def test_shows_the_date_and_the_time(self):
        out, _ = self.run_log()
        self.assertIn("2025-06-19 09:32", out)


class ContractLog(LogBase):
    def setUp(self):
        super().setUp()
        self.stub(CONTRACT_ENTRIES)
        log.set_context("contract", "con1", "IE incorporation agreement")

    def test_queries_the_contract_record_type_by_its_link_field(self):
        self.run_log()
        self.assertEqual(self.calls, [(
            "contract:record",
            [{"key": "contract", "constraint_type": "equals", "value": "con1"}],
        )])

    def test_has_no_doc_column(self):
        out, _ = self.run_log()
        self.assertNotIn("Doc", out)

    def test_renders_oldest_first(self):
        out, _ = self.run_log()
        self.assertLess(out.index("Needs Update"), out.index("Live"))

    def test_blank_text_renders_as_dash(self):
        out, _ = self.run_log()
        self.assertIn("Needs Update", out)  # the row survives an empty body


class EdgeCases(LogBase):
    def test_no_entries(self):
        self.stub([])
        log.set_context("invoice", "inv9", "1111111999")
        out, _ = self.run_log()
        self.assertIn("No log entries.", out)

    def test_api_failure_is_reported_without_a_traceback(self):
        def _boom(typename, constraints=None, **kwargs):
            raise RuntimeError("HTTP 500")
        log.api_list = _boom
        log.set_context("contract", "con1", "x")
        out, err = self.run_log()
        self.assertIn("Failed to fetch log", err)
        self.assertIn("HTTP 500", err)

    def test_missing_date_renders_as_dash(self):
        self.stub([{"_id": "e", "invoice-status": "QUOTE", "text": "t", "Created By": "u1"}])
        log.set_context("invoice", "inv1", "x")
        out, _ = self.run_log()
        self.assertIn("QUOTE", out)


if __name__ == "__main__":
    unittest.main()
