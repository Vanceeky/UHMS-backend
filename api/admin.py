from django.contrib import admin
from .models import CustomUser, RoomType, Room, Booking, Payment

# ------------------------------
# CustomUser
# ------------------------------
@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'first_name', 'last_name', 'is_staff', 'is_active')
    search_fields = ('username', 'email', 'first_name', 'last_name')
    list_filter = ('is_staff', 'is_active')


# ------------------------------
# Payment Inline for Booking
# ------------------------------
class PaymentInline(admin.TabularInline):
    model = Payment
    extra = 1
    readonly_fields = ('created_at', 'updated_at', 'paid_at', 'transaction_reference')
    fields = (
        'payment_type',
        'description',
        'amount',
        'status',
        'receipt',
        'transaction_reference',
        'paid_at',
        'created_at',
        'updated_at',
    )
    show_change_link = True


# ------------------------------
# Booking Inline for Room
# ------------------------------
class BookingInline(admin.TabularInline):
    model = Booking
    fk_name = 'room'
    extra = 1
    readonly_fields = (
        'guest_name', 'email', 'contact_number',
        'check_in', 'check_out', 'adults', 'children',
        'assigned_room',
        'extra_children', 'total_price', 'status', 'notes'
    )
    fields = readonly_fields
    show_change_link = True
    inlines = [PaymentInline]  # Optional if using nested admin


# ------------------------------
# Room Inline for RoomType
# ------------------------------
class RoomInline(admin.TabularInline):
    model = Room
    extra = 1
    readonly_fields = ('status',)
    fields = ('room_number', 'status')
    show_change_link = True
    inlines = [BookingInline]  # Optional: requires django-nested-admin


# ------------------------------
# RoomType Admin
# ------------------------------
@admin.register(RoomType)
class RoomTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'price', 'max_adults', 'max_children')
    search_fields = ('name',)
    inlines = [RoomInline]


# ------------------------------
# Room Admin
# ------------------------------
@admin.register(Room)
class RoomAdmin(admin.ModelAdmin):
    list_display = ('room_number', 'room_type', 'status')
    list_filter = ('status', 'room_type')
    search_fields = ('room_number', 'room_type__name')
    inlines = [BookingInline]


# ------------------------------
# Booking Admin
# ------------------------------
@admin.register(Booking)
class BookingAdmin(admin.ModelAdmin):
    list_display = (
        'guest_name',
        'room',
        'check_in',
        'check_out',
        'status',
        'total_price',
        
    )
    list_filter = ('status', 'check_in', 'check_out')
    search_fields = ('guest_name', 'email', 'contact_number', 'room__room_number')
    inlines = [PaymentInline]
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        (None, {
            'fields': ('room', 'guest_name', 'email', 'contact_number')
        }),
        ('Booking Info', {
            'fields': ('check_in', 'check_out', 'assigned_room', 'adults', 'children', 'extra_children', 'total_price', 'additional_fee', 'status', 'notes')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at')
        }),
    )
