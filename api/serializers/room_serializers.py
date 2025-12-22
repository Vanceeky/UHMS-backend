from rest_framework import serializers
from api.models import RoomType, Room


class RoomTypeSerializer(serializers.ModelSerializer):
    class Meta:
        model = RoomType
        fields = '__all__'


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = '__all__'


class RoomTypeSnippetSerializer(serializers.ModelSerializer):

    class Meta:
        model = RoomType
        fields = ['id', 'name']

class RoomOperationSerializer(serializers.ModelSerializer):

    room_type = RoomTypeSnippetSerializer(read_only=True)
    

    last_updated = serializers.DateTimeField(source='updated_at', read_only=True)

    class Meta:
        model = Room
        fields = [
            'id', 
            'room_number', 
            'floor', 
            'room_type', 
            'status', 
            'note', 
            'last_updated'
        ]
        
        read_only_fields = ['id', 'room_number', 'floor', 'room_type', 'last_updated']

    def validate_status(self, value):

        return value