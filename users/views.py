from rest_framework import status, generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.conf import settings
from django.core.cache import cache
from django.contrib import messages
from twilio.rest import Client
import os

from .serializers import (
    BasicUserSerializer, UserRegistrationSerializer, UserLoginSerializer,
    ChangePasswordSerializer, ForgotPasswordSerializer, ResetPasswordSerializer,
    DriverSerializer, SendOTPSerializer, VerifyOTPSerializer, DeleteAccountSerializer,
    GoogleLoginSerializer, FacebookLoginSerializer
)

from .email_utils import send_welcome_email, send_deletion_confirmation_email, send_deletion_otp_email, send_password_reset_otp_email

User = get_user_model()

def get_user_by_identifier(identifier):
    try:
        if '@' in identifier:
            return User.objects.get(email=identifier)
        else:
            return User.objects.get(phone_number=identifier)
    except User.DoesNotExist:
        return None

def send_otp_verification(user, purpose='general'):
    if hasattr(user, 'phone_number') and user.phone_number:
        if purpose == 'password_reset':
            message_body = f'Your Riding App password reset code is: {user.otp_code}\n\nThis code will expire in 10 minutes.\n\nIf you did not request this, please ignore.'
        elif purpose == 'deletion':
            message_body = f"Your account deletion verification code is: {user.otp_code}. This code will expire in 10 minutes."
        else:
            message_body = f'Your Riding App verification code is: {user.otp_code}\n\nThis code will expire in 10 minutes.'
        
        try:
            client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
            client.messages.create(
                body=message_body,
                from_=settings.TWILIO_PHONE_NUMBER,
                to=user.phone_number
            )
            return True, "SMS sent successfully"
        except Exception as e:
            return False, f"Failed to send SMS: {str(e)}"
    
    elif user.email:
        try:
            if purpose == 'password_reset':
                email_sent, email_message = send_password_reset_otp_email(user)
            elif purpose == 'deletion':
                email_sent, email_message = send_deletion_otp_email(user)
            else:
                send_mail(
                    'Your OTP Code - Riding App',
                    f'Your verification code is: {user.otp_code}\n\nThis code will expire in 10 minutes.',
                    settings.DEFAULT_FROM_EMAIL,
                    [user.email],
                    fail_silently=False,
                )
                return True, "Email sent successfully"
            
            return email_sent, email_message
        except Exception as e:
            return False, f"Failed to send email: {str(e)}"
    
    else:
        return False, "User has no email or phone number"

