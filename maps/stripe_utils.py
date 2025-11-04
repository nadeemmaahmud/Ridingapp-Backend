import stripe
from django.conf import settings

stripe.api_key = settings.STRIPE_SECRET_KEY

def create_payment_intent(amount, currency='usd', metadata=None):
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=int(amount * 100),
            currency=currency,
            metadata=metadata or {},
            automatic_payment_methods={'enabled': True},
        )
        return payment_intent
    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def confirm_payment_intent(payment_intent_id):
    try:
        payment_intent = stripe.PaymentIntent.retrieve(payment_intent_id)
        return payment_intent
    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def refund_payment(payment_intent_id, amount=None):
    try:
        refund_params = {'payment_intent': payment_intent_id}
        if amount:
            refund_params['amount'] = int(amount * 100)
        
        refund = stripe.Refund.create(**refund_params)
        return refund
    except stripe.error.StripeError as e:
        raise Exception(f"Stripe error: {str(e)}")

def construct_webhook_event(payload, signature, webhook_secret):
    try:
        event = stripe.Webhook.construct_event(
            payload, signature, webhook_secret
        )
        return event
    except ValueError as e:
        raise Exception("Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        raise Exception("Invalid signature")
