from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend
from django.db.models import Q

from .models import Category, MenuItem
from .serializers import (
    CategorySerializer, MenuItemSerializer, MenuItemCreateSerializer,
    CategoryWithItemsSerializer, RestaurantMenuSerializer,
    MenuItemBulkUpdateSerializer, MenuSearchSerializer
)
from restaurants.models import Restaurant
from accounts.permissions import IsAdminUser, IsManagerOrAdmin, IsChefOrHigher


class CategoryViewSet(viewsets.ModelViewSet):
    """ViewSet for category management"""
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAuthenticated, IsChefOrHigher]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['restaurant', 'is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['order_index', 'name', 'created_at']

    def get_queryset(self):
        user = self.request.user

        # Admin can see all categories
        if user.role == 'admin':
            return Category.objects.all()

        # Manager/Chef can see categories from their restaurant
        elif user.role in ['manager', 'chef']:
            if user.restaurant:
                return Category.objects.filter(restaurant=user.restaurant)

        return Category.objects.none()

    @action(detail=True, methods=['get'])
    def items(self, request, pk=None):
        """Get all items in a category"""
        category = self.get_object()
        items = category.items.all()

        # Filter by availability if requested
        available_only = request.query_params.get(
            'available_only', 'true').lower() == 'true'
        if available_only:
            items = items.filter(is_available=True)

        serializer = MenuItemSerializer(items, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['post'])
    def reorder(self, request):
        """Reorder categories"""
        order_data = request.data.get('order', [])

        for index, category_id in enumerate(order_data):
            Category.objects.filter(id=category_id).update(order_index=index)

        return Response({'success': True, 'message': 'Categories reordered'})


class MenuItemViewSet(viewsets.ModelViewSet):
    """ViewSet for menu item management"""
    queryset = MenuItem.objects.all()
    permission_classes = [IsAuthenticated, IsChefOrHigher]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['category', 'is_available']
    search_fields = ['name', 'description']
    ordering_fields = ['name', 'price', 'created_at']

    def get_serializer_class(self):
        if self.action in ['create', 'update', 'partial_update']:
            return MenuItemCreateSerializer
        return MenuItemSerializer

    def get_queryset(self):
        user = self.request.user
        queryset = MenuItem.objects.all()

        # Filter by restaurant for non-admin users
        if user.role != 'admin':
            if user.restaurant:
                queryset = queryset.filter(
                    category__restaurant=user.restaurant)
            else:
                queryset = MenuItem.objects.none()

        return queryset

    @action(detail=False, methods=['post'])
    def bulk_update(self, request):
        """Bulk update menu items (prices, availability)"""
        serializer = MenuItemBulkUpdateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        updated_items = []
        errors = []

        for item_data in serializer.validated_data['items']:
            try:
                item = MenuItem.objects.get(id=item_data['id'])

                # Update fields if provided
                for field in ['price', 'is_available', 'preparation_time']:
                    if field in item_data:
                        setattr(item, field, item_data[field])

                item.save()
                updated_items.append(item.id)

            except MenuItem.DoesNotExist:
                errors.append(f"Item with id {item_data['id']} not found")
            except Exception as e:
                errors.append(
                    f"Error updating item {item_data['id']}: {str(e)}")

        return Response({
            'success': True,
            'updated_items': updated_items,
            'errors': errors,
            'message': f'Updated {len(updated_items)} items'
        })

    @action(detail=False, methods=['get'])
    def search(self, request):
        """Search menu items with filters"""
        serializer = MenuSearchSerializer(data=request.query_params)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        data = serializer.validated_data
        queryset = self.get_queryset()

        # Apply search query
        if data.get('query'):
            queryset = queryset.filter(
                Q(name__icontains=data['query']) |
                Q(description__icontains=data['query'])
            )

        # Filter by category
        if data.get('category_id'):
            queryset = queryset.filter(category_id=data['category_id'])

        # Filter by price range
        if data.get('min_price'):
            queryset = queryset.filter(price__gte=data['min_price'])
        if data.get('max_price'):
            queryset = queryset.filter(price__lte=data['max_price'])

        # Filter by availability
        if data.get('available_only', True):
            queryset = queryset.filter(is_available=True)

        # Apply ordering
        queryset = queryset.order_by('name')

        page = self.paginate_queryset(queryset)
        if page is not None:
            serializer = MenuItemSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = MenuItemSerializer(queryset, many=True)
        return Response(serializer.data)


class PublicMenuView(APIView):
    """Public view for restaurant menu (no authentication required)"""
    permission_classes = []

    def get(self, request, restaurant_id):
        """Get complete menu for a restaurant"""
        try:
            restaurant = Restaurant.objects.get(
                id=restaurant_id, is_active=True)

            # Get categories with items
            categories = Category.objects.filter(
                restaurant=restaurant,
                is_active=True
            ).prefetch_related('items').order_by('order_index')

            # Filter to only include available items
            for category in categories:
                category.items = category.items.filter(is_available=True)

            serializer = CategoryWithItemsSerializer(categories, many=True)

            return Response({
                'restaurant': {
                    'id': restaurant.id,
                    'name': restaurant.name,
                    'description': restaurant.description
                },
                'categories': serializer.data
            })

        except Restaurant.DoesNotExist:
            return Response(
                {'error': 'Restaurant not found or inactive'},
                status=status.HTTP_404_NOT_FOUND
            )


class RestaurantMenuView(viewsets.GenericViewSet):
    """View for restaurant-specific menu operations"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get menu for user's restaurant"""
        user = request.user

        if not user.restaurant:
            return Response(
                {'error': 'No restaurant assigned'},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Get all active categories with items
        categories = Category.objects.filter(
            restaurant=user.restaurant,
            is_active=True
        ).prefetch_related('items').order_by('order_index')

        # Filter items based on user role
        show_unavailable = user.role in ['admin', 'manager', 'chef']

        if not show_unavailable:
            for category in categories:
                category.items = category.items.filter(is_available=True)

        serializer = CategoryWithItemsSerializer(categories, many=True)

        return Response({
            'restaurant': {
                'id': user.restaurant.id,
                'name': user.restaurant.name
            },
            'show_unavailable': show_unavailable,
            'categories': serializer.data
        })
