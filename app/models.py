from django.db import models
from django.db.models import CheckConstraint, F, Q, TextField, Value
from django.db.models.functions import Concat
from django.utils.text import slugify


class Model(models.Model):
    def save(self, *args, **kwargs):
        if not self.id and not self.slug:
            self.slug = slugify(self.name)

        super().save(*args, **kwargs)

    class Meta:
        abstract = True


class Project(Model):
    name = models.TextField()
    slug = models.SlugField(unique=True, blank=False)


class StackManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                full_path=Concat(
                    "project__slug", Value("/"), "slug", output_field=TextField()
                )
            )
        )


class Stack(Model):
    name = models.TextField()
    slug = models.SlugField(blank=False)
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    used_by = models.ManyToManyField("Stack", through="UsedBy")

    objects = StackManager()

    def outputs(self):
        return {
            output.key: {
                "value": output.value,
                "deprecated": output.deprecated if output.deprecated else None,
                "warning": output.warning if output.warning else None,
            }
            for output in self.output_set.all()
        }

    class Meta:
        unique_together = [["project", "slug"]]


class UsedByManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .annotate(
                full_path=Concat(
                    "used_by__project__slug",
                    Value("/"),
                    "used_by__slug",
                    output_field=TextField(),
                )
            )
        )


class UsedBy(models.Model):
    stack = models.ForeignKey(
        Stack, related_name="used_by_rel", on_delete=models.CASCADE
    )
    used_by = models.ForeignKey(Stack, related_name="+", on_delete=models.CASCADE)
    last_used_at = models.DateTimeField()

    objects = UsedByManager()

    class Meta:
        unique_together = [["stack", "used_by"]]
        constraints = [
            CheckConstraint(
                check=~Q(stack=F("used_by")),
                name="check_self_reference",
            ),
        ]


class Output(models.Model):
    stack = models.ForeignKey(Stack, on_delete=models.CASCADE)
    key = models.SlugField(null=False, blank=False)
    value = models.JSONField()
    deprecated = models.TextField(blank=True)
    warning = models.TextField(blank=True)

    class Meta:
        unique_together = [["stack", "key"]]
