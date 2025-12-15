from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from api.models import RoomType, Room, Booking, Payment
from api.serializers.booking_serializer import RoomSerializer, BookingCreateSerializer, BookingSerializer, CheckedInBookingSerializer
from rest_framework import viewsets, mixins, parsers
from rest_framework.generics import ListAPIView

from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone




class AvailableRoomsView(APIView):
    def get(self, request, pk):
        """
        GET /api/room-types/<pk>/available-rooms/?check_in=YYYY-MM-DD&check_out=YYYY-MM-DD
        Returns rooms for the RoomType that are AVAILABLE for the given date range
        """
        check_in = request.query_params.get('check_in')
        check_out = request.query_params.get('check_out')

        if not check_in or not check_out:
            return Response({"detail": "check_in and check_out query parameters are required."}, status=status.HTTP_400_BAD_REQUEST)

        check_in_date = parse_date(check_in)
        check_out_date = parse_date(check_out)

        if not check_in_date or not check_out_date:
            return Response({"detail": "Invalid date format."}, status=status.HTTP_400_BAD_REQUEST)

        room_type = get_object_or_404(RoomType, pk=pk)

        # All rooms for this type
        rooms = Room.objects.filter(room_type=room_type, status=Room.Status.AVAILABLE)

        # Exclude rooms that are already booked in the given date range
        booked_rooms = Booking.objects.filter(
            room__room_type=room_type,
            status__in=[Booking.Status.PENDING, Booking.Status.CONFIRMED, Booking.Status.CHECKED_IN],
        ).filter(
            check_in__lt=check_out_date,
            check_out__gt=check_in_date
        ).values_list('room_id', flat=True)

        available_rooms = rooms.exclude(id__in=booked_rooms)

        serializer = RoomSerializer(available_rooms, many=True)
        return Response(serializer.data)


# ✅ Add RetrieveModelMixin here
class BookingViewSet(viewsets.GenericViewSet, mixins.CreateModelMixin, mixins.RetrieveModelMixin):
    queryset = Booking.objects.all()
    serializer_class = BookingCreateSerializer
    parser_classes = (parsers.MultiPartParser, parsers.FormParser)


class BookingListView(ListAPIView):
    queryset = Booking.objects.select_related("room__room_type").prefetch_related("payments")
    serializer_class = BookingSerializer



class ApproveBookingView(APIView):
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update booking status
        booking.status = Booking.Status.CONFIRMED
        booking.save()

        payment = get_object_or_404(Payment, booking=booking)
        payment.status = Payment.PaymentStatus.PAID
        payment.save()

        # Prepare email content
        subject = f"Booking Confirmed: {booking.id}"
        message = f"""
            Dear {booking.guest_name},

            We are pleased to inform you that your booking (ID: {booking.id}) has been confirmed.

            Booking Details:
            - Room: {booking.room.room_type.name}
            - Check-in: {booking.check_in}
            - Check-out: {booking.check_out}
            - Total Guests: {booking.adults + booking.children + booking.extra_children}
            - Total Price: ₱{booking.total_price}

            If you have any questions or need to make changes, please contact us.

            Thank you for choosing our hotel!

            Best regards,
            Hotel Management Team
        """

        # Send email
        send_mail(
            subject=subject,
            message=message,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
        )

        return Response(
            {"detail": f"Booking {booking.id} approved and email sent to {booking.email}."},
            status=status.HTTP_200_OK
        )

class RejectBookingView(APIView):
    """
    Reject a booking: update status, send email to guest
    """
    def post(self, request, pk):
        reason = request.data.get("reason", "Your booking was rejected.")

        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        # Update status
        booking.status = Booking.Status.REJECTED  # mark as cancelled/rejected
        booking.save()

        reason = request.data.get("reason", "Your booking was rejected.")
        subject = request.data.get("subject", f"Booking {booking.id} Rejected")

        send_mail(
            subject=subject,
            message=f"Hello {booking.guest_name},\n\n{reason}\n\nThank you.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[booking.email],
        )


        return Response({"detail": f"Booking {booking.id} rejected and email sent."}, status=status.HTTP_200_OK)
    

