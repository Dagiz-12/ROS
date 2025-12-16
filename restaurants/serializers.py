from rest_framework import serializers
from .models import Restaurant, Branch
from accounts.serializers import UserSerializer


class RestaurantSerializer(serializers.ModelSerializer):
    branch_count = serializers.SerializerMethodField()
    active_branch_count = serializers.SerializerMethodField()

    class Meta:
        model = Restaurant
        fields = [
            'id', 'name', 'description', 'logo', 'address',
            'phone', 'email', 'config_json', 'is_active',
            'branch_count', 'active_branch_count', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at',
                            'branch_count', 'active_branch_count']

    def get_branch_count(self, obj):
        return obj.branches.count()

    def get_active_branch_count(self, obj):
        return obj.branches.filter(is_active=True).count()


class BranchSerializer(serializers.ModelSerializer):
    restaurant_name = serializers.CharField(
        source='restaurant.name', read_only=True)
    waiter_count = serializers.SerializerMethodField()
    table_count = serializers.SerializerMethodField()

    class Meta:
        model = Branch
        fields = [
            'id', 'restaurant', 'restaurant_name', 'name', 'location',
            'phone', 'settings', 'is_active', 'waiter_count', 'table_count',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at',
                            'updated_at', 'waiter_count', 'table_count']

    def get_waiter_count(self, obj):
        # This will be implemented when we have table model
        return 0

    def get_table_count(self, obj):
        # This will be implemented when we have table model
        return 0


class BranchCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Branch
        fields = ['restaurant', 'name', 'location',
                  'phone', 'settings', 'is_active']


class RestaurantCreateSerializer(serializers.ModelSerializer):
    initial_branch = BranchCreateSerializer(write_only=True, required=False)

    class Meta:
        model = Restaurant
        fields = [
            'name', 'description', 'logo', 'address', 'phone', 'email',
            'config_json', 'is_active', 'initial_branch'
        ]

    def create(self, validated_data):
        initial_branch_data = validated_data.pop('initial_branch', None)

        # Create restaurant
        restaurant = Restaurant.objects.create(**validated_data)

        # Create initial branch if provided
        if initial_branch_data:
            Branch.objects.create(restaurant=restaurant, **initial_branch_data)

        return restaurant
