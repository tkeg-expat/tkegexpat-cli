# tests/test_employee_entities.py
#
# 2026-10-05 backend rename: entity_crm -> entity_employee, and entity_admin /
# entity_rd / entity_marketing were folded into it (told apart by
# `employee_type`). These tests pin the CLI to that schema.
import contextlib
import io
import unittest

from tkegexpat import cit, entities, entity_dir, project_item, user


CRM = {
    "_id": "1709130786129x113248120930304000", "employee_type": "crm",
    "prime_entity": "p-crm", "tkeg-expat-email": "crm@x", "active": True,
    "single-busy-rate": 14, "total-employee-busy-rate": 3,
    "pending-lead-number": 5, "pending-project-number": 10,
    "available-points": 30775.91,
    "belonging_admin_entity_new": "1791128419997x304312463708560100",
}
RD = {
    "_id": "1791129101485x398977089057885200", "employee_type": "rd",
    "prime_entity": "p-rd", "single-busy-rate": 24.5,
    "pending-project-number": 45, "rd_ongoing_rd_item_number": 4,
    "available-points": 84554.78,
    "belonging_admin_entity_new": "1791128419997x304312463708560100",
}
ADMIN = {
    "_id": "1791128419997x304312463708560100", "employee_type": "admin",
    "prime_entity": "p-admin", "available-points": 32831.58,
}


def _capture(fn, *args):
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        result = fn(*args)
    return result, out.getvalue(), err.getvalue()


class EntityDirBase(unittest.TestCase):
    def setUp(self):
        self.list_calls, self.get_calls, self.cell_calls = [], [], []
        self._saved = {
            name: getattr(entity_dir, name)
            for name in ("api_list", "api_get", "prime_name", "entity_cell", "id_to_abbr", "_user_name")
        }
        self._term_width = cit._term_width
        cit._term_width = lambda: 200
        entity_dir.prime_name = lambda pid: {"p-crm": "Crm Person", "p-rd": "Rd Person", "p-admin": "Admin Person"}.get(pid)
        entity_dir.id_to_abbr = lambda cid: str(cid)
        entity_dir._user_name = lambda uid: "-"

        def _cell(ref, typename):
            self.cell_calls.append((ref, typename))
            return f"Admin Person\n{ref}"
        entity_dir.entity_cell = _cell

    def tearDown(self):
        for name, fn in self._saved.items():
            setattr(entity_dir, name, fn)
        cit._term_width = self._term_width
        entity_dir._last.update(kind=None, records=[])

    def stub_list(self, rows):
        def _api_list(typename, constraints=None, **kwargs):
            self.list_calls.append((typename, constraints))
            return list(rows)
        entity_dir.api_list = _api_list

    def stub_get(self, rec):
        def _api_get(path, *a, **kw):
            self.get_calls.append(path)
            return {"response": rec}
        entity_dir.api_get = _api_get


class EntityDirList(EntityDirBase):
    def test_each_command_lists_entity_employee_by_its_employee_type(self):
        for kind in ("crm", "rd", "admin"):
            self.list_calls.clear()
            self.stub_list([])
            _capture(entity_dir.cmd_entity, kind, [])
            self.assertEqual(self.list_calls, [(
                "entity_employee",
                [{"key": "employee_type", "constraint_type": "equals", "value": kind}],
            )])

    def test_list_heading_and_rows_are_unchanged(self):
        self.stub_list([CRM])
        ok, out, _ = _capture(entity_dir.cmd_entity, "crm", [])
        self.assertTrue(ok)
        self.assertIn("CRM Entities (1)", out)
        self.assertIn("Crm Person", out)


