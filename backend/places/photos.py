from io import BytesIO
from uuid import uuid4

from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from PIL import Image, ImageOps
from rest_framework import generics, serializers, status
from rest_framework.exceptions import APIException
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.permissions import BasePermission, IsAuthenticatedOrReadOnly, SAFE_METHODS
from rest_framework.renderers import BaseRenderer, JSONRenderer
from rest_framework.reverse import reverse
from rest_framework.views import APIView

from administration.models import record_activity
from .models import ItemStatus, Place, PlacePhoto


MAX_UPLOAD_BYTES = 5 * 1024 * 1024
MAX_PIXELS = 16_000_000


class PhotoStorageUnavailable(APIException):
    status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    default_detail = "Photo storage is unavailable. Please try again."


class PlacePhotoSerializer(serializers.ModelSerializer):
    image = serializers.FileField(write_only=True)
    image_url = serializers.SerializerMethodField()
    can_delete = serializers.SerializerMethodField()
    username = serializers.CharField(source="user.username", read_only=True)
    place_name = serializers.CharField(source="place.name", read_only=True)
    reviewer = serializers.CharField(source="reviewed_by.username", read_only=True, default=None)

    class Meta:
        model = PlacePhoto
        fields = ["id", "place", "place_name", "user", "username", "image", "image_url",
                  "caption", "status", "reviewer", "reviewed_at", "rejection_reason",
                  "created_at", "can_delete"]
        read_only_fields = [field for field in fields if field not in ("image", "caption")]

    def get_image_url(self, obj):
        return reverse("place-photo-content", kwargs={"place_id": obj.place_id, "pk": obj.pk},
                       request=self.context["request"])

    def get_can_delete(self, obj):
        user = self.context["request"].user
        return user.is_authenticated and (user.pk == obj.user_id or user.is_staff)

    def validate_image(self, upload):
        if upload.size > MAX_UPLOAD_BYTES:
            raise serializers.ValidationError("Choose a photo of 5 MiB or less.")
        try:
            with Image.open(upload, formats=["JPEG", "PNG", "WEBP"]) as source:
                if source.width * source.height > MAX_PIXELS:
                    raise serializers.ValidationError("Choose a photo of 16 megapixels or less.")
                if getattr(source, "is_animated", False):
                    raise serializers.ValidationError("Choose a still photo.")
                source.load()
                image = ImageOps.exif_transpose(source)
                image.thumbnail((2400, 2400))
                rgba = image.convert("RGBA")
                clean = Image.new("RGB", rgba.size, "white")
                clean.paste(rgba, mask=rgba.getchannel("A"))
                output = BytesIO()
                clean.save(output, "JPEG", quality=85)
        except (OSError, ValueError, SyntaxError, Image.DecompressionBombError) as exc:
            raise serializers.ValidationError("Choose a readable JPEG, PNG, or WebP photo.") from exc
        return ContentFile(output.getvalue(), name=f"{uuid4().hex}.jpg")

    def create(self, validated_data):
        photo = PlacePhoto(**validated_data)
        try:
            with transaction.atomic():
                photo.save()
        except Exception as exc:
            if photo.image._committed:
                photo.image.delete(save=False)
            if isinstance(exc, OSError):
                raise PhotoStorageUnavailable() from exc
            raise
        return photo


def visible_photos(user, place_id):
    photos = PlacePhoto.objects.filter(place_id=place_id).select_related("user", "place", "reviewed_by")
    if user.is_staff:
        return photos
    allowed = Q(status=ItemStatus.APPROVED)
    if user.is_authenticated:
        allowed |= Q(user=user)
    return photos.filter(allowed)


class PhotoOwnerOrStaff(BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.method in SAFE_METHODS or request.user.is_staff or request.user.pk == obj.user_id


class PlacePhotoListCreateView(generics.ListCreateAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly]
    parser_classes = [MultiPartParser, FormParser]
    serializer_class = PlacePhotoSerializer

    def get_queryset(self):
        place = get_object_or_404(Place, pk=self.kwargs["place_id"])
        return visible_photos(self.request.user, place.pk)

    def perform_create(self, serializer):
        place = get_object_or_404(Place, pk=self.kwargs["place_id"])
        serializer.save(place=place, user=self.request.user)


class PlacePhotoDetailView(generics.RetrieveDestroyAPIView):
    permission_classes = [IsAuthenticatedOrReadOnly, PhotoOwnerOrStaff]
    serializer_class = PlacePhotoSerializer

    def get_queryset(self):
        return visible_photos(self.request.user, self.kwargs["place_id"])

    @transaction.atomic
    def perform_destroy(self, instance):
        if self.request.user.is_staff:
            record_activity(self.request, "deleted", "place photo", instance,
                            f"Deleted photo #{instance.pk} of {instance.place.name}")
        instance.delete()


class PhotoRenderer(BaseRenderer):
    media_type = "image/jpeg"
    format = "jpg"
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # Successful requests stream a FileResponse directly. DRF renders only errors here.
        renderer_context["response"]["Content-Type"] = "application/json"
        return JSONRenderer().render(data)


class PlacePhotoContentView(APIView):
    renderer_classes = [PhotoRenderer, JSONRenderer]

    def get(self, request, place_id, pk):
        photo = get_object_or_404(visible_photos(request.user, place_id), pk=pk)
        try:
            stream = photo.image.open("rb")
        except FileNotFoundError as exc:
            raise Http404("Photo file is missing.") from exc
        except OSError as exc:
            raise PhotoStorageUnavailable() from exc
        response = FileResponse(stream, content_type="image/jpeg")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