class CancelBookingView(APIView):
    """
    Guest cancels booking
    """
    def post(self, request, pk):
        try:
            booking = Booking.objects.get(pk=pk)
        except Booking.DoesNotExist:
            return Response({"detail": "Booking not found."}, status=status.HTTP_404_NOT_FOUND)

        booking.status = Booking.Status.CANCELLED
        booking.save()
        return Response({"detail": f"Booking {booking.id} cancelled successfully."})
    


class AvailablePhysicalRoomsView(APIView):
    def get(self, request, pk):  # pk = room_type id
        room_type = get_object_or_404(RoomType, id=pk)

        rooms = Room.objects.filter(
            room_type=room_type,
            status=Room.Status.AVAILABLE
        )

        assigned_rooms = Booking.objects.filter(
            assigned_room__isnull=False
        ).values_list('assigned_room_id', flat=True)

        available_rooms = rooms.exclude(id__in=assigned_rooms)

        serializer = RoomSerializer(available_rooms, many=True)
        return Response(serializer.data)



class CheckInGuestView(APIView):
    def post(self, request, booking_id):
        # 1. Get booking
        booking = get_object_or_404(Booking, id=booking_id)
        remaining_balance = request.data.get("remaining_balance")

        if booking.status != Booking.Status.CONFIRMED:
            return Response({"error": "Only confirmed bookings can be checked in."}, status=400)

        # 2. Get selected room from request
        room_id = request.data.get("room_id")
        room = get_object_or_404(Room, id=room_id)

        if room.status != Room.Status.AVAILABLE:
            return Response({"error": "Room is not available."}, status=400)

        # 3. Assign room and update statuses
        booking.assigned_room = room
        booking.status = Booking.Status.CHECKED_IN
        booking.save()

        room.status = Room.Status.OCCUPIED
        room.save()



        # 4. Handle remaining balance payments
        Payment.objects.create(
            booking=booking,  # Link the payment to the current booking
            amount=remaining_balance,  # Amount of the remaining balance
            payment_type=Payment.PaymentCategory.REMAINING,  # Categorize as "Remaining Balance"
            status=Payment.PaymentStatus.PAID,  # Mark the payment as fully paid
            description=f"Remaining balance fully paid for booking {booking.id}: ₱{remaining_balance}",  # Detailed description for reporting
        )

        return Response({
            "message": "Guest successfully checked in.",
            "booking_id": booking.id,
            "room": f"{room.room_type.name} - #{room.room_number}",
            "guest_name": booking.guest_name
        }, status=status.HTTP_200_OK)



class CheckOutGuestView(APIView):
    def post(self, request, booking_id):
        booking = get_object_or_404(Booking, id=booking_id)
        room = booking.assigned_room

        if not room:
            return Response({"error": "No room assigned for this booking."}, status=400)
        if room.status != Room.Status.OCCUPIED:
            return Response({"error": "Room is not occupied."}, status=400)
        if booking.status != Booking.Status.CHECKED_IN:
            return Response({"error": "Only checked-in bookings can be checked out."}, status=400)

        # Update booking and room
        booking.status = Booking.Status.CHECKED_OUT
        booking.save()

        room.status = Room.Status.DIRTY
        room.save()

        # Handle additional fees
        additional_fees = booking.additional_fee or []
        for fee in additional_fees:
            item_name = fee.get("name", "Additional Item")
            amount = fee.get("amount", 0)

            description = f"Additional charge for {item_name} (₱{amount:,.2f})"
            Payment.objects.create(
                booking=booking,
                amount=fee["amount"],
                payment_type=Payment.PaymentCategory.ADDITIONAL,
                status=Payment.PaymentStatus.PAID,
                description=description
            )

        return Response({
            "message": "Guest successfully checked out.",
            "booking_id": booking.id,
            "room": f"{room.room_type.name} - #{room.room_number}",
            "guest_name": booking.guest_name,
            "additional_fees": additional_fees,
        })



class CheckedInBookingListView(APIView):
   # permission_classes = [IsAuthenticated]

    def get(self, request):
        bookings = (
            Booking.objects
            .filter(status=Booking.Status.CHECKED_IN)
            .select_related("assigned_room", "assigned_room__room_type")
            .order_by("assigned_room__room_number")
        )

        serializer = CheckedInBookingSerializer(bookings, many=True)
        return Response(serializer.data)



