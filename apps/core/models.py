import uuid

from django.db import models


class TimeStampedModel(models.Model):
    """
    Abstract base model providing self-updating
    created_at and updated_at fields.
    """

    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Date de création")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Dernière mise à jour")

    class Meta:
        abstract = True


class UUIDModel(models.Model):
    """
    Abstract base model providing a UUID primary key
    for public, unguessable URLs and IDs.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True
