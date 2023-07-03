from .models import Project, Stack, UsedBy
from .serializers import ProjectSerializer, StackSerializer
from django.db.models.query import QuerySet
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import mixins, renderers, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.response import Response
from rest_framework.settings import api_settings


class RawRenderer(renderers.JSONRenderer):
    media_type = "text/plain"
    format = "raw"

    def render(self, data, accepted_media_type=None, renderer_context=None):
        data = data["value"]

        if isinstance(data, str):
            return data.encode()

        return super().render(data, accepted_media_type, renderer_context)


class StackViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    viewsets.GenericViewSet,
):
    serializer_class = StackSerializer
    lookup_field = "slug"

    def get_queryset(self) -> QuerySet:
        return Stack.objects.filter(project__slug=self.kwargs["project"])

    def _update_used_by(self, request, obj):
        header = request.headers.get("x-watson-stack")
        if header is not None:
            caller = Stack.objects.filter(full_path=header).first()
            if caller is not None and caller.pk != obj.pk:
                UsedBy.objects.update_or_create(
                    stack=obj, used_by=caller, defaults={"last_used_at": timezone.now()}
                )

    @action(detail=True, url_path="outputs")
    def get_all_outputs(self, request, project, slug, format=None):
        obj = get_object_or_404(self.get_queryset(), slug=slug)
        self._update_used_by(request, obj)
        return Response(obj.outputs())

    @action(
        detail=True,
        url_path="outputs/(?P<key>[^/.]+)",
        renderer_classes=[*api_settings.DEFAULT_RENDERER_CLASSES, RawRenderer],
    )
    def get_output(self, request, project, slug, key, format=None):
        obj = get_object_or_404(self.get_queryset(), slug=slug)
        self._update_used_by(request, obj)
        try:
            value = obj.outputs()[key]
        except KeyError:
            raise NotFound(f"{key!r} is not present in the outputs.")
        return Response(value)


class ProjectViewSet(
    mixins.CreateModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin,
    mixins.DestroyModelMixin,
    mixins.ListModelMixin,
    viewsets.GenericViewSet,
):
    queryset = Project.objects.all()
    serializer_class = ProjectSerializer
    lookup_field = "slug"

    def post(self, request, slug):
        project = get_object_or_404(self.queryset, slug=slug)
        serializer = StackSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        serializer.save(project_id=project.id)
        data = serializer.data
        data["id"] = f"{project.slug}/{serializer.instance.slug}"

        try:
            headers = {"Location": str(data[api_settings.URL_FIELD_NAME])}
        except (TypeError, KeyError):
            headers = {}
        return Response(data, status=status.HTTP_201_CREATED, headers=headers)
