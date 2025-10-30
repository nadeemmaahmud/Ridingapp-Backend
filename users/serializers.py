from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.core.cache import cache
import re

User = get_user_model()

class UserRegistrationSerializer(serializers.Serializer):
    account_type = serializers.ChoiceField(
        choices=[('user', 'User'), ('driver', 'Driver')], 
        required=True
    )
    full_name = serializers.CharField(max_length=100, required=True)
    email_or_phone = serializers.CharField(
        max_length=100, 
        required=True,
        help_text="Enter either your email address or phone number"
    )
    password = serializers.CharField(
        write_only=True, 
        validators=[validate_password],
        required=True
    )

    def validate_email_or_phone(self, value):
        if '@' in value:
            try:
                serializers.EmailField().run_validation(value)
                if User.objects.filter(email=value).exists():
                    raise serializers.ValidationError("A user with this email already exists.")
                return value
            except ValidationError:
                raise serializers.ValidationError("Please enter a valid email address.")
        else:
            if not re.match(r'^\+?1?\d{9,15}$', value):
                raise serializers.ValidationError("Please enter a valid phone number (9-15 digits).")
            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("A user with this phone number already exists.")
            return value

    def create(self, validated_data):
        email_or_phone = validated_data.pop('email_or_phone')
        password = validated_data.pop('password')
        
        if '@' in email_or_phone:
            validated_data['email'] = email_or_phone
            validated_data['phone_number'] = None
        else:
            validated_data['phone_number'] = email_or_phone  
            validated_data['email'] = None
            
        user = User.objects.create_user(password=password, **validated_data)
        return user
    
class UserLoginSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        email_or_phone = data.get('email_or_phone')
        password = data.get('password')

        if email_or_phone and password:
            user = None
            
            if '@' in email_or_phone:
                try:
                    user = User.objects.get(email=email_or_phone)
                except User.DoesNotExist:
                    pass
            else:
                try:
                    user = User.objects.get(phone_number=email_or_phone)
                except User.DoesNotExist:
                    pass

            if user and user.check_password(password):
                if not user.is_active:
                    raise serializers.ValidationError("User account is disabled.")
                data['user'] = user
                return data
            else:
                raise serializers.ValidationError("Unable to log in with provided credentials.")
        else:
            raise serializers.ValidationError("Must include 'email_or_phone' and 'password'.")
    
class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(write_only=True, required=True)
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct.")
        return value

    def validate(self, data):
        if data['old_password'] == data['new_password']:
            raise serializers.ValidationError("New password must be different from the old password.")
        return data
    
    def validate_new_password(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return attrs

    def save(self, **kwargs):
        user = self.context['request'].user
        user.set_password(self.validated_data['new_password'])
        user.save()
        return user
    
class ForgotPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField()

    def validate_email_or_phone(self, value):
        user = None
        if '@' in value:
            try:
                user = User.objects.get(email=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this email does not exist.")
        else:
            try:
                user = User.objects.get(phone_number=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("User with this phone number does not exist.")
        return value
    
class ResetPasswordSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(max_length=100)
    otp_code = serializers.CharField(
        max_length=6, 
        min_length=6,
        help_text="Enter the 6-digit OTP code"
    )
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True, required=True)

    def validate_otp_code(self, value):
        if not value.isdigit():
            raise serializers.ValidationError("OTP must contain only digits.")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return data

class BasicUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'account_type', 'full_name', 'email', 'phone_number', 'is_verified',
            'date_joined', 'profile_picture', 'id_number', 'payment_method'
        ]
        read_only_fields = ['id', 'date_joined', 'account_type', 'is_verified']

class DriverSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            'id', 'account_type', 'full_name', 'email', 'phone_number', 
            'date_joined', 'profile_picture', 'is_verified',
            'id_number', 'payment_method', 'driving_license_picture', 
            'car_picture', 'car_name', 'plate_number'
        ]
        read_only_fields = ['id', 'date_joined', 'account_type', 'is_verified']

class SendOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(
        max_length=100,
        help_text="Enter email or phone number to receive OTP"
    )

    def validate_email_or_phone(self, value):
        user = None
        if '@' in value:
            try:
                user = User.objects.get(email=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this email.")
        else:
            try:
                user = User.objects.get(phone_number=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this phone number.")
        
        self.context['user'] = user
        return value

class VerifyOTPSerializer(serializers.Serializer):
    email_or_phone = serializers.CharField(max_length=100)
    otp_code = serializers.CharField(
        max_length=6, 
        min_length=6,
        help_text="Enter the 6-digit OTP code"
    )

    def validate(self, data):
        email_or_phone = data.get('email_or_phone')
        otp_code = data.get('otp_code')

        user = None
        if '@' in email_or_phone:
            try:
                user = User.objects.get(email=email_or_phone)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this email.")
        else:
            try:
                user = User.objects.get(phone_number=email_or_phone)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this phone number.")

        if not user.verify_otp(otp_code):
            raise serializers.ValidationError("Invalid or expired OTP code.")

        data['user'] = user
        return data
    email_or_phone = serializers.CharField(
        max_length=100,
        help_text="Enter email or phone number to send OTP"
    )
    
    def validate_email_or_phone(self, value):
        user = None
        if '@' in value:
            try:
                user = User.objects.get(email=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this email address.")
        else:
            try:
                user = User.objects.get(phone_number=value)
            except User.DoesNotExist:
                raise serializers.ValidationError("No user found with this phone number.")
        
        self.context['user'] = user
        return value