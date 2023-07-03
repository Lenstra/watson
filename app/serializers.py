import base64
import json

from .models import Output, Project, Stack, UsedBy
from django.conf import settings
from django.utils.module_loading import import_string
from rest_framework import serializers
from rest_framework.reverse import reverse


class HyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        """
        Given an object, return the URL that hyperlinks to the object.

        May raise a `NoReverseMatch` if the `view_name` and `lookup_field`
        attributes are not configured to correctly match the URL conf.
        """
        # Unsaved objects will not yet have a valid URL.
        if hasattr(obj, "pk") and obj.pk in (None, ""):
            return None

        lookup_value = getattr(obj, self.lookup_field)
        kwargs = {self.lookup_url_kwarg: lookup_value}
        try:
            kwargs["project"] = obj.project.slug
        except AttributeError:
            pass
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)


# https://www.django-rest-framework.org/api-guide/serializers/#dynamically-modifying-fields
class DynamicFieldsModelSerializer(serializers.HyperlinkedModelSerializer):
    """
    A ModelSerializer that takes an additional `fields` argument that
    controls which fields should be displayed.
    """

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' arg up to the superclass
        fields = kwargs.pop("fields", None)

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

        if fields is not None:
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(fields)
            existing = set(self.fields)
            for field_name in existing - allowed:
                self.fields.pop(field_name)


class ProjectSerializerStub(DynamicFieldsModelSerializer):
    id = serializers.CharField(source="slug", read_only=True)
    url = HyperlinkedIdentityField(view_name="project-detail", lookup_field="slug")

    class Meta:
        model = Project
        fields = ["id", "url", "name"]


class UsedBySerializer(serializers.Serializer):
    id = serializers.CharField(source="full_path", read_only=True)
    url = serializers.SerializerMethodField()
    last_used_at = serializers.DateTimeField()

    class Meta:
        model = UsedBy
        fields = ["id", "url", "last_used_at"]

    def get_url(self, obj):
        return reverse(
            "stack-detail",
            kwargs={"project": obj.used_by.project.slug, "slug": obj.used_by.slug},
            request=self.context["request"],
        )


class OutputSerializer(serializers.Serializer):
    value = serializers.JSONField()
    deprecated = serializers.CharField(default="")
    warning = serializers.CharField(default="")
    sensitive = serializers.BooleanField(default=False)


class StackSerializer(DynamicFieldsModelSerializer):
    id = serializers.CharField(source="full_path", read_only=True)
    url = HyperlinkedIdentityField(view_name="stack-detail", lookup_field="slug")
    project = ProjectSerializerStub(read_only=True)
    outputs = serializers.DictField(child=OutputSerializer(), default=dict)
    used_by = UsedBySerializer(source="used_by_rel", many=True, read_only=True)

    def create(self, validated_data):
        outputs = validated_data.pop("outputs")
        stack = Stack.objects.create(**validated_data)
        wrapper = import_string(settings.WRAPPER)()

        objects = []
        for k, v in outputs.items():
            if v["sensitive"]:
                b = json.dumps(v["value"]).encode()
                value = base64.b85encode(wrapper.encrypt(b)).decode()
            else:
                value = v["value"]

            objects.append(
                Output(
                    stack_id=stack.id,
                    key=k,
                    value=value,
                    deprecated=v["deprecated"],
                    sensitive=v["sensitive"],
                )
            )

        Output.objects.bulk_create(objects)
        return stack

    class Meta:
        model = Stack
        fields = ["id", "url", "name", "project", "outputs", "used_by"]


class ProjectSerializer(ProjectSerializerStub):
    stacks = StackSerializer(
        source="stack_set",
        many=True,
        read_only=True,
        fields=("id", "url", "name"),
    )

    class Meta:
        model = Project
        fields = ["id", "url", "name", "stacks"]
