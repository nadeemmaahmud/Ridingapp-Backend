from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, ChangePasswordView, ForgotPasswordView,
    ResetPasswordView, SendOTPView, VerifyOTPView, DeleteAccountView,
    ConfirmDeleteAccountView, GoogleLoginView, FacebookLoginView
)

urlpatterns = [
    path('token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    path('register/', UserRegistrationView.as_view(), name='user-registration'),
    path('login/', UserLoginView.as_view(), name='user-login'),
    path('logout/', UserLogoutView.as_view(), name='user-logout'),
    path('profile/', UserProfileView.as_view(), name='user-profile'),
    path('change-password/', ChangePasswordView.as_view(), name='change-password'),
    path('forgot-password/', ForgotPasswordView.as_view(), name='forgot-password'),
    path('reset-password/', ResetPasswordView.as_view(), name='reset-password'),
    path('send-otp/', SendOTPView.as_view(), name='send-otp'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('delete-account/', DeleteAccountView.as_view(), name='delete-account'),
    path('confirm-delete-account/', ConfirmDeleteAccountView.as_view(), name='confirm-delete-account'),
    path('auth/google/', GoogleLoginView.as_view(), name='google-login'),
    path('auth/facebook/', FacebookLoginView.as_view(), name='facebook-login'),
]