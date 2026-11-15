"""Database model constraint tests."""

import pytest
from django.db import IntegrityError

from apps.core.models import Report, Sequence

pytestmark = pytest.mark.django_db


def test_sequence_cache_key_unique():
    Sequence.objects.create(cache_key="unique-ck-1", manifest={})
    with pytest.raises(IntegrityError):
        Sequence.objects.create(cache_key="unique-ck-1", manifest={})


def test_report_revision_unique_constraint():
    seq = Sequence.objects.create(cache_key="rev-unique", manifest={"frames": [], "warnings": []})
    root = Report.objects.create(owner="a", sequence=seq, snapshot={"title": "r1"})
    Report.objects.create(owner="a", sequence=seq, snapshot={"title": "r2"}, parent=root, root=root, revision=2)
    with pytest.raises(IntegrityError):
        Report.objects.create(owner="a", sequence=seq, snapshot={"title": "dup"}, parent=root, root=root, revision=2)


def test_sequence_manifest_stores_json():
    data = {"frames": [{"id": "a"}], "warnings": ["w"], "nested": {"deep": True}}
    s = Sequence.objects.create(cache_key="json-test", manifest=data)
    s.refresh_from_db()
    assert s.manifest == data


def test_report_root_null_for_first_revision():
    """The first report in an investigation has no root or parent."""
    seq = Sequence.objects.create(cache_key="root-null", manifest={"frames": [], "warnings": []})
    r = Report.objects.create(owner="a", sequence=seq, snapshot={"title": "first"})
    assert r.root is None
    assert r.parent is None
    assert r.revision == 1


def test_artifact_protected_by_sequence():
    """Deleting a sequence with artifacts should be prevented by PROTECT."""
    from apps.core.models import Artifact

    seq = Sequence.objects.create(cache_key="protect-test", manifest={})
    Artifact.objects.create(sequence=seq, filename="test.fits", sha256="a" * 64, media_type="application/fits", size=100)
    with pytest.raises(Exception):  # ProtectedError is a subclass of IntegrityError
        seq.delete()
