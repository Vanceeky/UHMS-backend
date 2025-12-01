from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
# Create your models here.


class CustomUser(AbstractUser):
    
    class Role(models.TextChoices):
        ADMIN = 'admin', "ADMIN"
        FRONT_DESK = 'front_desk', "FRONT_DESK"
        HOUSEKEEPING = 'housekeeping', "HOUSEKEEPING"
        MAINTENANCE = 'maintenance', "MAINTENANCE"
        RESTUARANT = 'restaurant', "RESTAURANT"
        INVENTORY = 'inventory', "INVENTORY"

    role = models.CharField(max_length=20, choices=Role.choices, default=Role.FRONT_DESK)

    def __str__(self):
        return f"{self.get_full_name().upper()} - {self.role.upper()}"


class RoomType(models.Model):
    name = models.CharField(max_length=100, unique=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='room_type_images/', blank=True, null=True)
    amenities = models.JSONField(default=list, blank=True, null=True)

    max_adults = models.PositiveIntegerField(default=2)
    max_children = models.PositiveIntegerField(default=0)

    extra_adult_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    extra_child_fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.name} - ₱{self.price}/night"
    

class Room(models.Model):
    class Status(models.TextChoices):
        AVAILABLE = "available", "Available"
        OCCUPIED = "occupied", "Occupied"
        DIRTY = "dirty", "Needs Cleaning"
        CLEANING = "cleaning", "Cleaning In Progress"
        MAINTENANCE = "maintenance", "Under Maintenance"
        OUT_OF_SERVICE = "out_of_service", "Out of Service"
      

    room_number = models.CharField(max_length=10, unique=True)
    floor = models.PositiveIntegerField(default=1)

    # linked to room type
    room_type = models.ForeignKey(RoomType, on_delete=models.CASCADE, related_name='rooms')

    status = models.CharField(max_length=30, choices=Status.choices, default=Status.AVAILABLE)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.room_number} - {self.room_type.name}"
    



# ------------------------------
# Booking Model
# ------------------------------
class Booking(models.Model):
    id = models.CharField(
        max_length=20,
        primary_key=True,
        editable=False,
        unique=True
    )

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"           # Online booking, not confirmed yet
        CONFIRMED = "confirmed", "Confirmed"     # Staff confirmed
        CHECKED_IN = "checked_in", "Checked In" # Guest checked in
        CHECKED_OUT = "checked_out", "Checked Out"
        CANCELLED = "cancelled", "Cancelled"
        REJECTED = "rejected", "Rejected"

    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="bookings")
    assigned_room = models.ForeignKey(
        Room,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_bookings"
    )
    guest_name = models.CharField(max_length=255)
    email = models.EmailField()
    contact_number = models.CharField(max_length=20)

    check_in = models.DateField()
    check_out = models.DateField()

    adults = models.PositiveBigIntegerField()
    children = models.PositiveBigIntegerField()
    extra_children = models.PositiveIntegerField(default=0)

    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    additional_fee = models.JSONField(default=list, blank=True, null=True)  # e.g., restaurant orders

    notes = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.PENDING)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    def save(self, *args, **kwargs):
        if not self.id:
            today = datetime.date.today()
            date_str = today.strftime("%y%m%d")  # e.g. 250128

            # Look for the latest booking today
            last_booking = (
                Booking.objects.filter(id__startswith=f"BKG-{date_str}")
                .order_by("-id")
                .first()
            )

            if last_booking:
                # Extract last 4 digits
                last_number = int(last_booking.id.split("-")[-1])
                new_number = f"{last_number + 1:04d}"
            else:
                new_number = "0001"

            self.id = f"BKG-{date_str}-{new_number}"

        super().save(*args, **kwargs)
    def __str__(self):
        return f"{self.guest_name} - {self.room.room_number} ({self.check_in} to {self.check_out})"

# ------------------------------
# Payment Model
# ------------------------------
class Payment(models.Model):
    class PaymentStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PAID = "paid", "Paid"
        FAILED = "failed", "Failed"

    class PaymentCategory(models.TextChoices):
        DOWNPAYMENT = "downpayment", "Downpayment"
        REMAINING = "remaining", "Remaining Balance"
        ADDITIONAL = "additional", "Additional Fee"

    booking = models.ForeignKey(Booking, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=10, decimal_places=2)

    receipt = models.ImageField(upload_to='payment_receipts/', blank=True, null=True)
    
    # Structured type
    payment_type = models.CharField(
        max_length=20,
        choices=PaymentCategory.choices,
        default=PaymentCategory.ADDITIONAL
    )

    # Flexible description for staff / reporting
    description = models.TextField(blank=True, null=True)
    """ Downpayment example: "20% of Deluxe Room (Dec 1-5)"
    Remaining balance: "80% remaining for Deluxe Room"
    Additional fee: "Restaurant order: Pasta x2, Juice x1" """

    status = models.CharField(
        max_length=20,
        choices=PaymentStatus.choices,
        default=PaymentStatus.PENDING
    )

    transaction_reference = models.CharField(max_length=100, blank=True, null=True)
    paid_at = models.DateTimeField(blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.booking.guest_name} - {self.payment_type} ({self.amount} - {self.status})"


