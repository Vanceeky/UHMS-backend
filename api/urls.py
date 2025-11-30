from django.urls import path
from rest_framework.routers import DefaultRouter

from api.views.room import RoomTypeViewSet
from api.views.booking import AvailableRoomsView, BookingViewSet, BookingListView, ApproveBookingView, RejectBookingView, CancelBookingView


router = DefaultRouter()
router.register('room_type', RoomTypeViewSet)
router.register(r'bookings', BookingViewSet, basename='booking')

urlpatterns = router.urls
urlpatterns += [    
    path("booking-list/", BookingListView.as_view(), name="booking-list"),
    path('bookings/<str:pk>/approve/', ApproveBookingView.as_view(), name='booking-approve'),
    path('bookings/<str:pk>/reject/', RejectBookingView.as_view(), name='booking-reject'),
    path('bookings/<str:pk>/cancel/', CancelBookingView.as_view(), name='booking-cancel'),


    path('room-types/<int:pk>/available-rooms/', AvailableRoomsView.as_view(), name='available-rooms'),
    
    ]