class EntityDirDetail(EntityDirBase):
    def test_detail_reads_entity_employee_by_id(self):
        self.stub_get(CRM)
        _capture(entity_dir.cmd_entity, "crm", [CRM["_id"]])
        self.assertEqual(self.get_calls, [f"/api/1.1/obj/entity_employee/{CRM['_id']}"])

    def test_crm_detail_maps_the_renamed_busy_rate(self):
        self.stub_get(CRM)
        _, out, _ = _capture(entity_dir.cmd_entity, "crm", [CRM["_id"]])
        self.assertIn("CRM Busy Rate", out)
        self.assertIn("14", out)
        self.assertIn("30775.91", out)

    def test_rd_detail_maps_the_folded_rd_fields(self):
        self.stub_get(RD)
        _, out, _ = _capture(entity_dir.cmd_entity, "rd", [RD["_id"]])
        self.assertIn("RD Busy Rate", out)
        self.assertIn("24.5", out)
        self.assertIn("On-going Items", out)
        self.assertIn("45", out)
        self.assertNotIn("Authorized Service", out)  # retired 2026-10-04

    def test_reports_to_follows_belonging_admin_entity_new(self):
        self.stub_get(RD)
        _capture(entity_dir.cmd_entity, "rd", [RD["_id"]])
        self.assertIn(("1791128419997x304312463708560100", "entity_employee"), self.cell_calls)

    def test_admin_detail_reads_available_points(self):
        self.stub_get(ADMIN)
        _, out, _ = _capture(entity_dir.cmd_entity, "admin", [ADMIN["_id"]])
        self.assertIn("32831.58", out)

    def test_an_id_of_another_employee_type_is_not_found_with_a_hint(self):
        self.stub_get(RD)
        _, out, err = _capture(entity_dir.cmd_entity, "crm", [RD["_id"]])
        self.assertIn(f"No crm entity found with ID '{RD['_id']}'", err)
        self.assertIn(f"try: rd {RD['_id']}", err)
        self.assertNotIn("RD Busy Rate", out)


class UserEntities(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self._api_list = user.api_list

        def _api_list(typename, constraints=None, **kwargs):
            self.calls.append((typename, constraints))
            if typename == "entity_employee":
                return [RD, ADMIN, CRM]
            if typename == "entity_client":
                return [{"_id": "client1"}]
            return []
        user.api_list = _api_list

    def tearDown(self):
        user.api_list = self._api_list

    def test_one_entity_employee_lookup_bucketed_by_employee_type(self):
        found = user._find_user_entities("u1")
        self.assertEqual(found, {
            "CRM Entity": CRM["_id"],
            "RD Entity": RD["_id"],
            "Admin Entity": ADMIN["_id"],
            "Client Entity": "client1",
        })
        self.assertEqual(self.calls[0], (
            "entity_employee",
            [{"key": "portal_user", "constraint_type": "equals", "value": "u1"}],
        ))
        self.assertEqual([c[0] for c in self.calls], ["entity_employee", "entity_client"])


class ProjectItemDetail(unittest.TestCase):
    def setUp(self):
        self.cells = []
        self._saved = (entities.entity_cell, project_item._resolve_project_label,
                       project_item._resolve_product_name, project_item.id_to_abbr, cit._term_width)

        def _cell(ref, typename):
            self.cells.append((ref, typename))
            return str(ref) if ref else "-"
        entities.entity_cell = _cell
        project_item._resolve_project_label = lambda pid: "-"
        project_item._resolve_product_name = lambda pid: "-"
        project_item.id_to_abbr = lambda cid: "-"
        cit._term_width = lambda: 200

    def tearDown(self):
        (entities.entity_cell, project_item._resolve_project_label,
         project_item._resolve_product_name, project_item.id_to_abbr, cit._term_width) = self._saved

    def test_crm_and_rd_operator_resolve_through_entity_employee(self):
        it = {"_id": "i1", "item_name": "x", "data: crm": "crm1", "entity_rd_new": "rd1"}
        _capture(project_item._render_item_detail, it)
        self.assertIn(("crm1", "entity_employee"), self.cells)
        self.assertIn(("rd1", "entity_employee"), self.cells)


if __name__ == "__main__":
    unittest.main()
