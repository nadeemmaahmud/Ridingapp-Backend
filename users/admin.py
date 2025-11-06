from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django import forms
from .models import CustomUser

class CustomUserCreationForm(UserCreationForm):
    email_or_phone = forms.CharField(
        max_length=150,
        help_text="Enter either email address or phone number"
    )
    
    class Meta:
        model = CustomUser
        fields = ('email_or_phone', 'full_name', 'account_type')

    def clean_email_or_phone(self):
        email_or_phone = self.cleaned_data.get('email_or_phone')
        
        if '@' in email_or_phone:
            try:
                forms.EmailField().clean(email_or_phone)
                if CustomUser.objects.filter(email=email_or_phone).exists():
                    raise forms.ValidationError("A user with this email already exists.")
                return email_or_phone
            except forms.ValidationError:
                raise forms.ValidationError("Please enter a valid email address.")
        else:
            if CustomUser.objects.filter(phone_number=email_or_phone).exists():
                raise forms.ValidationError("A user with this phone number already exists.")
            return email_or_phone

    def save(self, commit=True):
        user = super().save(commit=False)
        email_or_phone = self.cleaned_data['email_or_phone']
        
        if '@' in email_or_phone:
            user.email = email_or_phone
            user.phone_number = None
            user.username = email_or_phone
        else:
            user.phone_number = email_or_phone
            user.email = None
            user.username = email_or_phone
            
        if commit:
            user.save()
        return user

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('email', 'phone_number', 'full_name', 'account_type', 
                 'is_verified', 'is_staff', 'profile_picture', 
                 'id_number', 'payment_method', 'driver_is_available', 'driving_license_picture', 
                 'car_picture', 'car_name', 'plate_number')

class CustomUserAdmin(UserAdmin):
    add_form = CustomUserCreationForm
    form = CustomUserChangeForm
    model = CustomUser
    
    list_display = (
        'username', 'email', 'phone_number', 'full_name', 
        'account_type', 'is_verified', 'driver_is_available', 'is_staff', 'date_joined'
    )
    
    list_filter = (
        'account_type', 'is_verified', 'driver_is_available', 'is_staff', 'date_joined'
    )
    
    search_fields = ('username', 'email', 'phone_number', 'full_name')
    
    ordering = ('-date_joined',)
    
    readonly_fields = ('date_joined', 'updated_at', 'username')
    
    fieldsets = (
        (None, {
            'fields': ('username', 'password')
        }),
        ('Personal Info', {
            'fields': ('full_name', 'email', 'phone_number', 'account_type', 'profile_picture', 'id_number')
        }),
        ('Payment Info', {
            'fields': ('payment_method',)
        }),
        ('Driver Info', {
            'fields': ('driver_is_available', 'driving_license_picture', 'car_picture', 'car_name', 'plate_number')
        }),
        ('Permissions', {
            'fields': ('is_verified', 'is_staff')
        }),
        ('Important Dates', {
            'fields': ('last_login', 'date_joined', 'updated_at')
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email_or_phone', 'full_name', 'account_type', 'password1', 'password2'),
        }),
        ('Permissions', {
            'fields': ('is_verified', 'is_staff')
        }),
    )
    
    actions = ['verify_users', 'unverify_users', 'make_drivers_available', 'make_drivers_unavailable']
    
    def verify_users(self, request, queryset):
        updated = queryset.update(is_verified=True)
        self.message_user(request, f'{updated} users have been verified.')
    verify_users.short_description = "Verify selected users"
    
    def unverify_users(self, request, queryset):
        updated = queryset.update(is_verified=False)
        self.message_user(request, f'{updated} users have been unverified.')
    unverify_users.short_description = "Unverify selected users"
    
    def make_drivers_available(self, request, queryset):
        updated = queryset.filter(account_type='driver').update(driver_is_available=True)
        self.message_user(request, f'{updated} drivers have been marked as available.')
    make_drivers_available.short_description = "Mark selected drivers as available"
    
    def make_drivers_unavailable(self, request, queryset):
        updated = queryset.filter(account_type='driver').update(driver_is_available=False)
        self.message_user(request, f'{updated} drivers have been marked as unavailable.')
    make_drivers_unavailable.short_description = "Mark selected drivers as unavailable"
    
    def get_email_or_phone(self, obj):
        return obj.email or obj.phone_number
    get_email_or_phone.short_description = "Email/Phone"
    
    def profile_completion(self, obj):
        return "Complete" if obj.is_completed else "Incomplete"
    profile_completion.short_description = "Profile Status"

admin.site.register(CustomUser, CustomUserAdmin)

admin.site.site_header = "Riding App Administration"
admin.site.site_title = "Riding App Admin"
admin.site.index_title = "Welcome to Riding App Administration"
