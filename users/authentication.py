from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import AuthenticationFailed
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

class CustomJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        orig_iat = validated_token.get('orig_iat')
        if hasattr(user, 'last_password_change') and user.last_password_change:
            if orig_iat and timezone.make_aware(timezone.datetime.fromtimestamp(orig_iat)) < user.last_password_change:
                raise AuthenticationFailed('Access token is invalid due to password change.')
        return user
