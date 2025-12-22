from rest_framework_simplejwt.serializers import TokenObtainPairSerializer, TokenRefreshSerializer

from rest_framework_simplejwt.tokens import RefreshToken

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['role'] = user.role
        token['username'] = user.username
        token['email'] = user.email

        return token
    

class CustomTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        data = super().validate(attrs)

        
        refresh = RefreshToken(attrs['refresh'])
        user = self.context['request'].user  # This may be None if user isn't authenticated

        
        from django.contrib.auth import get_user_model
        User = get_user_model()
        try:
            user_id = refresh['user_id']
            user = User.objects.get(id=user_id)
        except Exception:
            user = None

        if user:
            data['role'] = user.role
            data['username'] = user.username
            data['email'] = user.email

        return data