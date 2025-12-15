from django.urls import path
from rest_framework.routers import DefaultRouter

from api.views.room import RoomTypeViewSet
from api.views.booking import AvailableRoomsView, BookingViewSet, BookingListView, ApproveBookingView, RejectBookingView, CancelBookingView, AvailablePhysicalRoomsView, CheckInGuestView, CheckOutGuestView, CheckedInBookingListView
from api.views.check_out import BookingDetailView
from api.views.order import MenuView, OrderViewSet


router = DefaultRouter()
router.register('room_type', RoomTypeViewSet)
router.register(r'bookings', BookingViewSet, basename='booking')

router.register(r'menu', MenuView, basename='menu')
router.register(r'order', OrderViewSet, basename='order')

urlpatterns = router.urls
urlpatterns += [    
    path("booking-list/", BookingListView.as_view(), name="booking-list"),
    path('bookings/<str:pk>/approve/', ApproveBookingView.as_view(), name='booking-approve'),
    path('bookings/<str:pk>/reject/', RejectBookingView.as_view(), name='booking-reject'),
    path('bookings/<str:pk>/cancel/', CancelBookingView.as_view(), name='booking-cancel'),


    path('room-types/<int:pk>/available-rooms/', AvailableRoomsView.as_view(), name='available-rooms'),
        # ⭐ NEW ENDPOINTS ⭐
    path('room-types/<int:pk>/available-physical-rooms/', AvailablePhysicalRoomsView.as_view(),
         name='available-physical-rooms'),

     path('bookings/<str:booking_id>/check-in/', CheckInGuestView.as_view(), name='booking-check-in'),

     path("booking/<str:booking_id>/check-out/", CheckOutGuestView.as_view(), name="booking-check-out"),

    path("bookings/<str:booking_id>/details/", BookingDetailView.as_view(), name="booking-detail"),


    path(
        "bookings/list/checked-in/",
        CheckedInBookingListView.as_view(),
        name="checked-in-bookings",
    ),

    ]
