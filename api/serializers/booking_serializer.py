from rest_framework import serializers
from api.models import Room, RoomType, Booking, Payment
from django.db import transaction
from django.db.models import Q
from datetime import date

from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail


class RoomSerializer(serializers.ModelSerializer):
    class Meta:
        model = Room
        fields = ('id', 'room_number', 'status', 'floor', 'room_type')

class PaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Payment
        fields = ["id", "amount", "payment_type", "status", "description", "paid_at"]


class BookingCreateSerializer(serializers.ModelSerializer):
    # Inputs from Frontend
    room_type_id = serializers.IntegerField(write_only=True)
    gcash_reference = serializers.CharField(write_only=True, required=True)
    receipt_image = serializers.ImageField(write_only=True, required=False)
    
    # Read-only outputs
    room_details = serializers.CharField(source='room.room_number', read_only=True)
    status = serializers.CharField(read_only=True)
    total_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Booking
        fields = [
            'id', 'guest_name', 'email', 'contact_number', 
            'check_in', 'check_out', 'adults', 'children', 
            'room_type_id', 'gcash_reference', 'receipt_image',
            'room_details', 'status', 'total_price'
        ]

    def validate(self, data):

        check_in = data['check_in']
        check_out = data['check_out']
        room_type_id = data['room_type_id']

        if check_in >= check_out:
            raise serializers.ValidationError("Check-out date must be after check-in date.")

        if check_in < date.today():
            raise serializers.ValidationError("Cannot book dates in the past.")

       
        rooms_of_type = Room.objects.filter(
            room_type_id=room_type_id, 
            status=Room.Status.AVAILABLE
        )

        
        unavailable_rooms = Booking.objects.filter(
            room__in=rooms_of_type,
            check_in__lt=check_out,
            check_out__gt=check_in,
            status__in=[Booking.Status.CONFIRMED, Booking.Status.PENDING, Booking.Status.CHECKED_IN]
        ).values_list('room_id', flat=True)

        available_rooms = rooms_of_type.exclude(id__in=unavailable_rooms)

        if not available_rooms.exists():
            raise serializers.ValidationError("No rooms of this type are available for the selected dates.")

        # Store the first available room in the context to use in create()
        self.context['available_room'] = available_rooms.first()
        
        return data

    @transaction.atomic
    def create(self, validated_data):
        # Extract non-model fields
        room_type_id = validated_data.pop('room_type_id')
        gcash_ref = validated_data.pop('gcash_reference')
        receipt_img = validated_data.pop('receipt_image', None)
        
        # Get the room we found in validate()
        room = self.context['available_room']
        room_type = room.room_type

        
        nights = (validated_data['check_out'] - validated_data['check_in']).days
        
        # Calculate Base
        base_price = room_type.price * nights

        # Calculate Extra Person Fees
        extra_adults = max(0, validated_data['adults'] - room_type.max_adults)
        extra_children = max(0, validated_data['children'] - room_type.max_children)
        
        extra_cost = (extra_adults * room_type.extra_adult_fee * nights) + \
                     (extra_children * room_type.extra_child_fee * nights)

        total_price = base_price + extra_cost

        # 1. Create Booking
        booking = Booking.objects.create(
            room=room,
            total_price=total_price,
            status=Booking.Status.PENDING, # Pending verification
            **validated_data
        )

        # 2. Create Downpayment Record (20%)
        downpayment_amount = total_price * Decimal("0.20")
        
        Payment.objects.create(
            booking=booking,
            amount=downpayment_amount,
            payment_type=Payment.PaymentCategory.DOWNPAYMENT,
            status=Payment.PaymentStatus.PENDING, # Pending verification of screenshot
            transaction_reference=gcash_ref,
            receipt=receipt_img,
            description=f"20% Downpayment via GCash. Ref: {gcash_ref}"
        )

        subject = f"Booking Received – Pending Verification (ID: {booking.id})"

        message = f"""
        Dear {booking.guest_name},

        Thank you for choosing our hotel.

        We have successfully received your booking request. Your reservation is currently
        PENDING VERIFICATION while we review your submitted payment.

        Booking Details:
        - Booking ID: {booking.id}
        - Room Type: {room.room_type.name}
        - Check-in Date: {booking.check_in}
        - Check-out Date: {booking.check_out}
        - Total Guests: {booking.adults + booking.children + booking.extra_children}
        - Total Price: ₱{booking.total_price}
        - Downpayment Submitted: ₱{downpayment_amount}

        Our team will verify your payment within 24 hours.
        Once approved, you will receive a confirmation email.

        If any additional information is required, we will contact you via this email.

        Best regards,
        Hotel Management Team
        """

        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
            fail_silently=False,
        )
        
 
        



        return booking
    

