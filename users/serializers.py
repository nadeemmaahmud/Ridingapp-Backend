from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth import get_user_model, authenticate
from django.core.exceptions import ValidationError
import re

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['account_type', 'full_name', 'email', 'phone_number', 'is_active', 'is_staff', 'is_superuser']
        read_only_fields = ['is_active', 'is_staff', 'is_superuser']

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])
    email_or_phone = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['account_type', 'full_name', 'email_or_phone', 'password']

    def validate_email_or_phone(self, value):
        if '@' in value:
            try:
                serializers.EmailField().run_validation(value)

                if User.objects.filter(email=value).exists():
                    raise serializers.ValidationError("Email is already in use.")
                return value
            except ValidationError:
                raise serializers.ValidationError("Invalid email format.")
        else:
            if not re.match(r'^\+?1?\d{9,15}$', value):
                raise serializers.ValidationError("Invalid phone number format.")

            if User.objects.filter(phone_number=value).exists():
                raise serializers.ValidationError("Phone number is already in use.")
            return value

    def create(self, validated_data):
        email_or_phone = validated_data.pop('email_or_phone')
        password = validated_data.pop('password')

        if '@' in email_or_phone:
            validated_data['email'] = email_or_phone
        else:
            validated_data['phone_number'] = email_or_phone

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
                    user = authenticate(email=email_or_phone)
                except User.DoesNotExist:
                    pass
            else:
                try:
                    user = authenticate(phone_number=email_or_phone)
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
        
class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['account_type', 'full_name', 'email', 'phone_number']
    
    def validate_email(self, value):
        user = self.instance
        if value and User.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError("Email is already in use.")
        return value

    def validate_phone_number(self, value):
        user = self.instance
        if value and User.objects.exclude(pk=user.pk).filter(phone_number=value).exists():
            raise serializers.ValidationError("Phone number is already in use.")
        return value
    
    def update(self, instance, validated_data):
        instance.account_type = validated_data.get('account_type', instance.account_type)
        instance.full_name = validated_data.get('full_name', instance.full_name)
        instance.save()
        return instance
    
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
        self.context['user'] = user
        return value
    
class ResetPasswordSerializer(serializers.Serializer):
    new_password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(write_only=True, required=True)
    reset_token = serializers.CharField(write_only=True, required=True)

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError("New passwords don't match.")
        return data