class UserRegistrationView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            
            email_status = "No email address provided"
            phone_status = "No phone number provided"
            
            if user.email:
                try:
                    email_sent, email_message = send_welcome_email(user)
                    if email_sent:
                        email_status = "Welcome email sent successfully"
                        print(f"Welcome email sent to {user.email}")
                    else:
                        email_status = f"Failed to send welcome email: {email_message}"
                        print(f"Failed to send welcome email: {email_message}")
                except Exception as e:
                    email_status = f"Exception sending welcome email: {str(e)}"
                    print(f"Exception sending welcome email: {str(e)}")

            elif user.phone_number:
                try:
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    twilio_message = client.messages.create(
                        body=f"Account created successfully! Welcome to Riding App. Your account is ready to use.",
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=user.phone_number
                    )
                    phone_status = "Welcome SMS sent successfully"
                    print(f"Welcome SMS sent to {user.phone_number}")
                except Exception as e:
                    phone_status = "SMS service temporarily unavailable"
                    print(f"SMS Error for {user.phone_number}: {str(e)}")
            
            response_data = {
                'message': 'User registered successfully',
                'user': BasicUserSerializer(user).data,
            }
            
            if settings.DEBUG:
                if user.email:
                    response_data['email_status'] = email_status
                elif user.phone_number:
                    response_data['phone_status'] = phone_status

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
            refresh_token = request.data.get("refresh")
            
            if not refresh_token:
                return Response({
                    'message': 'Logout successful (client-side logout)',
                    'note': 'Please remove tokens from client storage'
                }, status=status.HTTP_200_OK)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'message': 'Logout successful (server-side logout)',
                'note': 'Refresh token has been blacklisted'
            }, status=status.HTTP_200_OK)
            
        except Exception as e:
            print(f"Logout error: {str(e)}")
            
            if "token_blacklist" in str(e).lower():
                return Response({
                    'error': 'Token blacklist not configured properly'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            elif "invalid" in str(e).lower() or "expired" in str(e).lower():
                return Response({
                    'message': 'Logout successful',
                    'note': 'Token was already invalid or expired'
                }, status=status.HTTP_200_OK)
            else:
                return Response({
                    'error': 'Logout failed. Please try again.',
                    'debug_info': str(e) if settings.DEBUG else None
                }, status=status.HTTP_400_BAD_REQUEST)

class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            user = serializer.save()
            from django.utils import timezone
            user.last_password_change = timezone.now()
            user.save()
            
            if user.email:
                try:
                    send_mail(
                        'Password Changed - Riding App',
                        f'Dear {user.get_full_name() or user.username},\n\nYour password has been successfully changed.\n\nIf you did not make this change, please contact our support team immediately.\n\nBest regards,\nThe Riding App Team',
                        settings.DEFAULT_FROM_EMAIL,
                        [user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    print(f"Failed to send password change notification: {str(e)}")
            elif user.phone_number:
                try:
                    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
                    client.messages.create(
                        body=f'Riding App: Your password has been changed successfully. If you did not make this change, contact support immediately.',
                        from_=settings.TWILIO_PHONE_NUMBER,
                        to=user.phone_number
                    )
                except Exception as e:
                    print(f"Failed to send password change SMS notification: {str(e)}")

            
            refresh_token = request.data.get("refresh")
            if refresh_token:
                try:
                    token = RefreshToken(refresh_token)
                    token.blacklist()
                except Exception as e:
                    print(f"Failed to blacklist token after password change: {str(e)}")

            return Response({
                'message': 'Password changed successfully. You have been logged out for security. Please login again with your new password.',
                'note': 'Refresh token has been blacklisted. Access token is now invalid.'
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ForgotPasswordView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = ForgotPasswordSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            
            user = get_user_by_identifier(email_or_phone)
            if not user:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user.generate_otp()
            
            success, message = send_otp_verification(user, 'password_reset')
            
            if not success:
                return Response({
                    'error': f'Failed to send OTP: {message}',
                    'debug_otp': user.otp_code if settings.DEBUG else None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            if hasattr(user, 'phone_number') and user.phone_number:
                response_data = {
                    'message': 'OTP sent successfully via SMS for password reset',
                    'otp_code': user.otp_code if settings.DEBUG else None
                }
                return Response(response_data, status=status.HTTP_200_OK)
            else:
                return Response({
                    'message': 'OTP sent successfully via email for password reset',
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
            
            user = get_user_by_identifier(email_or_phone)
            if not user:
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
            
            user = get_user_by_identifier(email_or_phone)
            if not user:
                return Response({
                    'error': 'User not found'
                }, status=status.HTTP_404_NOT_FOUND)
            
            user.generate_otp()
            
            success, message = send_otp_verification(user, 'general')
            
            if not success:
                return Response({
                    'error': f'Failed to send OTP: {message}',
                    'debug_otp': user.otp_code if settings.DEBUG else None
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
            response_data = {
                'message': 'OTP sent successfully',
                'otp_code': user.otp_code if settings.DEBUG else None
            }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class VerifyOTPView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        if serializer.is_valid():
            email_or_phone = serializer.validated_data['email_or_phone']
            otp_code = serializer.validated_data['otp_code']
            
            user = get_user_by_identifier(email_or_phone)
            if not user:
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
        
        user.generate_otp()
        user.save()
        
        cache.set(f'delete_user_{user.id}', True, timeout=600)
        
        success, message = send_otp_verification(user, 'deletion')
        
        if not success:
            return Response({
                'error': f'Failed to send OTP: {message}',
                'debug_otp': user.otp_code if settings.DEBUG else None
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        
        if hasattr(user, 'phone_number') and user.phone_number:
            response_data = {
                'message': 'Account deletion OTP sent successfully via SMS. Please check your phone.',
                'otp_code': user.otp_code if settings.DEBUG else None
            }
            return Response(response_data, status=status.HTTP_200_OK)
        else:
            return Response({
                'message': 'Account deletion OTP sent successfully via email. Please check your email.',
                'otp_code': user.otp_code if settings.DEBUG else None
            }, status=status.HTTP_200_OK)


class ConfirmDeleteAccountView(APIView):
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
            account_type = serializer.validated_data.get('account_type', 'user')
            
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
                        account_type=account_type
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
                
                if not email:
                    if not facebook_id:
                        return Response({
                            'error': 'Facebook account must have either an email address or valid ID'
                        }, status=status.HTTP_400_BAD_REQUEST)
                    email = f"fb_{facebook_id}@facebook.user"
                
                name = user_data.get('name', '')
                first_name = user_data.get('first_name', '')
                last_name = user_data.get('last_name', '')
                
                username = f"fb_{facebook_id}" if facebook_id else email
                
                try:
                    try:
                        user = User.objects.get(email=email)
                    except User.DoesNotExist:
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
                        account_type=account_type
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