from tables.models import Order, OrderItem, Table
from menu.models import MenuItem


class OrderManager:
    """Manager class for consistent order operations"""

    @staticmethod
    def create_order_with_items(table, order_type, items_data, **kwargs):
        """
        Create an order with items consistently.

        Args:
            table: Table object
            order_type: 'waiter', 'qr', or 'online'
            items_data: List of dicts with menu_item, quantity, special_instructions
            **kwargs: Additional order fields (customer_name, notes, etc.)

        Returns:
            Order object
        """
        # Determine initial status
        status_map = {
            'qr': 'pending',
            'waiter': 'confirmed',
            'online': 'pending'
        }

        requires_waiter_confirmation_map = {
            'qr': True,
            'waiter': False,
            'online': False
        }

        # Update table status to occupied when order is created
        if order_type == 'waiter':
            table.status = 'occupied'
            table.save()

        # Prepare order data
        order_data = {
            'table': table,
            'order_type': order_type,
            'status': status_map.get(order_type, 'pending'),
            'requires_waiter_confirmation': requires_waiter_confirmation_map.get(order_type, True),
            **kwargs
        }

        # Add waiter for waiter orders
        if order_type == 'waiter' and 'waiter' in kwargs:
            order_data['waiter'] = kwargs['waiter']

        # Create order
        order = Order.objects.create(**order_data)

        # Add order items
        OrderManager._add_order_items(order, items_data)

        # Calculate totals
        order.calculate_totals()

        return order

    @staticmethod
    def _add_order_items(order, items_data):
        """Add items to order with validation"""
        items_added = 0

        for item_data in items_data:
            try:
                menu_item = MenuItem.objects.get(
                    id=item_data['menu_item'],
                    is_available=True
                )

                OrderItem.objects.create(
                    order=order,
                    menu_item=menu_item,
                    quantity=item_data['quantity'],
                    special_instructions=item_data.get(
                        'special_instructions', ''),
                    unit_price=menu_item.price  # Explicitly set unit_price
                )
                items_added += 1

            except MenuItem.DoesNotExist:
                # Log the error but continue with other items
                print(
                    f"Warning: MenuItem {item_data['menu_item']} not found or not available")
                continue

        if items_added == 0:
            order.delete()
            raise ValueError("No valid items were added to the order")

        return items_added

    @staticmethod
    def create_from_cart(cart, **kwargs):
        """Create order from existing cart"""
        order_data = {
            'table': cart.table,
            'order_type': kwargs.get('order_type', 'qr'),
            'customer_name': kwargs.get('customer_name', ''),
            'notes': kwargs.get('notes', ''),
            **kwargs
        }

        # Update table status for QR orders too
        if order_data['order_type'] == 'qr':
            cart.table.status = 'occupied'
            cart.table.save()

        order = Order.objects.create(**order_data)

        # Transfer cart items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                menu_item=cart_item.menu_item,
                quantity=cart_item.quantity,
                special_instructions=cart_item.special_instructions,
                unit_price=cart_item.menu_item.price  # Explicitly set unit_price
            )

        # Deactivate cart
        cart.is_active = False
        cart.save()

        # Calculate totals
        order.calculate_totals()

        return order

    @staticmethod
    def update_table_status(order, new_status):
        """Update table status based on order status"""
        table = order.table

        # Define when to change table status
        if new_status in ['served', 'completed', 'cancelled']:
            # Meal is done, table becomes available for cleaning
            table.status = 'cleaning'
        elif new_status == 'ready':
            # Food is ready, table is still occupied
            table.status = 'occupied'
        elif new_status == 'preparing':
            # Food is being prepared, table is still occupied
            table.status = 'occupied'
        elif new_status == 'confirmed':
            # Order confirmed, table is occupied
            table.status = 'occupied'
        elif new_status == 'pending':
            # QR order pending, table is still available? Or should it be reserved?
            table.status = 'occupied'  # Safer to mark as occupied

        table.save()
        return table
