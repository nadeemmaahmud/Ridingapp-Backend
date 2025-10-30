from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
import random

from .serializers import (
    BasicUserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    DriverSerializer, SendOTPSerializer, VerifyOTPSerializer,
)

User = get_user_model()

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'message': 'User registered successfully',
                'user': BasicUserSerializer(user).data,
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data['user']
            refresh = RefreshToken.for_user(user)
            
            return Response({
                'message': 'Login successful',
                'user': BasicUserSerializer(user).data,
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        try:
            refresh_token = request.data["refresh"]
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response({
                'message': 'Logout successful'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Something went wrong'
            }, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Password changed successfully'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            
            user = None
            try:
                if '@' in email_or_phone:
                    user = User.objects.get(email=email_or_phone)
                else:
                    user = User.objects.get(phone_number=email_or_phone)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user.generate_otp()
            
            if user.email:
                try:
                    send_mail(
                        'Password Reset OTP - Riding App',
                        f'Your password reset verification code is: {user.otp_code}\n\nThis code will expire in 10 minutes.\n\nIf you did not request a password reset, please ignore this email.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    return Response({
                        'error': 'Failed to send OTP via email'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                pass
            
            return Response({
                'message': 'OTP sent successfully for password reset',
                'otp_code': user.otp_code if settings.DEBUG else None
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ResetPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ResetPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            otp_code = serializer.validated_data['otp_code']
            new_password = serializer.validated_data['new_password']
            
            user = None
            try:
                if '@' in email_or_phone:
                    user = User.objects.get(email=email_or_phone)
                else:
                    user = User.objects.get(phone_number=email_or_phone)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if user.verify_otp(otp_code):
                user.set_password(new_password)
                user.save()
                
                user.clear_otp()
                
                return Response({
                    'message': 'Password reset successfully'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid or expired OTP'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        user = self.request.user
        if user.account_type == 'driver':
            return DriverSerializer
        return BasicUserSerializer

    def get(self, request):
        user = self.request.user
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(user)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    def put(self, request):
        user = self.request.user
        serializer_class = self.get_serializer_class()
        serializer = serializer_class(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Profile updated successfully',
                'user': serializer.data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        user = self.request.user
        user.delete()
        return Response({
            'message': 'User deleted successfully'
        }, status=status.HTTP_200_OK)

class SendOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            
            user = None
            try:
                if '@' in email_or_phone:
                    user = User.objects.get(email=email_or_phone)
                else:
                    user = User.objects.get(phone_number=email_or_phone)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user.generate_otp()
            if user.email:
                try:
                    send_mail(
                        'Your OTP Code - Riding App',
                        f'Your verification code is: {user.otp_code}\n\nThis code will expire in 10 minutes.',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=False,
                    )
                except Exception as e:
                    return Response({
                        'error': 'Failed to send OTP via email'
                    }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            else:
                pass
            
            return Response({
                'message': 'OTP sent successfully',
                'otp_code': user.otp_code if settings.DEBUG else None
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            otp_code = serializer.validated_data['otp_code']
            
            user = None
            try:
                if '@' in email_or_phone:
                    user = User.objects.get(email=email_or_phone)
                else:
                    user = User.objects.get(phone_number=email_or_phone)
            except User.DoesNotExist:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            if user.verify_otp(otp_code):
                user.is_verified = True
                user.save()
                
                user.clear_otp()
                
                refresh = RefreshToken.for_user(user)
                
                return Response({
                    'message': 'OTP verified successfully',
                    'access': str(refresh.access_token),
                    'refresh': str(refresh),
                    'user': BasicUserSerializer(user).data
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Invalid or expired OTP'
                }, status=status.HTTP_400_BAD_REQUEST)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)