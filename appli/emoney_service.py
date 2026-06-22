"""
Service pour l'intégration E-Money (Airtel Money, Orange Money, M-PESA) en RDC
"""

import requests
import json
import base64
from datetime import datetime
from typing import Dict, Optional
import hashlib
import hmac
import cauris
from .payment_config import CAURIS_CONFIG, ORANGE_MONEY_CONFIG, MPESA_CONFIG, PAYPAL_CONFIG

class EMoneyService:
    """
    Service pour gérer les paiements via E-Money en République Démocratique du Congo
    Supporte: Airtel Money, Orange Money, M-PESA
    """
    
    def __init__(self):
        # Configuration Cauris pour Airtel Money
        self.cauris_config = CAURIS_CONFIG
        
        # Configuration des APIs alternatives (à remplacer par les vraies clés API)
        self.orange_config = ORANGE_MONEY_CONFIG
        self.mpesa_config = MPESA_CONFIG
        self.paypal_config = PAYPAL_CONFIG
        
        # Initialiser Cauris si la clé API est configurée
        if CAURIS_CONFIG['api_key'] != 'YOUR_CAURIS_API_KEY':
            cauris.api_key = CAURIS_CONFIG['api_key']
    
    def process_airtel_payment(self, phone_number: str, amount: float, reference: str) -> Dict:
        """
        Traite un paiement via Airtel Money en utilisant Cauris

        Args:
            phone_number: Numéro de téléphone (format: +243XXXXXXXXX)
            amount: Montant à payer
            reference: Référence de la transaction

        Returns:
            Dict avec le statut de la transaction
        """
        try:
            # Vérifier si Cauris est configuré
            if self.cauris_config['api_key'] == 'YOUR_CAURIS_API_KEY':
                # Mode simulation si la clé API n'est pas configurée
                return {
                    'success': True,
                    'transaction_id': f"AIRTEL_SIMULATED_{reference}_{datetime.now().timestamp()}",
                    'status': 'pending',
                    'message': 'Paiement Airtel Money simulé (configurez votre clé API Cauris pour la production)',
                    'provider': 'airtel',
                    'mode': 'simulation'
                }

            # Utiliser Cauris pour créer un paiement Airtel Money
            charge = cauris.Charge.create(
                amount=int(amount),
                phone=phone_number,
                currency=self.cauris_config['currency'],
                notify_url=self.cauris_config['notify_url'],
                metadata={
                    'reference': reference,
                    'provider': 'airtel'
                }
            )

            return {
                'success': True,
                'transaction_id': charge.id,
                'status': charge.status,
                'message': 'Demande de paiement Airtel Money envoyée avec succès. Veuillez valider sur votre téléphone.',
                'provider': 'airtel',
                'mode': 'production'
            }

        except Exception as e:
            return {
                'success': False,
                'status': 'failed',
                'message': f'Erreur lors du paiement Airtel Money: {str(e)}',
                'provider': 'airtel'
            }
    
    def process_orange_payment(self, phone_number: str, amount: float, reference: str) -> Dict:
        """
        Traite un paiement via Orange Money
        
        Args:
            phone_number: Numéro de téléphone (format: +243XXXXXXXXX)
            amount: Montant à payer
            reference: Référence de la transaction
            
        Returns:
            Dict avec le statut de la transaction
        """
        try:
            # Préparer les données pour l'API Orange Money
            payload = {
                'msisdn': phone_number,
                'amount': amount,
                'currency': 'CDF',
                'reference': reference,
                'merchant_id': self.orange_config['merchant_id'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Générer la signature
            signature = self._generate_signature(payload, self.orange_config['api_secret'])
            
            headers = {
                'Authorization': f'Bearer {self.orange_config["api_key"]}',
                'X-Signature': signature,
                'Content-Type': 'application/json'
            }
            
            # Appel à l'API (simulation pour le moment)
            # response = requests.post(
            #     f"{self.orange_config['base_url']}/payments",
            #     json=payload,
            #     headers=headers
            # )
            
            # Simulation de réponse réussie
            return {
                'success': True,
                'transaction_id': f"ORANGE_{reference}_{datetime.now().timestamp()}",
                'status': 'completed',
                'message': 'Paiement Orange Money effectué avec succès',
                'provider': 'orange'
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'failed',
                'message': f'Erreur lors du paiement Orange Money: {str(e)}',
                'provider': 'orange'
            }
    
    def process_mpesa_payment(self, phone_number: str, amount: float, reference: str) -> Dict:
        """
        Traite un paiement via M-PESA
        
        Args:
            phone_number: Numéro de téléphone (format: +243XXXXXXXXX)
            amount: Montant à payer
            reference: Référence de la transaction
            
        Returns:
            Dict avec le statut de la transaction
        """
        try:
            # Préparer les données pour l'API M-PESA
            payload = {
                'phoneNumber': phone_number,
                'amount': amount,
                'accountReference': reference,
                'transactionDesc': 'Paiement abonnement Jessna CinéHub',
                'shortcode': self.mpesa_config['shortcode'],
                'timestamp': datetime.now().isoformat()
            }
            
            # Générer le mot de passe pour M-PESA
            password = self._generate_mpesa_password()
            
            headers = {
                'Authorization': f'Bearer {self.mpesa_config["api_key"]}',
                'Content-Type': 'application/json'
            }
            
            # Appel à l'API (simulation pour le moment)
            # response = requests.post(
            #     f"{self.mpesa_config['base_url']}/stkpush/v1/processrequest",
            #     json=payload,
            #     headers=headers
            # )
            
            # Simulation de réponse réussie
            return {
                'success': True,
                'transaction_id': f"MPESA_{reference}_{datetime.now().timestamp()}",
                'status': 'completed',
                'message': 'Paiement M-PESA effectué avec succès',
                'provider': 'mpesa'
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'failed',
                'message': f'Erreur lors du paiement M-PESA: {str(e)}',
                'provider': 'mpesa'
            }
    
    def process_paypal_payment(self, amount: float, reference: str, return_url: str, cancel_url: str) -> Dict:
        """
        Traite un paiement via PayPal
        
        Args:
            amount: Montant à payer
            reference: Référence de la transaction
            return_url: URL de retour après paiement réussi
            cancel_url: URL de retour après annulation
            
        Returns:
            Dict avec le statut de la transaction et l'URL de paiement
        """
        try:
            # Préparer les données pour l'API PayPal
            payload = {
                'intent': 'sale',
                'payer': {
                    'payment_method': 'paypal'
                },
                'transactions': [{
                    'amount': {
                        'total': str(amount),
                        'currency': 'USD'
                    },
                    'description': f'Abonnement Jessna CinéHub - Réf: {reference}'
                }],
                'redirect_urls': {
                    'return_url': return_url,
                    'cancel_url': cancel_url
                }
            }
            
            # Appel à l'API PayPal (simulation pour le moment)
            # response = requests.post(
            #     'https://api.paypal.com/v1/payments/payment',
            #     json=payload,
            #     headers={'Authorization': f'Bearer {PAYPAL_ACCESS_TOKEN}'}
            # )
            
            # Simulation de réponse réussie
            return {
                'success': True,
                'payment_url': f'https://paypal.com/checkout?token=SIMULATED_{reference}',
                'transaction_id': f"PAYPAL_{reference}_{datetime.now().timestamp()}",
                'status': 'pending',
                'message': 'Redirection vers PayPal pour paiement',
                'provider': 'paypal'
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'failed',
                'message': f'Erreur lors du paiement PayPal: {str(e)}',
                'provider': 'paypal'
            }
    
    def process_card_payment(self, card_number: str, expiry: str, cvv: str, amount: float, reference: str) -> Dict:
        """
        Traite un paiement via carte bancaire (Visa/Mastercard)
        
        Args:
            card_number: Numéro de carte
            expiry: Date d'expiration (MM/YY)
            cvv: Code CVV
            amount: Montant à payer
            reference: Référence de la transaction
            
        Returns:
            Dict avec le statut de la transaction
        """
        try:
            # Préparer les données pour le processeur de paiement
            payload = {
                'card_number': card_number,
                'expiry': expiry,
                'cvv': cvv,
                'amount': amount,
                'currency': 'USD',
                'reference': reference
            }
            
            # Appel à l'API du processeur de paiement (simulation pour le moment)
            # response = requests.post(
            #     'https://api.payment-processor.com/v1/charges',
            #     json=payload,
            #     headers={'Authorization': f'Bearer {PAYMENT_PROCESSOR_TOKEN}'}
            # )
            
            # Simulation de réponse réussie
            return {
                'success': True,
                'transaction_id': f"CARD_{reference}_{datetime.now().timestamp()}",
                'status': 'completed',
                'message': 'Paiement par carte effectué avec succès',
                'provider': 'card'
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'failed',
                'message': f'Erreur lors du paiement par carte: {str(e)}',
                'provider': 'card'
            }
    
    def check_transaction_status(self, transaction_id: str, provider: str) -> Dict:
        """
        Vérifie le statut d'une transaction
        
        Args:
            transaction_id: ID de la transaction
            provider: Fournisseur de paiement (airtel, orange, mpesa, paypal, card)
            
        Returns:
            Dict avec le statut actuel de la transaction
        """
        try:
            # Appel à l'API appropriée pour vérifier le statut
            # (simulation pour le moment)
            
            return {
                'success': True,
                'transaction_id': transaction_id,
                'status': 'completed',
                'message': 'Transaction complétée avec succès'
            }
            
        except Exception as e:
            return {
                'success': False,
                'status': 'unknown',
                'message': f'Erreur lors de la vérification: {str(e)}'
            }
    
    def _generate_signature(self, payload: Dict, secret: str) -> str:
        """
        Génère une signature HMAC pour sécuriser les requêtes API
        """
        message = json.dumps(payload, sort_keys=True)
        signature = hmac.new(
            secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def _generate_mpesa_password(self) -> str:
        """
        Génère le mot de passe pour l'API M-PESA
        """
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        password_str = f"{self.mpesa_config['shortcode']}{self.mpesa_config['passkey']}{timestamp}"
        password = base64.b64encode(password_str.encode()).decode()
        return password
