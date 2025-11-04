"""
Authentication serializers
"""
from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    """User serializer"""

    class Meta:
        model = User
        fields = [
            'id', 'email', 'username', 'full_name',
            'is_active', 'is_verified', 'created_at', 'last_login'
        ]
        read_only_fields = ['id', 'created_at', 'last_login']


class UserRegisterSerializer(serializers.ModelSerializer):
    """User registration serializer"""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ['email', 'username', 'password', 'password_confirm', 'full_name']

    def validate(self, attrs):
        """Validate that passwords match"""
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def create(self, validated_data):
        """Create user with hashed password"""
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserLoginSerializer(serializers.Serializer):
    """User login serializer"""

    email = serializers.EmailField(required=True)
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )
