from django.core.mail import send_mail, EmailMultiAlternatives
from django.conf import settings
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

def send_confirmation_email(user, email_type, **kwargs):
    if not user.email:
        error_msg = f"Cannot send {email_type} email: User {user.id if hasattr(user, 'id') else 'unknown'} has no email address"
        logger.warning(error_msg)
        print(f"[ERROR] {error_msg}")
        return False, "User has no email address"
    
    print(f"[INFO] Attempting to send {email_type} email to {user.email}")
    
    if not hasattr(settings, 'EMAIL_HOST_USER') or not settings.EMAIL_HOST_USER:
        error_msg = "EMAIL_HOST_USER not configured in settings"
        logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    
    if not hasattr(settings, 'EMAIL_HOST_PASSWORD') or not settings.EMAIL_HOST_PASSWORD:
        error_msg = "EMAIL_HOST_PASSWORD not configured in settings"
        logger.error(error_msg)
        print(f"[ERROR] {error_msg}")
        return False, error_msg
    
    print(f"[OK] Email settings configured - Host: {settings.EMAIL_HOST}, User: {settings.EMAIL_HOST_USER}")
    
    try:
        context = {
            'user': user,
            'current_year': timezone.now().year,
            **kwargs
        }
        
        if email_type == 'registration':
            subject = 'Welcome to Riding App - Registration Successful!'
            template_name = 'emails/welcome_email.html'
            
            plain_message = f"""
                Dear {user.get_full_name() or user.username},

                Welcome to Riding App!

                Your account has been successfully created. We're excited to have you join our community.                Account Details:
                - Account Type: {user.get_account_type_display()}
                - Email: {user.email}
                - Registration Date: {user.date_joined.strftime('%B %d, %Y at %I:%M %p')}

                What's Next?
                {'• Complete your profile by adding your driving license and car details' if user.account_type == 'driver' else '• Complete your profile by adding your personal information'}
                • Start booking rides or offer rides to earn money
                • Explore all the features available in the app

                If you have any questions or need assistance, please don't hesitate to contact our support team.

                Thank you for choosing Riding App!

                Best regards,
                The Riding App Team
            """.strip()
            
        elif email_type == 'deletion':
            subject = 'Account Deletion Confirmation - Riding App'
            template_name = 'emails/deletion_confirmation_email.html'
            context['deletion_date'] = kwargs.get('deletion_date', timezone.now().strftime('%B %d, %Y at %I:%M %p'))
            
            plain_message = f"""
                Dear {user.get_full_name() or user.username},

                This email confirms that your Riding App account has been successfully deleted.

                Account Details (Deleted):
                - Account Type: {user.get_account_type_display()}
                - Email: {user.email}
                - Deletion Date: {context['deletion_date']}

                What This Means:
                • Your account and all associated data have been permanently removed
                • You will no longer receive any communications from us
                • Any active bookings or rides have been cancelled
                • All payment information has been securely deleted

                If you deleted your account by mistake or have any concerns, please contact our support team within 24 hours.

                Thank you for being part of the Riding App community.

                Best regards,
                The Riding App Team
            """.strip()
            
        else:
            logger.error(f"Unknown email type: {email_type}")
            return False, f"Unknown email type: {email_type}"
        
        try:
            print(f"[INFO] Attempting to render HTML template: {template_name}")
            html_message = render_to_string(template_name, context)
            print("[OK] HTML template rendered successfully")
            
            print(f"[INFO] Creating email with subject: {subject}")
            email = EmailMultiAlternatives(
                subject=subject,
                body=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                to=[user.email]
            )
            email.attach_alternative(html_message, "text/html")
            
            print(f"[INFO] Sending email to {user.email}...")
            email.send()
            print("[SUCCESS] Email sent successfully!")
            
        except Exception as template_error:
            print(f"[WARNING] HTML template failed, sending plain text: {template_error}")
            logger.warning(f"HTML template failed, sending plain text: {template_error}")
            try:
                print(f"[INFO] Sending plain text email to {user.email}...")
                send_mail(
                    subject=subject,
                    message=plain_message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[user.email],
                    fail_silently=False,
                )
                print("[SUCCESS] Plain text email sent successfully!")
            except Exception as plain_error:
                error_msg = f"Failed to send plain text email: {str(plain_error)}"
                print(f"[ERROR] {error_msg}")
                logger.error(error_msg)
                raise plain_error
        
        logger.info(f"Successfully sent {email_type} confirmation email to {user.email}")
        return True, f"Confirmation email sent successfully"
        
    except Exception as e:
        error_msg = f"Failed to send {email_type} confirmation email to {user.email}: {str(e)}"
        logger.error(error_msg)
        return False, error_msg


def send_welcome_email(user):
    return send_confirmation_email(user, 'registration')


def send_deletion_confirmation_email(user):
    return send_confirmation_email(
        user, 
        'deletion', 
        deletion_date=timezone.now().strftime('%B %d, %Y at %I:%M %p')
    )