from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.db.models import Q

User = get_user_model()


class EmailOrUsernameModelBackend(ModelBackend):
    def authenticate(self, request, username=None, password=None, **kwargs):
        try:
            # Try to fetch user by username or email
            user = User.objects.get(
                Q(username=username) | Q(email=username)
            )

            if user.check_password(password):
                return user
        except User.DoesNotExist:
            return None
        except User.MultipleObjectsReturned:
            # Handle case where email and username might be the same
            users = User.objects.filter(
                Q(username=username) | Q(email=username)
            )
            for user in users:
                if user.check_password(password):
                    return user
            return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
