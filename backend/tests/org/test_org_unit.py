"""Tests for OrgUnit model."""

from django.test import TestCase

from app.org.models import IsolationPolicy, OrgUnit


class TestOrgUnitCreation(TestCase):
    def test_create_root_org_unit(self):
        unit = OrgUnit.objects.create(name="Acme Corp", slug="acme-corp", node_type="org")
        assert unit.parent is None
        assert unit.isolation_policy == IsolationPolicy.OPEN

    def test_create_child_org_unit(self):
        parent = OrgUnit.objects.create(name="Acme Corp", slug="acme", node_type="org")
        child = OrgUnit.objects.create(name="Engineering", slug="engineering", node_type="department", parent=parent)
        assert child.parent == parent

    def test_isolation_policy_choices(self):
        assert set(IsolationPolicy.values) == {"open", "isolated", "inherit_only", "visible_only"}


class TestOrgUnitAncestors(TestCase):
    def setUp(self):
        self.corp = OrgUnit.objects.create(name="Corp", slug="corp", node_type="org")
        self.dept = OrgUnit.objects.create(name="Dept", slug="dept", node_type="department", parent=self.corp)
        self.team = OrgUnit.objects.create(name="Team", slug="team", node_type="team", parent=self.dept)

    def test_get_ancestors(self):
        ancestors = self.team.get_ancestors()
        assert list(ancestors) == [self.dept, self.corp]

    def test_get_descendants(self):
        descendants = self.corp.get_descendants()
        pks = {u.pk for u in descendants}
        assert pks == {self.dept.pk, self.team.pk}

    def test_root_node_has_no_ancestors(self):
        assert self.corp.get_ancestors() == []
