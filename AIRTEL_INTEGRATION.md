# Intégration Airtel Money avec Cauris

Ce document explique comment configurer et utiliser l'intégration Airtel Money pour Jessna CinéHub en utilisant le SDK Cauris.

## 📋 Prérequis

- Python 3.8+
- Django 4.2+
- Compte Cauris avec clé API
- Numéro de téléphone Airtel Money pour les tests

## 🚀 Installation

Le SDK Cauris est déjà installé dans le projet. Si vous devez le réinstaller:

```bash
pip install cauris
```

## ⚙️ Configuration

### 1. Obtenir les clés API Cauris

1. Créez un compte sur [Cauris](https://cauris.com)
2. Obtenez votre clé API et clé secrète depuis le tableau de bord
3. Configurez le mode (test ou production)

### 2. Configurer les clés API

Ouvrez le fichier `backend auth/appli/payment_config.py` et remplacez les valeurs par défaut:

```python
CAURIS_CONFIG = {
    'api_key': 'VOTRE_VRAIE_CLE_API',  # Remplacez par votre clé API
    'api_secret': 'VOTRE_VRAIE_CLE_SECRETE',  # Remplacez par votre clé secrète
    'base_url': 'https://api.cauris.com',
    'currency': 'CDF',  # Devise congolaise
    'notify_url': 'http://localhost:8000/api/payment-webhook/',  # URL pour recevoir les notifications
    'mode': 'test',  # 'test' pour le mode test, 'live' pour la production
}
```

### 3. Configurer le webhook

Pour la production, remplacez `localhost:8000` par votre domaine réel:

```python
'notify_url': 'https://votre-domaine.com/api/payment-webhook/',
```

## 🔄 Fonctionnement

### Processus de paiement Airtel Money

1. **Demande de paiement**: L'utilisateur sélectionne Airtel Money et entre son numéro
2. **Notification USSD**: L'utilisateur reçoit une notification USSD sur son téléphone
3. **Validation**: L'utilisateur valide le paiement avec son code PIN
4. **Webhook**: Cauris envoie une notification à votre serveur via le webhook
5. **Activation**: L'abonnement est activé automatiquement

### Flux technique

```
Frontend → Backend → Cauris API → USSD Push → Utilisateur
                                              ↓
                                         Validation
                                              ↓
Webhook ← Cauris API ← Utilisateur
```

## 📝 Utilisation

### Mode Test

Si les clés API ne sont pas configurées, le système fonctionne en mode simulation:

```python
# Le paiement est simulé
{
    'success': True,
    'transaction_id': 'AIRTEL_SIMULATED_...',
    'status': 'pending',
    'message': 'Paiement Airtel Money simulé (configurez votre clé API Cauris pour la production)',
    'provider': 'airtel',
    'mode': 'simulation'
}
```

### Mode Production

Une fois les clés API configurées, le système utilise l'API Cauris réelle:

```python
# Le paiement est traité par Cauris
{
    'success': True,
    'transaction_id': 'cauris_charge_id',
    'status': 'pending',
    'message': 'Demande de paiement Airtel Money envoyée avec succès. Veuillez valider sur votre téléphone.',
    'provider': 'airtel',
    'mode': 'production'
}
```

## 🔧 API Endpoints

### Webhook de paiement

**URL**: `POST /api/payment-webhook/`

Ce endpoint reçoit les notifications de Cauris quand un paiement est validé ou échoué.

**Payload exemple**:
```json
{
    "id": "charge_id",
    "status": "success",
    "metadata": {
        "reference": "SUB123",
        "provider": "airtel"
    }
}
```

## 🧪 Tests

### Tester en mode simulation

1. Lancez l'application
2. Sélectionnez Airtel Money comme moyen de paiement
3. Entrez un numéro de téléphone (format: +243XXXXXXXXX)
4. Le paiement sera simulé

### Tester en mode production

1. Configurez vos clés API Cauris
2. Changez le mode en `'live'` dans `payment_config.py`
3. Utilisez un numéro de téléphone réel
4. Validez le paiement sur votre téléphone via USSD

## 📊 Monitoring

Les logs sont enregistrés dans le fichier de logs Django:

```python
logger.info(f"Webhook reçu: {data}")
logger.info(f"Paiement {transaction_id} validé avec succès")
logger.error(f"Erreur lors du paiement: {str(e)}")
```

## 🔒 Sécurité

- Les clés API ne doivent jamais être commitées dans le repository
- Utilisez des variables d'environnement pour les clés en production
- Le webhook utilise `@csrf_exempt` pour permettre les requêtes externes
- Vérifiez toujours l'authenticité des webhooks en production

## 🚨 Dépannage

### Erreur: "Paiement Airtel Money simulé"

**Cause**: Les clés API Cauris ne sont pas configurées

**Solution**: Configurez les clés API dans `payment_config.py`

### Erreur: "Paiement non trouvé"

**Cause**: Le transaction_id ne correspond à aucun paiement dans la base de données

**Solution**: Vérifiez que le transaction_id est correctement stocké lors de la création du paiement

### Webhook non reçu

**Cause**: L'URL du webhook n'est pas accessible depuis l'extérieur

**Solution**: 
- Vérifiez que votre serveur est accessible publiquement
- Utilisez un service comme ngrok pour les tests locaux
- Configurez correctement le firewall

## 📞 Support

Pour toute question sur l'intégration Cauris:
- Documentation Cauris: https://docs.cauris.com
- Support Cauris: support@cauris.com

## 🔄 Mise à jour

Pour mettre à jour le SDK Cauris:

```bash
pip install --upgrade cauris
```

## 📝 Notes importantes

- Les paiements Airtel Money expirent après 15 minutes par défaut
- L'utilisateur doit valider le paiement sur son téléphone via USSD
- Le webhook doit être accessible publiquement en production
- Testez toujours en mode test avant de passer en production
