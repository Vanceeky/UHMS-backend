from rest_framework import viewsets, mixins
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend

from api.models import Room
from api.serializers.room_serializers import RoomOperationSerializer

class RoomOperationViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.UpdateModelMixin, # Allows PATCH/PUT
    viewsets.GenericViewSet
):
    """
    API Endpoint for Housekeeping & Maintenance.
    
    Capabilities:
    - List all rooms (optimized)
    - Filter by floor or status
    - Search by room number
    - Update ONLY status and notes
    """
    # select_related is vital here to fetch RoomType data in the same query
    queryset = Room.objects.all().select_related('room_type').order_by('floor', 'room_number')
    serializer_class = RoomOperationSerializer
    
    # Enable Searching and Filtering
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    
    # ?status=dirty&floor=1
    filterset_fields = ['status', 'floor']
    
    # ?search=101
    search_fields = ['room_number', 'room_type__name']
    
    # ?ordering=-updated_at
    ordering_fields = ['updated_at', 'floor', 'room_number']

    # Restrict HTTP methods to only allow Reading and Updating
    # DELETE and POST are intentionally disabled for safety
    http_method_names = ['get', 'patch', 'head', 'options']

    def perform_update(self, serializer):
        """
        Hook to add extra logic during update if needed.
        Example: Log who made the change if you have user context.
        """
        # user = self.request.user
        # serializer.save(last_modified_by=user)
        serializer.save()