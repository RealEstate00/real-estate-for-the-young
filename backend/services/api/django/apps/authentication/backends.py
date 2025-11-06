"""
Custom authentication backend for email-based login
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend


User = get_user_model()


class EmailBackend(ModelBackend):
    """
    Custom authentication backend that allows users to log in using their email address
    instead of username
    """

    def authenticate(self, request, email=None, password=None, **kwargs):
        """
        Authenticate a user based on email address and password

        Args:
            request: HTTP request object
            email: User's email address
            password: User's password
            **kwargs: Additional keyword arguments

        Returns:
            User object if authentication successful, None otherwise
        """
        if email is None or password is None:
            return None

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Run the default password hasher once to reduce the timing
            # difference between an existing and a nonexistent user
            User().set_password(password)
            return None

        if user.check_password(password) and self.user_can_authenticate(user):
            return user

        return None

    def get_user(self, user_id):
        """
        Get user by ID

        Args:
            user_id: User's ID

        Returns:
            User object if exists, None otherwise
        """
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
