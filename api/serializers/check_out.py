from rest_framework import serializers
from api.models import Booking, Room, Payment, RoomType

class AssignedRoomSerializer(serializers.ModelSerializer):
    room_type_name = serializers.CharField(source="room_type.name")

    class Meta:
        model = Room
        fields = ["id", "room_number", "floor", "room_type_name"]

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "payment_type", "status", "description", "paid_at"]

class BookingDetailSerializer(serializers.ModelSerializer):
    assigned_room = AssignedRoomSerializer(source="assigned_room", read_only=True)
    payments = PaymentSerializer(many=True, read_only=True)

    class Meta:
        model = Booking
        fields = [
            "id",
            "guest_name",
            "guest_email",
            "guest_phone",
            "status",
            "check_in",
            "check_out",
            "nights",
            "total_amount",
            "downpayment",
            "remaining_balance",
            "additional_fee",
            "assigned_room",
            "payments",
        ]
