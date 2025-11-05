import stripe
from django.conf import settings
from stripe import _error as stripe_error

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount, currency='usd', metadata=None):
    if not stripe.api_key:
        raise Exception("Stripe API key is not configured. Please check STRIPE_SECRET_KEY in your environment variables.")
    
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            metadata=metadata or {},
            automatic_payment_methods={'enabled': True, 'allow_redirects': 'never'},
        )
        return payment_intent
    except stripe_error.InvalidRequestError as e:
        raise Exception(f"Invalid request to Stripe: {str(e)}")
    except stripe_error.AuthenticationError as e:
        raise Exception(f"Stripe authentication failed. Check your API key: {str(e)}")
    except stripe_error.APIConnectionError as e:
        raise Exception(f"Network error connecting to Stripe: {str(e)}")
    except stripe_error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def confirm_payment_intent(payment_intent_id):
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return payment_intent
    except stripe_error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def refund_payment(payment_intent_id, amount=None):
    try:
        refund_params = {'payment_intent': payment_intent_id}
        if amount:
            refund_params['amount'] = int(amount * 100)
        
        refund = stripe.Refund.create(**refund_params)
        return refund
    except stripe_error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def construct_webhook_event(payload, signature, webhook_secret):
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        return event
    except ValueError as e:
        raise Exception("Invalid payload")
    except stripe_error.SignatureVerificationError as e:
        raise Exception("Invalid signature")


def confirm_payment_with_test_card(payment_intent_id):
    if not stripe.api_key:
        raise Exception("Stripe API key is not configured.")
    
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        
        if payment_intent.status == 'succeeded':
            return stripe.PaymentIntent.retrieve(
                payment_intent_id,
                expand=['charges']
            )
        
        test_payment_method = 'pm_card_visa'
        
        payment_intent = stripe.PaymentIntent.modify(
            payment_intent_id,
            payment_method=test_payment_method,
        )
        
        payment_intent = stripe.PaymentIntent.confirm(
            payment_intent_id,
            return_url='https://example.com/payment/complete',
            expand=['charges'],
        )
        
        return payment_intent
    except stripe_error.InvalidRequestError as e:
        raise Exception(f"Invalid request to Stripe: {str(e)}")
    except stripe_error.CardError as e:
        raise Exception(f"Card error: {str(e)}")
    except stripe_error.AuthenticationError as e:
        raise Exception(f"Authentication error: {str(e)}")
    except stripe_error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")
    except Exception as e:
        raise Exception(f"Unexpected error: {str(e)}")
