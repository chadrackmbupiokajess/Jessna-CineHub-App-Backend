from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, PaymentMethod, Subscription, Payment, Notification
import json
import logging

logger = logging.getLogger(__name__)

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username_or_email = data.get('username')
            password = data.get('password')

            # Vérifier si c'est un email ou un nom d'utilisateur
            if '@' in username_or_email:
                # C'est un email, trouver le nom d'utilisateur correspondant
                try:
                    user_obj = User.objects.get(email=username_or_email)
                    username = user_obj.username
                except User.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Identifiants incorrects'
                    }, status=401)
            else:
                username = username_or_email

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie',
                    'username': user.username
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Identifiants incorrects'
                }, status=401)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def register_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if User.objects.filter(username=username).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Ce nom d\'utilisateur existe déjà'
                }, status=400)

            if User.objects.filter(email=email).exists():
                return JsonResponse({
                    'success': False,
                    'message': 'Cet email est déjà utilisé'
                }, status=400)

            user = User.objects.create_user(username=username, email=email, password=password)
            return JsonResponse({
                'success': True,
                'message': 'Inscription réussie',
                'username': user.username
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def subscription_plans_view(request):
    if request.method == 'GET':
        try:
            plans = SubscriptionPlan.objects.filter(is_active=True)
            plans_data = []
            for plan in plans:
                plans_data.append({
                    'id': plan.id,
                    'name': plan.name,
                    'description': plan.description,
                    'price': str(plan.price),
                    'duration_days': plan.duration_days,
                    'features': plan.features
                })
            return JsonResponse({
                'success': True,
                'plans': plans_data
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def user_subscription_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            subscription = Subscription.objects.filter(user=user).first()

            # Vérifier si l'abonnement est valide et le paiement est complété
            if subscription and subscription.is_valid():
                # Vérifier le statut du paiement
                payment = Payment.objects.filter(subscription=subscription).first()
                if payment and payment.status == 'completed':
                    return JsonResponse({
                        'success': True,
                        'has_subscription': True,
                        'subscription': {
                            'plan_name': subscription.plan.name,
                            'status': subscription.status,
                            'start_date': subscription.start_date.isoformat(),
                            'end_date': subscription.end_date.isoformat(),
                        'auto_renew': subscription.auto_renew
                    }
                })
            else:
                return JsonResponse({
                    'success': True,
                    'has_subscription': False,
                    'message': 'Aucun abonnement actif'
                })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def create_subscription_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            plan_id = data.get('plan_id')
            payment_type = data.get('payment_type')
            account_number = data.get('account_number', '')
            account_name = data.get('account_name', '')

            user = User.objects.get(username=username)
            plan = SubscriptionPlan.objects.get(id=plan_id)

            # Créer ou récupérer le moyen de paiement
            # Pour Espèce, ne pas stocker le numéro de compte
            account_number_to_store = account_number if payment_type != 'cash' else 'N/A'
            payment_method, created = PaymentMethod.objects.get_or_create(
                user=user,
                payment_type=payment_type,
                defaults={
                    'account_number': account_number_to_store,
                    'account_name': account_name,
                    'is_default': True
                }
            )

            # Si le moyen de paiement existe déjà, le mettre par défaut
            if not created:
                PaymentMethod.objects.filter(user=user).update(is_default=False)
                payment_method.is_default = True
                payment_method.account_number = account_number_to_store
                payment_method.account_name = account_name
                payment_method.save()

            # Créer l'abonnement
            start_date = timezone.now()
            end_date = start_date + timedelta(days=plan.duration_days)

            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                status='pending',
                start_date=start_date,
                end_date=end_date,
                payment_method=payment_method
            )

            # Créer le paiement
            payment = Payment.objects.create(
                subscription=subscription,
                payment_method=payment_method,
                amount=plan.price,
                status='pending'
            )

            # Validation manuelle via admin Django - pas d'API automatique
            reference = f"SUB{subscription.id}"

            # Créer le paiement en statut pending pour validation manuelle
            payment.status = 'pending'
            payment.transaction_id = f"MANUAL{reference}{timezone.now().timestamp()}"
            payment.save()

            # Créer une notification pour l'utilisateur que le paiement est en cours
            Notification.objects.create(
                user=user,
                notification_type='payment_pending',
                title='Paiement en cours',
                message=f'Votre paiement de {plan.price} $ est en attente de validation par l\'administrateur.',
                expires_at=timezone.now() + timedelta(days=7)
            )

            # Activer l'abonnement
            subscription.status = 'active'
            subscription.save()

            # Créer une notification d'expiration si l'abonnement expire dans moins de 7 jours
            days_until_expiry = (subscription.end_date - timezone.now()).days
            if days_until_expiry <= 7:
                Notification.objects.create(
                    user=user,
                    notification_type='subscription_expiring',
                    title='Abonnement expire bientôt',
                    message=f'Votre abonnement {plan.name} expire dans {days_until_expiry} jours. Pensez à le renouveler pour continuer à profiter de nos services.',
                    expires_at=subscription.end_date - timedelta(days=7) + timedelta(days=2)
                )

            return JsonResponse({
                'success': True,
                'message': 'Abonnement créé avec succès',
                'subscription': {
                    'plan_name': subscription.plan.name,
                    'status': subscription.status,
                    'start_date': subscription.start_date.isoformat(),
                    'end_date': subscription.end_date.isoformat()
                }
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except SubscriptionPlan.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Plan d\'abonnement non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def user_payment_methods_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            payment_methods = PaymentMethod.objects.filter(user=user)
            
            methods_data = []
            for method in payment_methods:
                methods_data.append({
                    'id': method.id,
                    'payment_type': method.payment_type,
                    'payment_type_display': method.get_payment_type_display(),
                    'account_number': method.account_number,
                    'account_name': method.account_name,
                    'is_default': method.is_default,
                    'created_at': method.created_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'payment_methods': methods_data
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def add_payment_method_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            payment_type = data.get('payment_type')
            account_number = data.get('account_number', '')
            account_name = data.get('account_name', '')
            is_default = data.get('is_default', False)

            user = User.objects.get(username=username)

            # Si c'est le moyen par défaut, désactiver les autres
            if is_default:
                PaymentMethod.objects.filter(user=user).update(is_default=False)

            payment_method = PaymentMethod.objects.create(
                user=user,
                payment_type=payment_type,
                account_number=account_number,
                account_name=account_name,
                is_default=is_default
            )

            return JsonResponse({
                'success': True,
                'message': 'Moyen de paiement ajouté avec succès',
                'payment_method': {
                    'id': payment_method.id,
                    'payment_type': payment_method.payment_type,
                    'payment_type_display': payment_method.get_payment_type_display(),
                    'account_number': payment_method.account_number,
                    'account_name': payment_method.account_name,
                    'is_default': payment_method.is_default
                }
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def subscription_history_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            limit = request.GET.get('limit', 10)
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            subscriptions = Subscription.objects.filter(user=user).order_by('-created_at')[:int(limit)]
            
            history_data = []
            for subscription in subscriptions:
                payments = Payment.objects.filter(subscription=subscription)
                payments_data = []
                for payment in payments:
                    payments_data.append({
                        'id': payment.id,
                        'amount': str(payment.amount),
                        'status': payment.status,
                        'status_display': payment.get_status_display(),
                        'transaction_id': payment.transaction_id,
                        'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                        'payment_method': payment.payment_method.get_payment_type_display() if payment.payment_method else None,
                        'created_at': payment.created_at.isoformat()
                    })
                
                history_data.append({
                    'id': subscription.id,
                    'plan_name': subscription.plan.name,
                    'plan_description': subscription.plan.description,
                    'plan_price': str(subscription.plan.price),
                    'plan_duration_days': subscription.plan.duration_days,
                    'status': subscription.status,
                    'status_display': subscription.get_status_display(),
                    'start_date': subscription.start_date.isoformat(),
                    'end_date': subscription.end_date.isoformat(),
                    'auto_renew': subscription.auto_renew,
                    'payment_method': subscription.payment_method.get_payment_type_display() if subscription.payment_method else None,
                    'payments': payments_data,
                    'created_at': subscription.created_at.isoformat(),
                    'updated_at': subscription.updated_at.isoformat()
                })
            
            return JsonResponse({
                'success': True,
                'subscription_history': history_data
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def notifications_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            notifications = Notification.objects.filter(user=user).order_by('-created_at')
            
            notifications_data = []
            for notification in notifications:
                notifications_data.append({
                    'id': notification.id,
                    'notification_type': notification.notification_type,
                    'title': notification.title,
                    'message': notification.message,
                    'is_read': notification.is_read,
                    'is_active': notification.is_active(),
                    'created_at': notification.created_at.isoformat(),
                    'expires_at': notification.expires_at.isoformat() if notification.expires_at else None
                })
            
            return JsonResponse({
                'success': True,
                'notifications': notifications_data
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            notification_id = data.get('notification_id')
            action = data.get('action', 'mark_read')  # mark_read, mark_all_read
            
            user = User.objects.get(username=username)
            
            if action == 'mark_read' and notification_id:
                notification = Notification.objects.get(id=notification_id, user=user)
                notification.is_read = True
                notification.save()
                return JsonResponse({
                    'success': True,
                    'message': 'Notification marquée comme lue'
                })
            elif action == 'mark_all_read':
                Notification.objects.filter(user=user).update(is_read=True)
                return JsonResponse({
                    'success': True,
                    'message': 'Toutes les notifications marquées comme lues'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'message': 'Action non valide'
                }, status=400)
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Notification.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Notification non trouvée'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def check_subscription_expiry_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            subscription = Subscription.objects.filter(user=user, status='active').first()
            
            if not subscription:
                return JsonResponse({
                    'success': True,
                    'has_subscription': False,
                    'expires_soon': False,
                    'days_remaining': 0
                })
            
            days_remaining = (subscription.end_date - timezone.now()).days
            expires_soon = days_remaining <= 7 and days_remaining > 0
            
            return JsonResponse({
                'success': True,
                'has_subscription': True,
                'expires_soon': expires_soon,
                'days_remaining': days_remaining,
                'end_date': subscription.end_date.isoformat(),
                'plan_name': subscription.plan.name
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def payment_webhook_view(request):
    """
    Webhook pour recevoir les notifications de paiement de Cauris
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            logger.info(f"Webhook reçu: {data}")
            
            # Vérifier le statut du paiement
            status = data.get('status')
            transaction_id = data.get('id')
            metadata = data.get('metadata', {})
            reference = metadata.get('reference')
            
            if status == 'success':
                # Trouver le paiement correspondant
                try:
                    payment = Payment.objects.filter(transaction_id=transaction_id).first()
                    if payment:
                        # Mettre à jour le statut du paiement
                        payment.status = 'completed'
                        payment.payment_date = timezone.now()
                        payment.save()
                        
                        # Activer l'abonnement
                        subscription = payment.subscription
                        subscription.status = 'active'
                        subscription.save()
                        
                        # Créer une notification de paiement réussi
                        Notification.objects.create(
                            user=subscription.user,
                            notification_type='payment_success',
                            title='Paiement réussi',
                            message=f'Votre paiement {transaction_id} a été validé avec succès.',
                            expires_at=timezone.now() + timedelta(days=2)
                        )
                        
                        logger.info(f"Paiement {transaction_id} validé avec succès")
                        return JsonResponse({'success': True, 'message': 'Paiement validé'})
                except Payment.DoesNotExist:
                    logger.error(f"Paiement {transaction_id} non trouvé")
                    return JsonResponse({'success': False, 'message': 'Paiement non trouvé'}, status=404)
            
            elif status == 'failed':
                # Mettre à jour le statut du paiement comme échoué
                try:
                    payment = Payment.objects.filter(transaction_id=transaction_id).first()
                    if payment:
                        payment.status = 'failed'
                        payment.save()
                        
                        logger.info(f"Paiement {transaction_id} échoué")
                        return JsonResponse({'success': True, 'message': 'Paiement échoué'})
                except Payment.DoesNotExist:
                    logger.error(f"Paiement {transaction_id} non trouvé")
                    return JsonResponse({'success': False, 'message': 'Paiement non trouvé'}, status=404)
            
            return JsonResponse({'success': True, 'message': 'Webhook reçu'})

        except Exception as e:
            logger.error(f"Erreur lors du traitement du webhook: {str(e)}")
            return JsonResponse({'success': False, 'message': str(e)}, status=400)

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def user_profile_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d\'utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)

            return JsonResponse({
                'success': True,
                'profile': {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'date_joined': user.date_joined.isoformat()
                }
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def change_password_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            old_password = data.get('old_password')
            new_password = data.get('new_password')

            if not username or not old_password or not new_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Tous les champs sont requis'
                }, status=400)

            user = User.objects.get(username=username)

            # Vérifier l'ancien mot de passe
            if not user.check_password(old_password):
                return JsonResponse({
                    'success': False,
                    'message': 'Ancien mot de passe incorrect'
                }, status=400)

            # Changer le mot de passe
            user.set_password(new_password)
            user.save()

            return JsonResponse({
                'success': True,
                'message': 'Mot de passe changé avec succès'
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
