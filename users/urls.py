from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    UserRegistrationView, UserLoginView, UserLogoutView,
    UserProfileView, ChangePasswordView, ForgotPasswordView,
    ResetPasswordView, SendOTPView, VerifyOTPView
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
]