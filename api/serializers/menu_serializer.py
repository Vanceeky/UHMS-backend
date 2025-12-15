from rest_framework import serializers

from api.models import Menu, Order, OrderItem



class MenuSerializer(serializers.ModelSerializer):
    class Meta:
        model = Menu
        fields = '__all__'



class OrderItemSerializer(serializers.ModelSerializer):
    menu_id = serializers.PrimaryKeyRelatedField(
        queryset=Menu.objects.all(), source='menu', write_only=True
    )

    class Meta:
        model = OrderItem
        fields = ['id', 'menu_id', 'menu_name', 'price', 'quantity', 'subtotal']
        read_only_fields = ['id', 'menu_name', 'price', 'subtotal']

    def create(self, validated_data):
        menu = validated_data.pop('menu')
        quantity = validated_data['quantity']

        # Deduct stock
        menu.deduct_stock(quantity)

        # Snapshot
        validated_data['menu_name'] = menu.name
        validated_data['price'] = menu.price
        validated_data['subtotal'] = menu.price * quantity

        return OrderItem.objects.create(menu=menu, **validated_data)


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True)

    class Meta:
        model = Order
        fields = ['id', 'booking', 'order_type', 'order_status', 'total_amount', 'items', 'created_at', 'updated_at']
        read_only_fields = ['id', 'total_amount', 'created_at', 'updated_at']

    def validate(self, attrs):
        if attrs.get('order_type') == Order.OrderType.ROOM_SERVICE and not attrs.get('booking'):
            raise serializers.ValidationError("Room service orders must be linked to a booking.")
        return attrs
    

