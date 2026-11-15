import uuid

from django.db import models


class Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=64, db_index=True)
    state = models.CharField(max_length=24, default="queued", db_index=True)
    kind = models.CharField(max_length=24, default="sequence")
    selection = models.JSONField()
    stage = models.CharField(max_length=240, default="Waiting for worker")
    result = models.JSONField(default=dict)
    error = models.JSONField(default=dict)
    attempts = models.PositiveIntegerField(default=0)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)


class Dispatch(models.Model):
    job = models.OneToOneField(Job, on_delete=models.CASCADE)
    published = models.DateTimeField(null=True)


class Sequence(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cache_key = models.CharField(max_length=64, unique=True)
    manifest = models.JSONField()
    created = models.DateTimeField(auto_now_add=True)


class Artifact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    sequence = models.ForeignKey(Sequence, on_delete=models.PROTECT)
    filename = models.CharField(max_length=200)
    sha256 = models.CharField(max_length=64)
    media_type = models.CharField(max_length=80)
    size = models.PositiveIntegerField()


class Candidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=64, db_index=True)
    sequence = models.ForeignKey(Sequence, on_delete=models.PROTECT)
    data = models.JSONField()
    revision = models.PositiveIntegerField(default=1)
    updated = models.DateTimeField(auto_now=True)


class Report(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    owner = models.CharField(max_length=64, db_index=True)
    sequence = models.ForeignKey(Sequence, on_delete=models.PROTECT)
    snapshot = models.JSONField()
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="children")
    root = models.ForeignKey("self", null=True, blank=True, on_delete=models.PROTECT, related_name="revisions")
    revision = models.PositiveIntegerField(default=1)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["root", "revision"], name="unique_report_revision")]


class Share(models.Model):
    token_hash = models.CharField(max_length=64, primary_key=True)
    report = models.ForeignKey(Report, on_delete=models.CASCADE)
    revoked = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)


class Review(models.Model):
    report = models.ForeignKey(Report, on_delete=models.PROTECT)
    owner = models.CharField(max_length=64)
    text = models.TextField()
    created = models.DateTimeField(auto_now_add=True)
