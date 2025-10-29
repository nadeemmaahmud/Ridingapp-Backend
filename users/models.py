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
        ('user', 'user'),
        ('driver', 'driver'),
    )

    account_type = models.CharField(max_length=10, choices=account_type_choices, default='user')
    full_name = models.CharField(max_length=100, blank=True, default='')
    email = models.EmailField(unique=True, blank=True, null=True)
    phone_number = models.CharField(max_length=15, unique=True, blank=True, null=True)
    username = models.CharField(max_length=150, unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_completed = models.BooleanField(default=False)

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