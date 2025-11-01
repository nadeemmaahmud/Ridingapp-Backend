from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.core.exceptions import ValidationError

class CustomUserManager(BaseUserManager):
    def create_user(self, username=None, email=None, phone_number=None, password=None, **extra_fields):
        if username and not email and not phone_number:
            if '@' in username:
                email = username
            else:
                phone_number = username

        if not email and not phone_number:
            raise ValueError('The user must have either an email or a phone number.')

        if email and phone_number:
            raise ValueError('The user can only have either an email or a phone number, not both.')

        if email:
            email = self.normalize_email(email)
            extra_fields.setdefault('username', email)
            user = self.model(email=email, **extra_fields)
        else:
            extra_fields.setdefault('username', phone_number)
            user = self.model(phone_number=phone_number, **extra_fields)
            
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username=None, email=None, phone_number=None, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('account_type', 'user')
        extra_fields.setdefault('full_name', '')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, email, phone_number, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    account_type_choices = (
        ('user', 'User'),
        ('driver', 'Driver'),
    )

    payment_method_choices = (
        ('credit_card', 'Credit Card'),
        ('cash', 'Cash'),
    )

    account_type = models.CharField(max_length=10, choices=account_type_choices, default='user')
    full_name = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(unique=True, blank=True, null=True, db_index=True)
    phone_number = models.CharField(max_length=20, unique=True, blank=True, null=True, db_index=True)
    username = models.CharField(max_length=150, unique=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_password_change = models.DateTimeField(blank=True, null=True)

    is_verified = models.BooleanField(default=False)
    otp_code = models.CharField(max_length=6, blank=True, null=True)
    otp_created_at = models.DateTimeField(blank=True, null=True)

    profile_picture = models.ImageField(upload_to='profile_pictures/', blank=True, null=True)
    id_number = models.CharField(max_length=50, unique=True, blank=True, null=True)
    payment_method = models.CharField(max_length=50, blank=True, null=True, choices=payment_method_choices)

    driving_license_picture = models.ImageField(upload_to='driving_licenses/', blank=True, null=True)
    car_picture = models.ImageField(upload_to='car_pictures/', blank=True, null=True)
    car_name = models.CharField(max_length=100, blank=True, null=True)
    plate_number = models.CharField(max_length=20, blank=True, null=True)

    objects = CustomUserManager()

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'custom_user'
        verbose_name = 'User'
        verbose_name_plural = 'Users'

    def clean(self):
        if hasattr(self, '_skip_validation'):
            return
        
        if not self.email and not self.phone_number:
            raise ValidationError('Either email or phone number must be provided.')
        if self.email and self.phone_number:
            raise ValidationError('Only one of email or phone number can be provided.')

    def save(self, *args, **kwargs):
        if not self.username:
            if self.email:
                self.username = self.email
            elif self.phone_number:
                self.username = self.phone_number

        if not hasattr(self, '_skip_validation'):
            self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

    def get_full_name(self):
        return self.full_name

    def get_short_name(self):
        return self.full_name.split()[0] if self.full_name else self.username

    def generate_otp(self):
        import random
        from django.utils import timezone
        
        self.otp_code = str(random.randint(100000, 999999))
        self.otp_created_at = timezone.now()
        self.save()
        return self.otp_code

    def verify_otp(self, otp_code):
        from django.utils import timezone
        from datetime import timedelta
        
        if not self.otp_code or not self.otp_created_at:
            return False
            
        if self.otp_code != otp_code:
            return False
            
        if timezone.now() > self.otp_created_at + timedelta(minutes=10):
            return False
            
        return True

    def clear_otp(self):
        self.otp_code = None
        self.otp_created_at = None
        self.is_verified = True
        self.save()