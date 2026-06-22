"""
Configuration pour les services de paiement (Cauris, Airtel Money, Orange Money, etc.)
"""

# Configuration Cauris
CAURIS_CONFIG = {
    'api_key': 'YOUR_CAURIS_API_KEY',  # À remplacer par votre vraie clé API
    'api_secret': 'YOUR_CAURIS_API_SECRET',  # À remplacer par votre vraie clé secrète
    'base_url': 'https://api.cauris.com',
    'currency': 'CDF',  # Devise congolaise
    'notify_url': 'http://localhost:8000/api/payment-webhook/',  # URL pour recevoir les notifications
    'mode': 'test',  # 'test' pour le mode test, 'live' pour la production
}

# Configuration Orange Money (alternative directe)
ORANGE_MONEY_CONFIG = {
    'api_key': 'YOUR_ORANGE_API_KEY',
    'api_secret': 'YOUR_ORANGE_API_SECRET',
    'base_url': 'https://api.orange.com/orange-money',
    'merchant_id': 'YOUR_MERCHANT_ID',
    'currency': 'CDF',
    'notify_url': 'http://localhost:8000/api/payment-webhook/',
}

# Configuration M-PESA (alternative directe)
MPESA_CONFIG = {
    'api_key': 'YOUR_MPESA_API_KEY',
    'api_secret': 'YOUR_MPESA_API_SECRET',
    'base_url': 'https://api.safaricom.co.ke/mpesa',
    'shortcode': 'YOUR_SHORTCODE',
    'passkey': 'YOUR_PASSKEY',
    'currency': 'CDF',
    'notify_url': 'http://localhost:8000/api/payment-webhook/',
}

# Configuration PayPal
PAYPAL_CONFIG = {
    'client_id': 'YOUR_PAYPAL_CLIENT_ID',
    'client_secret': 'YOUR_PAYPAL_CLIENT_SECRET',
    'base_url': 'https://api.paypal.com',
    'mode': 'sandbox',  # 'sandbox' pour test, 'live' pour production
    'return_url': 'http://localhost:3000/payment/success',
    'cancel_url': 'http://localhost:3000/payment/cancel',
}

# Configuration des montants minimums et maximums par devise
PAYMENT_LIMITS = {
    'CDF': {
        'min': 100,  # 100 CDF minimum
        'max': 1000000,  # 1 000 000 CDF maximum
    },
    'USD': {
        'min': 1,  # 1 USD minimum
        'max': 10000,  # 10 000 USD maximum
    },
}

# Configuration des délais d'expiration des paiements (en minutes)
PAYMENT_TIMEOUT = {
    'airtel': 15,  # 15 minutes pour Airtel Money
    'orange': 15,  # 15 minutes pour Orange Money
    'mpesa': 15,  # 15 minutes pour M-PESA
    'paypal': 30,  # 30 minutes pour PayPal
    'bank': 60,  # 60 minutes pour les paiements bancaires
}
