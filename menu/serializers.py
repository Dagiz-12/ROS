from rest_framework import serializers
from .models import Category, MenuItem
from restaurants.models import Restaurant


class CategorySerializer(serializers.ModelSerializer):
    item_count = serializers.SerializerMethodField()
    available_item_count = serializers.SerializerMethodField()

    class Meta:
        model = Category
        fields = [
            'id', 'restaurant', 'name', 'description',
            'order_index', 'is_active', 'item_count',
            'available_item_count', 'created_at'
        ]
        read_only_fields = ['id', 'created_at',
                            'item_count', 'available_item_count']

    def get_item_count(self, obj):
        return obj.items.count()

    def get_available_item_count(self, obj):
        return obj.items.filter(is_available=True).count()


class MenuItemSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(
        source='category.name', read_only=True)
    restaurant_name = serializers.CharField(
        source='category.restaurant.name', read_only=True)

    class Meta:
        model = MenuItem
        fields = [
            'id', 'category', 'category_name', 'restaurant_name',
            'name', 'description', 'price', 'image',
            'preparation_time', 'is_available', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class MenuItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MenuItem
        fields = [
            'category', 'name', 'description', 'price',
            'image', 'preparation_time', 'is_available'
        ]

    def validate_price(self, value):
        if value < 0:
            raise serializers.ValidationError("Price cannot be negative")
        return value

    def validate_preparation_time(self, value):
        if value < 1:
            raise serializers.ValidationError(
                "Preparation time must be at least 1 minute")
        return value


class CategoryWithItemsSerializer(serializers.ModelSerializer):
    items = MenuItemSerializer(many=True, read_only=True)

    class Meta:
        model = Category
        fields = ['id', 'name', 'description',
                  'order_index', 'is_active', 'items']


class RestaurantMenuSerializer(serializers.ModelSerializer):
    categories = CategoryWithItemsSerializer(
        many=True, source='category_set', read_only=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'categories']


class MenuItemBulkUpdateSerializer(serializers.Serializer):
    items = serializers.ListField(
        child=serializers.DictField(),
        required=True
    )

    def validate_items(self, value):
        for item in value:
            if 'id' not in item:
                raise serializers.ValidationError(
                    "Each item must have an 'id' field")
            if 'price' in item and item['price'] < 0:
                raise serializers.ValidationError("Price cannot be negative")
        return value


class MenuSearchSerializer(serializers.Serializer):
    query = serializers.CharField(required=True, max_length=100)
    category_id = serializers.IntegerField(required=False, allow_null=True)
    min_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0)
    max_price = serializers.DecimalField(
        required=False, max_digits=10, decimal_places=2, min_value=0)
    available_only = serializers.BooleanField(default=True)
