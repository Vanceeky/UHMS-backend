from rest_framework.viewsets import ReadOnlyModelViewSet

from api.models import RoomType, Room

from api.serializers.room_serializers import RoomTypeSerializer, RoomSerializer


class RoomTypeViewSet(ReadOnlyModelViewSet):
    queryset = RoomType.objects.all()
    serializer_class = RoomTypeSerializer