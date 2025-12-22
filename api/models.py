from django.db import models
from django.contrib.auth.models import AbstractUser
import datetime
from django.core.exceptions import ValidationError



# Create your models here.


class CustomUser(AbstractUser):
    
    class Role(models.TextChoices):
        ADMIN = 'admin', "ADMIN"
        FRONT_DESK = 'front_desk', "FRONT_DESK"
        HOUSEKEEPING = 'housekeeping', "HOUSEKEEPING"
        MAINTENANCE = 'maintenance', "MAINTENANCE"
        RESTUARANT = 'restaurant', "RESTAURANT"
        INVENTORY = 'inventory', "INVENTORY"
        RESTUARANT_STAFF = 'restaurant_staff', "RESTUARANT_STAFF"

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
    note = models.TextField(blank=True, null=True)
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





class Menu(models.Model):

    CATEGORY_CHOICES = [
        ('BREAKFAST', 'Breakfast'),
        ('MAIN', 'Main Course'),
        ('APPETIZER', 'Appetizers'),
        ('DRINK', 'Drinks'),
        ('DESSERT', 'Desserts'),
    ]

    name = models.CharField(max_length=100)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    description = models.TextField(blank=True, null=True)

    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    imageUrl = models.ImageField(upload_to='menu_images/', blank=True, null=True)

    stock = models.PositiveIntegerField(default=0)
    low_stock_level = models.PositiveIntegerField(default=10)
    is_available = models.BooleanField(default=True)

    isBestSeller = models.BooleanField(default=False) 

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.price <= 0:
            raise ValidationError("Price must be greater than zero.")

    def deduct_stock(self, quantity=1):
        if quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        if self.stock < quantity:
            raise ValidationError("Insufficient stock.")

        self.stock -= quantity

        if self.stock == 0:
            self.is_available = False

        self.save(update_fields=["stock", "is_available"])

    def is_low_stock(self):
        return self.stock <= self.low_stock_level

    def __str__(self):
        return self.name
    


class Order(models.Model):

    class OrderType(models.TextChoices):
        DINE_IN = "dine_in", "Dine-in"
        ROOM_SERVICE = "room_service", "Room Service"

    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        PREPARING = "preparing", "Preparing"
        SERVED = "served", "Served"
        CANCELLED = "cancelled", "Cancelled"

    booking = models.ForeignKey(
        Booking,
        on_delete=models.CASCADE,
        related_name="orders",
        null=True,
        blank=True
    )

    order_type = models.CharField(
        max_length=20,
        choices=OrderType.choices,
        default=OrderType.DINE_IN
    )

    order_status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )

    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.order_type == self.OrderType.ROOM_SERVICE and not self.booking:
            raise ValidationError("Room service orders must be linked to a booking.")

    def __str__(self):
        return f"Order #{self.id} ({self.order_type})"



class OrderItem(models.Model):

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        related_name="items"
    )

    menu = models.ForeignKey(Menu, on_delete=models.PROTECT)

    menu_name = models.CharField(max_length=100)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    subtotal = models.DecimalField(max_digits=10, decimal_places=2)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def clean(self):
        if self.quantity is not None and self.quantity <= 0:
            raise ValidationError("Quantity must be greater than zero.")

        if self.price is not None and self.price <= 0:
            raise ValidationError("Price must be greater than zero.")


    def save(self, *args, **kwargs):
        # Snapshot values
        self.menu_name = self.menu.name
        self.price = self.menu.price

        self.subtotal = self.price * self.quantity
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.menu_name} x {self.quantity}"



