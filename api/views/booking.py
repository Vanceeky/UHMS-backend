from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from django.utils.dateparse import parse_date
from api.models import RoomType, Room, Booking
from api.serializers.booking_serializer import RoomSerializer, BookingCreateSerializer, BookingSerializer
from rest_framework import viewsets, mixins, parsers
from rest_framework.generics import ListAPIView

from django.conf import settings
from django.core.mail import send_mail




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
    