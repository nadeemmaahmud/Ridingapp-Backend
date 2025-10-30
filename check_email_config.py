import os
import sys
import django
from pathlib import Path

project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'RidingApp.settings')
django.setup()

from django.conf import settings
from users.models import CustomUser

def check_email_configuration():
    """Check if email is properly configured"""
    print("🔍 Checking Email Configuration...")
    print("=" * 50)
    
    checks = [
        ('EMAIL_BACKEND', getattr(settings, 'EMAIL_BACKEND', None)),
        ('EMAIL_HOST', getattr(settings, 'EMAIL_HOST', None)),
        ('EMAIL_PORT', getattr(settings, 'EMAIL_PORT', None)),
        ('EMAIL_USE_TLS', getattr(settings, 'EMAIL_USE_TLS', None)),
        ('EMAIL_HOST_USER', getattr(settings, 'EMAIL_HOST_USER', None)),
        ('EMAIL_HOST_PASSWORD', '***' if getattr(settings, 'EMAIL_HOST_PASSWORD', None) else None),
        ('DEFAULT_FROM_EMAIL', getattr(settings, 'DEFAULT_FROM_EMAIL', None)),
    ]
    
    all_configured = True
    for setting, value in checks:
        status = "✅" if value else "❌"
        print(f"{status} {setting}: {value}")
        if not value and setting in ['EMAIL_HOST_USER', 'EMAIL_HOST_PASSWORD']:
            all_configured = False
    
    print("=" * 50)
    
    if all_configured:
        print("✅ Email configuration looks good!")
    else:
        print("❌ Email configuration incomplete!")
        print("\n💡 To fix email issues:")
        print("1. Create a .env file based on .env.example")
        print("2. Add your Gmail credentials:")
        print("   EMAIL_HOST_USER=your_email@gmail.com")
        print("   EMAIL_HOST_PASSWORD=your_app_password")
        print("3. For Gmail, use App Password (not regular password)")
    
    return all_configured

if __name__ == "__main__":
    check_email_configuration()