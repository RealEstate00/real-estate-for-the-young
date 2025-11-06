"""
Authentication views
"""
from rest_framework import status, generics
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from django.utils import timezone
from .serializers import UserSerializer, UserRegisterSerializer, UserLoginSerializer

User = get_user_model()


@api_view(['POST'])
@permission_classes([AllowAny])
def register_view(request):
    """
    User registration endpoint

    POST /api/auth/register/
    """
    serializer = UserRegisterSerializer(data=request.data)

    if serializer.is_valid():
        user = serializer.save()

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)

        return Response({
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'token_type': 'bearer',
            'user': UserSerializer(user).data
        }, status=status.HTTP_201_CREATED)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    User login endpoint

    POST /api/auth/login/
    """
    serializer = UserLoginSerializer(data=request.data)

    if not serializer.is_valid():
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    email = serializer.validated_data['email']
    password = serializer.validated_data['password']

    # Authenticate user
    user = authenticate(request, email=email, password=password)

    if user is None:
        return Response(
            {'detail': 'Invalid email or password'},
            status=status.HTTP_401_UNAUTHORIZED
        )

    if not user.is_active:
        return Response(
            {'detail': 'Account is inactive'},
            status=status.HTTP_403_FORBIDDEN
        )

    # Update last login
    user.last_login = timezone.now()
    user.save(update_fields=['last_login'])

    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)

    return Response({
        'access_token': str(refresh.access_token),
        'refresh_token': str(refresh),
        'token_type': 'bearer',
        'user': UserSerializer(user).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    User logout endpoint (optional - mainly for token blacklisting)

    POST /api/auth/logout/
    """
    try:
        refresh_token = request.data.get('refresh_token')
        if refresh_token:
            token = RefreshToken(refresh_token)
            token.blacklist()

        return Response({'detail': 'Successfully logged out'})
    except Exception:
        return Response(
            {'detail': 'Invalid token'},
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def me_view(request):
    """
    Get current user info

    GET /api/auth/me/
    """
    serializer = UserSerializer(request.user)
    return Response(serializer.data)


class UserDetailView(generics.RetrieveAPIView):
    """
    Get user by ID (public info only)

    GET /api/auth/users/{id}/
    """
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserSerializer
    permission_classes = [AllowAny]
