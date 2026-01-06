# inventory/serializers.py
from rest_framework import serializers
from .models import StockItem, StockTransaction, StockAlert, Recipe, InventoryReport
from restaurants.serializers import RestaurantSerializer, BranchSerializer
from accounts.serializers import UserSerializer


class StockItemSerializer(serializers.ModelSerializer):
    restaurant = RestaurantSerializer(read_only=True)
    branch = BranchSerializer(read_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    stock_value = serializers.DecimalField(
        max_digits=12, decimal_places=2, read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    needs_reorder = serializers.BooleanField(read_only=True)

    class Meta:
        model = StockItem
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at', 'last_purchase_price']


class StockTransactionSerializer(serializers.ModelSerializer):
    stock_item = StockItemSerializer(read_only=True)
    stock_item_id = serializers.IntegerField(write_only=True)

    user = UserSerializer(read_only=True)
    user_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    order_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)
    menu_item_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    class Meta:
        model = StockTransaction
        fields = '__all__'
        read_only_fields = ['created_at']


class StockAlertSerializer(serializers.ModelSerializer):
    stock_item = StockItemSerializer(read_only=True)
    stock_item_id = serializers.IntegerField(write_only=True)

    resolved_by = UserSerializer(read_only=True)
    resolved_by_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    class Meta:
        model = StockAlert
        fields = '__all__'
        read_only_fields = ['created_at', 'resolved_at']


class RecipeSerializer(serializers.ModelSerializer):
    menu_item = serializers.StringRelatedField(read_only=True)
    menu_item_id = serializers.IntegerField(write_only=True)

    stock_item = StockItemSerializer(read_only=True)
    stock_item_id = serializers.IntegerField(write_only=True)

    ingredient_cost = serializers.DecimalField(
        max_digits=10, decimal_places=2, read_only=True)
    adjusted_quantity = serializers.DecimalField(
        max_digits=10, decimal_places=3, read_only=True)

    class Meta:
        model = Recipe
        fields = '__all__'
        read_only_fields = ['created_at', 'updated_at']


class InventoryReportSerializer(serializers.ModelSerializer):
    generated_by = UserSerializer(read_only=True)
    generated_by_id = serializers.IntegerField(write_only=True)

    restaurant = RestaurantSerializer(read_only=True)
    restaurant_id = serializers.IntegerField(write_only=True)
    branch_id = serializers.IntegerField(
        write_only=True, required=False, allow_null=True)

    class Meta:
        model = InventoryReport
        fields = '__all__'
        read_only_fields = ['created_at']
