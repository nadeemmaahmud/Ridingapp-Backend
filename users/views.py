from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.shortcuts import render, HttpResponse
import random

from .serializers import (
    BasicUserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    DriverSerializer, SendOTPSerializer, VerifyOTPSerializer, DeleteAccountSerializer,
    GoogleLoginSerializer, FacebookLoginSerializer, PhoneNumberSerializer, UpdatePhoneNumberSerializer
)
from .email_utils import send_welcome_email, send_deletion_confirmation_email

User = get_user_model()

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            email_status = "No email address provided"
            if user.email:
                try:
                    email_sent, email_message = send_welcome_email(user)
                    if email_sent:
                        email_status = "Welcome email sent successfully"
                        print(f"✅ Welcome email sent to {user.email}")
                    else:
                        email_status = f"Failed to send welcome email: {email_message}"
                        print(f"❌ Failed to send welcome email: {email_message}")
                except Exception as e:
                    email_status = f"Exception sending welcome email: {str(e)}"
                    print(f"💥 Exception sending welcome email: {str(e)}")
            
            response_data = {
                'message': 'User registered successfully',
                'user': BasicUserSerializer(user).data,
            }
            
            if settings.DEBUG:
                response_data['email_status'] = email_status
            
            return Response(response_data, status=status.HTTP_201_CREATED)
        
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
        user.generate_otp()

        if user.email:
            try:
                send_mail(
                    'Account Deletion Verification - Riding App',
                    f'Your account deletion verification code is: {user.otp_code}\n\nThis code will expire in 10 minutes.\n\nIf you did not request account deletion, please ignore this email.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
            except Exception as e:
                return Response({
                    'error': 'Failed to send verification OTP'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        cache.set(f'delete_user_{user.id}', True, timeout=600)

        return Response({
            'message': 'Verification OTP sent. Please verify to complete account deletion.',
            'otp_code': user.otp_code if settings.DEBUG else None
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


class DeleteAccountView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        user = self.request.user
        serializer = DeleteAccountSerializer(data=request.data, context={'user': user})
        
        if serializer.is_valid():
            try:
                if user.email:
                    try:
                        email_sent, email_message = send_deletion_confirmation_email(user)
                        if not email_sent:
                            print(f"Failed to send deletion confirmation email: {email_message}")
                    except Exception as e:
                        print(f"Exception sending deletion confirmation email: {str(e)}")
                
                user.clear_otp()
                
                cache.delete(f'delete_user_{user.id}')
                
                user_id = user.id
                user.delete()
                
                return Response({
                    'message': 'Account deleted successfully'
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': 'Failed to delete account. Please try again.'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class GoogleLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        if serializer.is_valid():
            access_token = serializer.validated_data['access_token']
            
            try:
                import requests
                response = requests.get(
                    'https://www.googleapis.com/oauth2/v1/userinfo',
                    params={'access_token': access_token}
                )
                
                if response.status_code != 200:
                    return Response({
                        'error': 'Invalid Google access token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user_data = response.json()
                email = user_data.get('email')
                name = user_data.get('name', '')
                first_name = user_data.get('given_name', '')
                last_name = user_data.get('family_name', '')
                
                try:
                    user = User.objects.get(email=email)
                    created = False
                except User.DoesNotExist:
                    user = User.objects.create_user(
                        email=email,
                        username=email,
                        full_name=name or f"{first_name} {last_name}".strip(),
                        account_type='user',
                        is_verified=True
                    )
                    created = True
                
                refresh = RefreshToken.for_user(user)
                
                if created and user.email:
                    try:
                        send_welcome_email(user)
                    except Exception as e:
                        print(f"Failed to send welcome email: {str(e)}")
                
                return Response({
                    'message': 'Google login successful',
                    'user': BasicUserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'created': created
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Google authentication failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class FacebookLoginView(APIView):
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        serializer = FacebookLoginSerializer(data=request.data)
        if serializer.is_valid():
            access_token = serializer.validated_data['access_token']
            account_type = serializer.validated_data.get('account_type', 'user')
            
            try:
                import requests
                response = requests.get(
                    'https://graph.facebook.com/me',
                    params={
                        'access_token': access_token,
                        'fields': 'id,name,email,first_name,last_name'
                    }
                )
                
                if response.status_code != 200:
                    return Response({
                        'error': 'Invalid Facebook access token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                user_data = response.json()
                
                if 'error' in user_data:
                    return Response({
                        'error': 'Invalid Facebook access token'
                    }, status=status.HTTP_400_BAD_REQUEST)
                
                email = user_data.get('email')
                facebook_id = user_data.get('id')
                
                # If no email, create a fallback email using Facebook ID
                if not email:
                    if not facebook_id:
                        return Response({
                            'error': 'Facebook account must have either an email address or valid ID'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    # Create a unique email using Facebook ID
                    email = f"fb_{facebook_id}@facebook.user"
                
                name = user_data.get('name', '')
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                
                # Use Facebook ID as username if available, otherwise use email
                username = f"fb_{facebook_id}" if facebook_id else email
                
                try:
                    # Try to find user by email first, then by Facebook ID pattern
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
                        # Try to find by Facebook username pattern
                        if facebook_id:
                            user = User.objects.get(username=f"fb_{facebook_id}")
                        else:
                            raise User.DoesNotExist
                    created = False
                except User.DoesNotExist:
                    user = User.objects.create_user(
                        email=email,
                        username=username,
                        full_name=name or f"{first_name} {last_name}".strip(),
                        account_type=account_type,
                        is_verified=True
                    )
                    created = True
                
                refresh = RefreshToken.for_user(user)
                
                if created and user.email:
                    try:
                        send_welcome_email(user)
                    except Exception as e:
                        print(f"Failed to send welcome email: {str(e)}")
                
                return Response({
                    'message': 'Facebook login successful',
                    'user': BasicUserSerializer(user).data,
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                    'created': created
                }, status=status.HTTP_200_OK)
                
            except Exception as e:
                return Response({
                    'error': f'Facebook authentication failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PhoneNumberManagementView(APIView):
    """API endpoint for managing user phone numbers with country codes"""
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Get current user's phone number and available country codes"""
        from .country_codes import get_country_codes, get_country_by_phone_code
        
        user = request.user
        current_phone = user.phone_number
        current_country = None
        
        if current_phone:
            # Try to extract country code from current phone number
            for country in get_country_codes():
                if current_phone.startswith(country['phone_code']):
                    current_country = country
                    break
        
        return Response({
            'current_phone_number': current_phone,
            'current_country': current_country,
            'available_countries': get_country_codes(),
            'user_id': user.id
        }, status=status.HTTP_200_OK)
    
    def post(self, request):
        """Update user's phone number with country code"""
        serializer = UpdatePhoneNumberSerializer(
            instance=request.user,
            data=request.data,
            partial=True
        )
        
        if serializer.is_valid():
            user = serializer.save()
            
            return Response({
                'message': 'Phone number updated successfully',
                'phone_number': user.phone_number,
                'user': BasicUserSerializer(user).data
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Remove user's phone number"""
        user = request.user
        user.phone_number = None
        user.save()
        
        return Response({
            'message': 'Phone number removed successfully'
        }, status=status.HTTP_200_OK)