class BookingSerializer(serializers.Serializer):
    id = serializers.CharField()
    guestName = serializers.SerializerMethodField()
    guestEmail = serializers.SerializerMethodField()
    guestPhone = serializers.SerializerMethodField()
    status = serializers.SerializerMethodField()

    checkIn = serializers.DateField(source="check_in")
    checkOut = serializers.DateField(source="check_out")

    roomType = serializers.SerializerMethodField()
    roomTypeId = serializers.IntegerField(source="room.room_type.id")
    assignedRoom = serializers.SerializerMethodField()

    nights = serializers.SerializerMethodField()
    totalAmount = serializers.DecimalField(source="total_price", max_digits=10, decimal_places=2)

    downpayment = serializers.SerializerMethodField()
    remainingBalance = serializers.SerializerMethodField()

    additionalFee = serializers.JSONField(source="additional_fee")

    payments = PaymentSerializer(many=True)

    paymentRef = serializers.SerializerMethodField()
    paymentReceiptUrl = serializers.SerializerMethodField()

    guests = serializers.SerializerMethodField()



    def get_guestName(self, obj):
        return obj.guest_name

    def get_guestEmail(self, obj):
        return obj.email

    def get_guestPhone(self, obj):
        return obj.contact_number

    def get_status(self, obj):
        # convert Django "checked_in" -> frontend "checked-in"
        return obj.status.replace("_", "-")

    def get_roomType(self, obj):
        return obj.room.room_type.name

    def get_nights(self, obj):
        return (obj.check_out - obj.check_in).days

    def get_downpayment(self, obj):
        payments = obj.payments.filter(
            payment_type=Payment.PaymentCategory.DOWNPAYMENT
        )
        return float(sum(p.amount for p in payments))

    def get_remainingBalance(self, obj):
        down = self.get_downpayment(obj)
        
        # If the booking is checked-in or later
        if obj.status in [Booking.Status.CHECKED_IN, Booking.Status.CHECKED_OUT]:
            remaining_paid = obj.payments.filter(
                payment_type=Payment.PaymentCategory.REMAINING,
                status=Payment.PaymentStatus.PAID
            ).exists()
            if remaining_paid:
                return 0.0
        
        # Otherwise, calculate normally
        return float(obj.total_price) - float(down)

    def get_paymentRef(self, obj):
        latest_payment = obj.payments.order_by("-created_at").first()
        return latest_payment.transaction_reference if latest_payment else ""

    def get_paymentReceiptUrl(self, obj):
        latest_payment = obj.payments.order_by("-created_at").first()
        return latest_payment.receipt.url if latest_payment and latest_payment.receipt else ""

    def get_guests(self, obj):
        return obj.adults + obj.children + obj.extra_children


    def get_assignedRoom(self, obj):
        if obj.assigned_room:
            return obj.assigned_room.room_number
        return None
    







class CheckedInBookingSerializer(serializers.ModelSerializer):
    roomNumber = serializers.CharField(source="assigned_room.room_number", read_only=True)
    roomType = serializers.CharField(source="assigned_room.room_type.name", read_only=True)
    name = serializers.CharField(source="guest_name", read_only=True)
    class Meta:
        model = Booking
        fields = [
            "id",
            "name",
            "roomNumber",
            "roomType",
        ]