import json
from rest_framework.viewsets import ViewSet

from api.models import Order, Menu, OrderItem, Payment

from api.serializers.menu_serializer import MenuSerializer, OrderSerializer
from rest_framework.response import Response
from rest_framework import status

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import extend_schema

from rest_framework import viewsets, mixins, parsers
from rest_framework.generics import ListAPIView
from rest_framework.permissions import IsAuthenticated
from django.db import transaction


class MenuView(ViewSet):
    def list(self, request):
        menus = Menu.objects.all()
        serializer = MenuSerializer(menus, many=True)
        return Response(serializer.data)
    
    def retrieve(self, request, pk=None):
        menu = get_object_or_404(Menu, pk=pk)
        serializer = MenuSerializer(menu)
        return Response(serializer.data)
    
    def create(self, request):
        serializer = MenuSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def patch(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk)
        serializer = MenuSerializer(menu, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
    
    def update(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk)
        serializer = MenuSerializer(menu, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)


    def delete(self, request, pk):
        menu = get_object_or_404(Menu, pk=pk)
        menu.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    




class OrderViewSet(viewsets.ViewSet):
    #permission_classes = [IsAuthenticated]

    def list(self, request):
        orders = Order.objects.all().order_by("-created_at")
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)
    

    def retrieve(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order)
        return Response(serializer.data)

    @transaction.atomic
    def create(self, request):
        serializer = OrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        items_data = serializer.validated_data.pop("items")

        # Create order first
        order = Order.objects.create(**serializer.validated_data)

        total_amount = 0
        additional_fee_items = []   # JSON for Booking.additional_fee
        description_parts = []      # Text for Payment.description

        for item in items_data:
            menu = item["menu"]
            quantity = item["quantity"]

            # Deduct stock
            menu.deduct_stock(quantity)

            price = menu.price
            subtotal = price * quantity

            # Create OrderItem
            OrderItem.objects.create(
                order=order,
                menu=menu,
                menu_name=menu.name,
                price=price,
                quantity=quantity,
                subtotal=subtotal,
            )

            total_amount += subtotal

            # For booking.additional_fee (JSON)
            additional_fee_items.append({
                "name": menu.name,
                "amount": float(subtotal),
            })

            # For payment.description (text)
            description_parts.append(f"{menu.name} x{quantity}")

        # Update order total
        order.total_amount = total_amount
        order.save(update_fields=["total_amount"])

        # ROOM SERVICE BILLING
        if order.order_type == Order.OrderType.ROOM_SERVICE and order.booking:
            booking = order.booking

            # Append to existing additional fees (never overwrite)
            existing_fees = booking.additional_fee or []
            existing_fees.extend(additional_fee_items)

            booking.additional_fee = existing_fees
            booking.save(update_fields=["additional_fee"])

            """             Payment.objects.create(
                booking=booking,
                amount=total_amount,
                payment_type=Payment.PaymentCategory.ADDITIONAL,
                status=Payment.PaymentStatus.PENDING,
                description=f"Restaurant order: {', '.join(description_parts)}",
            ) """

        return Response(
            OrderSerializer(order).data,
            status=status.HTTP_201_CREATED
        )

    @transaction.atomic
    def update(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderSerializer(order, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        return Response(serializer.data)

    def patch(self, request, pk=None):
        return self.update(request, pk)
    
    def destroy(self, request, pk=None):
        try:
            order = Order.objects.get(pk=pk)
        except Order.DoesNotExist:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        order.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    














