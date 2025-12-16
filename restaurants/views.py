from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django_filters.rest_framework import DjangoFilterBackend

from .models import Restaurant, Branch
from .serializers import (
    RestaurantSerializer, RestaurantCreateSerializer,
    BranchSerializer, BranchCreateSerializer
)
from accounts.permissions import IsAdminUser, IsManagerOrAdmin


class RestaurantViewSet(viewsets.ModelViewSet):
    """ViewSet for restaurant management"""
    queryset = Restaurant.objects.all()
    permission_classes = [IsAuthenticated, IsAdminUser]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['name', 'email', 'phone']
    ordering_fields = ['name', 'created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return RestaurantCreateSerializer
        return RestaurantSerializer

    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            # Allow any authenticated user to view restaurants
            return [IsAuthenticated()]
        return super().get_permissions()

    @action(detail=True, methods=['get'])
    def branches(self, request, pk=None):
        """Get all branches for a specific restaurant"""
        restaurant = self.get_object()
        branches = restaurant.branches.all()
        serializer = BranchSerializer(branches, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def add_branch(self, request, pk=None):
        """Add a new branch to restaurant"""
        restaurant = self.get_object()
        serializer = BranchCreateSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save(restaurant=restaurant)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['get'])
    def stats(self, request, pk=None):
        """Get restaurant statistics"""
        restaurant = self.get_object()

        stats = {
            'total_branches': restaurant.branches.count(),
            'active_branches': restaurant.branches.filter(is_active=True).count(),
            'total_staff': 0,  # Will implement when we link users
            'average_rating': 0,  # Will implement rating system
            'monthly_revenue': 0,  # Will implement in Phase 4
        }

        return Response(stats)


class BranchViewSet(viewsets.ModelViewSet):
    """ViewSet for branch management"""
    queryset = Branch.objects.all()
    serializer_class = BranchSerializer
    permission_classes = [IsAuthenticated, IsManagerOrAdmin]
    filter_backends = [DjangoFilterBackend,
                       filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['restaurant', 'is_active']
    search_fields = ['name', 'location', 'phone']
    ordering_fields = ['name', 'created_at']

    def get_serializer_class(self):
        if self.action == 'create':
            return BranchCreateSerializer
        return BranchSerializer

    def get_queryset(self):
        user = self.request.user

        # Admin can see all branches
        if user.role == 'admin':
            return Branch.objects.all()

        # Manager can see branches from their restaurant
        elif user.role == 'manager':
            if user.restaurant:
                return Branch.objects.filter(restaurant=user.restaurant)

        # Other roles can only see their assigned branch
        elif user.branch:
            return Branch.objects.filter(id=user.branch.id)

        return Branch.objects.none()

    @action(detail=True, methods=['get'])
    def staff(self, request, pk=None):
        """Get staff assigned to this branch"""
        branch = self.get_object()
        # Will implement when we link users to branches
        return Response({"message": "Will implement in Phase 2"}, status=status.HTTP_200_OK)

    @action(detail=True, methods=['post'])
    def toggle_active(self, request, pk=None):
        """Toggle branch active status"""
        branch = self.get_object()
        branch.is_active = not branch.is_active
        branch.save()

        status_text = 'activated' if branch.is_active else 'deactivated'
        return Response({
            'success': True,
            'message': f'Branch {status_text} successfully',
            'is_active': branch.is_active
        })

# Simplified Views for specific use cases


class MyRestaurantView(viewsets.GenericViewSet):
    """View for current user's restaurant"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get restaurant of current user"""
        user = request.user

        if user.role == 'admin':
            # Admin can see all restaurants
            restaurants = Restaurant.objects.all()
            serializer = RestaurantSerializer(restaurants, many=True)
            return Response(serializer.data)

        elif user.restaurant:
            # Return user's restaurant
            serializer = RestaurantSerializer(user.restaurant)
            return Response(serializer.data)

        return Response({
            'message': 'No restaurant assigned'
        }, status=status.HTTP_404_NOT_FOUND)


class MyBranchView(viewsets.GenericViewSet):
    """View for current user's branch"""
    permission_classes = [IsAuthenticated]

    def list(self, request):
        """Get branch of current user"""
        user = request.user

        if user.branch:
            serializer = BranchSerializer(user.branch)
            return Response(serializer.data)

        return Response({
            'message': 'No branch assigned'
        }, status=status.HTTP_404_NOT_FOUND)
