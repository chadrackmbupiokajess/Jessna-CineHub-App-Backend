from django.shortcuts import render
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from .models import AppUpdate, SubscriptionPlan, PaymentMethod, Subscription, Payment, Notification, UserProfile, WatchHistory, AppContent, PasswordResetToken
import hashlib
import json
import logging
import secrets
import requests
import os

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
                user_obj = User.objects.filter(username=username).first()

            user = authenticate(request, username=username, password=password)
            if user is not None:
                login(request, user)
                return JsonResponse({
                    'success': True,
                    'message': 'Connexion réussie',
                    'username': user.username
                })
            else:
                if user_obj is not None:
                    return JsonResponse({
                        'success': False,
                        'message': 'Mot de passe incorrect.'
                    }, status=401)
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
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': username,
                    'avatar_initial': username[0].upper() if username else 'U',
                    'bio': f'Bienvenue sur Jessna CinéHub, {username}.'
                }
            )
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

def hash_reset_token(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()

def build_password_reset_link(token):
    reset_base_url = getattr(settings, 'PASSWORD_RESET_LINK_BASE_URL', 'applicationmobile://reset-password')
    separator = '&' if '?' in reset_base_url else '?'
    return f"{reset_base_url}{separator}token={token}"

@csrf_exempt
def request_password_reset_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            email = (data.get('email') or '').strip().lower()

            if not email:
                return JsonResponse({
                    'success': False,
                    'message': 'Adresse e-mail requise'
                }, status=400)

            user = User.objects.filter(email__iexact=email).first()
            if not user:
                return JsonResponse({
                    'success': False,
                    'message': 'Aucun compte ne correspond a cette adresse e-mail.'
                }, status=404)

            PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())
            raw_token = secrets.token_urlsafe(40)
            PasswordResetToken.objects.create(
                user=user,
                token_hash=hash_reset_token(raw_token),
                expires_at=PasswordResetToken.default_expiry()
            )

            reset_link = build_password_reset_link(raw_token)
            subject = 'Reinitialisation de votre mot de passe Jessna CineHub'
            message = (
                f"Bonjour {user.username},\n\n"
                "Vous avez demande la reinitialisation de votre mot de passe Jessna CineHub.\n"
                f"Ouvrez ce lien pour definir un nouveau mot de passe:\n{reset_link}\n\n"
                "Ce lien expire dans 1 heure. Si vous n'etes pas a l'origine de cette demande, ignorez cet e-mail."
            )

            send_mail(
                subject,
                message,
                getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@jessnacinehub.com'),
                [user.email],
                fail_silently=False
            )

            return JsonResponse({
                'success': True,
                'message': 'Un e-mail de reinitialisation a ete envoye.'
            })
        except Exception as e:
            logger.exception('Password reset request failed')
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Methode non autorisee'}, status=405)

@csrf_exempt
def reset_password_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            token = (data.get('token') or '').strip()
            new_password = data.get('new_password') or ''
            confirm_password = data.get('confirm_password') or ''

            if not token or not new_password or not confirm_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Tous les champs sont requis'
                }, status=400)

            if new_password != confirm_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Les mots de passe ne correspondent pas.'
                }, status=400)

            reset_token = PasswordResetToken.objects.select_related('user').filter(
                token_hash=hash_reset_token(token)
            ).first()

            if not reset_token or not reset_token.is_valid():
                return JsonResponse({
                    'success': False,
                    'message': 'Lien de reinitialisation invalide ou expire.'
                }, status=400)

            try:
                validate_password(new_password, reset_token.user)
            except ValidationError as validation_error:
                return JsonResponse({
                    'success': False,
                    'message': ' '.join(validation_error.messages)
                }, status=400)

            user = reset_token.user
            user.set_password(new_password)
            user.save()
            PasswordResetToken.objects.filter(user=user, used_at__isnull=True).update(used_at=timezone.now())

            return JsonResponse({
                'success': True,
                'message': 'Mot de passe reinitialise avec succes.'
            })
        except Exception as e:
            logger.exception('Password reset failed')
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Methode non autorisee'}, status=405)

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
def app_update_view(request):
    if request.method == 'GET':
        try:
            update = AppUpdate.objects.filter(is_active=True).order_by('-updated_at').first()
            if not update:
                return JsonResponse({
                    'success': True,
                    'active': False,
                    'update_available': False,
                    'message': 'Aucune mise a jour active'
                })

            download_url = update.get_download_url(request)
            if not download_url:
                return JsonResponse({
                    'success': True,
                    'active': False,
                    'is_active': False,
                    'update_available': False,
                    'message': 'Aucun fichier APK disponible'
                })

            return JsonResponse({
                'success': True,
                'active': True,
                'is_active': True,
                'update_available': True,
                'version': update.version,
                'latest_version': update.version,
                'apk_url': download_url,
                'download_url': download_url,
                'message': update.message,
                'force_update': update.force_update,
                'updated_at': update.updated_at.isoformat()
            })
        except Exception as e:
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Methode non autorisee'}, status=405)

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
            profile, _ = UserProfile.objects.get_or_create(
                user=user,
                defaults={
                    'display_name': user.first_name or user.last_name or user.username,
                    'avatar_initial': (user.first_name or user.last_name or user.username)[0].upper() if (user.first_name or user.last_name or user.username) else 'U',
                    'bio': f'Bienvenue sur Jessna CinéHub, {user.username}.'
                }
            )

            if not profile.display_name:
                profile.display_name = user.first_name or user.last_name or user.username
            if not profile.avatar_initial:
                profile.avatar_initial = (profile.display_name or user.username)[0].upper()
            profile.save()

            subscription = Subscription.objects.filter(user=user).order_by('-created_at').first()
            completed_payment = Payment.objects.filter(subscription=subscription, status='completed').exists() if subscription else False
            if subscription and subscription.is_valid() and completed_payment:
                plan_name = subscription.plan.name
                plan_status = subscription.status
                has_subscription = True
                end_date = subscription.end_date.isoformat()
                auto_renew = subscription.auto_renew
            else:
                plan_name = 'Découverte'
                plan_status = 'inactive'
                has_subscription = False
                end_date = None
                auto_renew = False

            return JsonResponse({
                'success': True,
                'profile': {
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'display_name': profile.display_name,
                    'avatar_initial': profile.avatar_initial,
                    'avatar_color': profile.avatar_color,
                    'bio': profile.bio,
                    'phone': profile.phone,
                    'favorite_count': profile.favorite_count,
                    'recent_watch_count': profile.recent_watch_count,
                    'downloads_count': profile.downloads_count,
                    'member_since': user.date_joined.strftime('%m/%Y'),
                    'date_joined': user.date_joined.isoformat(),
                    'subscription': {
                        'has_subscription': has_subscription,
                        'plan_name': plan_name,
                        'status': plan_status,
                        'status_display': 'Actif' if has_subscription else 'Aucun abonnement',
                        'end_date': end_date,
                        'auto_renew': auto_renew,
                    }
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
            current_password = data.get('current_password')
            new_password = data.get('new_password')

            if not username or not current_password or not new_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Tous les champs sont requis'
                }, status=400)

            user = User.objects.get(username=username)

            # Vérifier l'ancien mot de passe
            if not user.check_password(current_password):
                return JsonResponse({
                    'success': False,
                    'message': 'Mot de passe actuel incorrect'
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

@csrf_exempt
def add_to_watch_history(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur non trouvé'
                }, status=404)
            
            # Créer ou mettre à jour l'historique
            movie_slug = data.get('movie_slug')
            season = data.get('season')
            episode = data.get('episode')
            
            # Pour les séries, on vérifie si c'est le même épisode
            if season and episode:
                existing = WatchHistory.objects.filter(
                    user=user,
                    movie_slug=movie_slug,
                    season=season,
                    episode=episode
                ).first()
            else:
                # Pour les films, on vérifie si c'est le même film
                existing = WatchHistory.objects.filter(
                    user=user,
                    movie_slug=movie_slug,
                    season__isnull=True,
                    episode__isnull=True
                ).first()
            
            if existing:
                # Mettre à jour l'entrée existante
                existing.progress_percentage = data.get('progress_percentage', 0)
                existing.duration_watched = data.get('duration_watched', 0)
                existing.watched_at = timezone.now()
                existing.save()
            else:
                # Créer une nouvelle entrée
                WatchHistory.objects.create(
                    user=user,
                    movie_title=data.get('movie_title'),
                    movie_slug=movie_slug,
                    movie_poster=data.get('movie_poster', ''),
                    content_type=data.get('content_type', 'movie'),
                    season=season,
                    episode=episode,
                    episode_title=data.get('episode_title', ''),
                    progress_percentage=data.get('progress_percentage', 0),
                    duration_watched=data.get('duration_watched', 0)
                )
            
            return JsonResponse({
                'success': True,
                'message': 'Historique mis à jour'
            })
        except Exception as e:
            logger.error(f"Erreur ajout historique: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def get_watch_history(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur non trouvé'
                }, status=404)
            
            history = WatchHistory.objects.filter(user=user)[:50]  # Limiter à 50 entrées
            
            history_data = []
            for item in history:
                history_data.append({
                    'id': item.id,
                    'movie_title': item.movie_title,
                    'movie_slug': item.movie_slug,
                    'movie_poster': item.movie_poster,
                    'content_type': item.content_type,
                    'season': item.season,
                    'episode': item.episode,
                    'episode_title': item.episode_title,
                    'watched_at': item.watched_at.isoformat(),
                    'progress_percentage': item.progress_percentage,
                    'duration_watched': item.duration_watched
                })
            
            return JsonResponse({
                'success': True,
                'history': history_data
            })
        except Exception as e:
            logger.error(f"Erreur récupération historique: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def payment_history_view(request):
    if request.method == 'GET':
        try:
            username = request.GET.get('username')
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur non trouvé'
                }, status=404)
            
            # Récupérer les paiements via les abonnements de l'utilisateur
            subscriptions = Subscription.objects.filter(user=user)
            payments = Payment.objects.filter(subscription__in=subscriptions).order_by('-created_at')[:20]
            
            payment_data = []
            for payment in payments:
                payment_method_name = 'Non spécifié'
                if payment.payment_method:
                    payment_method_name = payment.payment_method.get_payment_type_display()
                
                payment_data.append({
                    'id': payment.id,
                    'amount': str(payment.amount),
                    'status': payment.status,
                    'transaction_id': payment.transaction_id,
                    'payment_date': payment.payment_date.isoformat() if payment.payment_date else None,
                    'created_at': payment.created_at.isoformat(),
                    'plan_name': payment.subscription.plan.name if payment.subscription.plan else 'Inconnu',
                    'payment_method': payment_method_name,
                })
            
            return JsonResponse({
                'success': True,
                'payments': payment_data
            })
        except Exception as e:
            logger.error(f"Erreur récupération historique paiement: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def update_phone_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            phone = data.get('phone')
            
            try:
                user = User.objects.get(username=username)
            except User.DoesNotExist:
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur non trouvé'
                }, status=404)
            
            # Mettre à jour le numéro de téléphone dans le profil
            profile, created = UserProfile.objects.get_or_create(user=user)
            profile.phone = phone
            profile.save()
            
            return JsonResponse({
                'success': True,
                'message': 'Numéro de téléphone mis à jour'
            })
        except Exception as e:
            logger.error(f"Erreur mise à jour téléphone: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
@csrf_exempt
def app_content_view(request):
    if request.method == 'GET':
        try:
            content_type = request.GET.get('content_type')
            
            if content_type:
                # Récupérer un contenu spécifique
                try:
                    content = AppContent.objects.get(content_type=content_type, is_active=True)
                    return JsonResponse({
                        'success': True,
                        'content': {
                            'content_type': content.content_type,
                            'content_type_display': content.get_content_type_display(),
                            'title': content.title,
                            'subtitle': content.subtitle,
                            'content': content.content,
                            'contact_email': content.contact_email,
                            'contact_phone': content.contact_phone,
                        }
                    })
                except AppContent.DoesNotExist:
                    return JsonResponse({
                        'success': False,
                        'message': 'Contenu non trouvé'
                    }, status=404)
            else:
                # Récupérer tous les contenus actifs
                contents = AppContent.objects.filter(is_active=True)
                contents_data = []
                for content in contents:
                    contents_data.append({
                        'content_type': content.content_type,
                        'content_type_display': content.get_content_type_display(),
                        'title': content.title,
                        'subtitle': content.subtitle,
                        'content': content.content,
                        'contact_email': content.contact_email,
                        'contact_phone': content.contact_phone,
                    })
                
                return JsonResponse({
                    'success': True,
                    'contents': contents_data
                })
        except Exception as e:
            logger.error(f"Erreur récupération contenu: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)


@csrf_exempt
def update_profile_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            display_name = data.get('display_name')
            email = data.get('email')
            phone = data.get('phone')
            bio = data.get('bio')

            if not username:
                return JsonResponse({
                    'success': False,
                    'message': 'Nom d utilisateur requis'
                }, status=400)

            user = User.objects.get(username=username)
            profile, _ = UserProfile.objects.get_or_create(user=user)

            if display_name is not None:
                profile.display_name = display_name
                profile.avatar_initial = display_name[0].upper() if display_name else 'U'
            
            if phone is not None:
                profile.phone = phone
            
            if bio is not None:
                profile.bio = bio
            
            profile.save()

            if email is not None and email != user.email:
                if User.objects.filter(email=email).exclude(username=username).exists():
                    return JsonResponse({
                        'success': False,
                        'message': 'Cet email est deja utilise'
                    }, status=400)
                user.email = email
                user.save()

            return JsonResponse({
                'success': True,
                'message': 'Profil mis a jour avec succes',
                'profile': {
                    'username': user.username,
                    'email': user.email,
                    'display_name': profile.display_name,
                    'phone': profile.phone,
                    'bio': profile.bio,
                    'avatar_initial': profile.avatar_initial,
                }
            })
        except User.DoesNotExist:
            return JsonResponse({
                'success': False,
                'message': 'Utilisateur non trouve'
            }, status=404)
        except Exception as e:
            logger.error(f'Erreur mise a jour profil: {e}')
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Methode non autorisee'}, status=405)

@csrf_exempt
def cinetpay_initiate_payment_view(request):
    """Endpoint pour initialiser un paiement CinetPay"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            plan_id = data.get('plan_id')
            amount = data.get('amount')
            
            if not username or not plan_id or not amount:
                return JsonResponse({
                    'success': False,
                    'message': 'Paramètres manquants: username, plan_id, amount'
                }, status=400)
            
            try:
                user = User.objects.get(username=username)
                plan = SubscriptionPlan.objects.get(id=plan_id)
                profile = UserProfile.objects.get(user=user)
            except (User.DoesNotExist, SubscriptionPlan.DoesNotExist, UserProfile.DoesNotExist):
                return JsonResponse({
                    'success': False,
                    'message': 'Utilisateur ou plan non trouvé'
                }, status=404)
            
            transaction_id = f"CINETPAY-{username}-{plan_id}-{int(timezone.now().timestamp())}"
            
            # Créer une méthode de paiement CinetPay
            payment_method = PaymentMethod.objects.create(
                user=user,
                payment_type='cinetpay',
                account_number='CINETPAY',
                account_name='CinetPay Payment'
            )
            
            # Créer l'abonnement en attente avec les dates
            start_date = timezone.now()
            end_date = start_date + timedelta(days=plan.duration_days)
            
            subscription = Subscription.objects.create(
                user=user,
                plan=plan,
                status='pending',
                payment_method=payment_method,
                start_date=start_date,
                end_date=end_date
            )
            
            # Créer le paiement
            payment = Payment.objects.create(
                subscription=subscription,
                payment_method=payment_method,
                amount=amount,
                status='pending',
                transaction_id=transaction_id
            )
            
            api_key = os.environ.get('CINETPAY_API_KEY', '')
            api_password = os.environ.get('CINETPAY_API_PASSWORD', '')
            
            logger.info(f'CinetPay Config - API_KEY: {api_key[:10]}... if api_key else "MISSING", API_PASSWORD: {"SET" if api_password else "MISSING"}')
            
            if not api_key or not api_password:
                return JsonResponse({
                    'success': False,
                    'message': 'Configuration CinetPay manquante (API_KEY ou API_PASSWORD)'
                }, status=500)
            
            # Utiliser le SDK Python officiel
            try:
                from cinetpay import CinetPayClient, ClientConfig, CountryCredentials, PaymentRequest
                
                client = CinetPayClient(ClientConfig(
                    credentials={
                        settings.CINETPAY_COUNTRY: CountryCredentials(
                            api_key=api_key,
                            api_password=api_password,
                        ),
                    },
                    debug=True,
                ))
                
                payment = client.payment.initialize(
                    PaymentRequest(
                        currency='XOF',
                        merchant_transaction_id=transaction_id,
                        amount=int(float(amount) * 1000),
                        lang='fr',
                        designation=f'Abonnement {plan.name} - {username}',
                        client_email=user.email or 'client@example.com',
                        client_first_name=profile.display_name or username,
                        client_last_name='Client',
                        client_phone_number=profile.phone.replace(' ', '') if profile.phone else '+243000000000',
                        success_url=settings.CINETPAY_RETURN_URL,
                        failed_url=settings.CINETPAY_RETURN_URL,
                        notify_url=settings.CINETPAY_NOTIFY_URL,
                        channel='PUSH',
                    ),
                    settings.CINETPAY_COUNTRY,
                )
                
                if payment.payment_url:
                    return JsonResponse({
                        'success': True,
                        'payment_url': payment.payment_url,
                        'transaction_id': transaction_id
                    })
                else:
                    return JsonResponse({
                        'success': False,
                        'message': 'Erreur lors de l\'initialisation du paiement'
                    }, status=400)
                    
            except ImportError:
                # Fallback si le SDK n'est pas installé
                logger.error('SDK cinetpay-python non installé')
                return JsonResponse({
                    'success': False,
                    'message': 'SDK CinetPay non installé. Installez avec: pip install cinetpay-python'
                }, status=500)
            except Exception as e:
                logger.error(f'Erreur SDK CinetPay: {e}')
                return JsonResponse({
                    'success': False,
                    'message': f'Erreur SDK: {str(e)}'
                }, status=500)
                
        except Exception as e:
            logger.error(f'Erreur CinetPay initiate payment: {e}')
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)

@csrf_exempt
def cinetpay_notify_view(request):
    """Endpoint IPN CinetPay pour recevoir les notifications de paiement"""
    if request.method == 'POST':
        try:
            data = request.POST if request.content_type == 'multipart/form-data' else json.loads(request.body)
            
            transaction_id = data.get('cpm_trans_id')
            site_id = data.get('cpm_site_id')
            signature = data.get('signature')
            
            if not transaction_id:
                logger.error('CinetPay notify: transaction_id manquant')
                return HttpResponse('transaction_id manquant', status=400)
            
            logger.info(f'CinetPay notify reçu: transaction_id={transaction_id}, site_id={site_id}')
            
            try:
                payment = Payment.objects.get(transaction_id=transaction_id)
                logger.info(f'Paiement trouvé: {payment.id}, statut actuel: {payment.status}')
                
                if payment.status == 'completed':
                    return HttpResponse('Paiement déjà traité')
                
                payment_status = data.get('cpm_payment_status', 'pending')
                if payment_status == 'ACCEPTED':
                    payment.status = 'completed'
                    payment.payment_date = timezone.now()
                    
                    if payment.subscription:
                        subscription = payment.subscription
                        subscription.status = 'active'
                        subscription.save()
                        logger.info(f'Abonnement activé pour utilisateur: {subscription.user.username}')
                elif payment_status == 'REJECTED':
                    payment.status = 'failed'
                else:
                    payment.status = 'pending'
                
                payment.save()
                return HttpResponse('Notification traitée avec succès')
                
            except Payment.DoesNotExist:
                logger.error(f'Paiement non trouvé pour transaction_id: {transaction_id}')
                return HttpResponse('Paiement non trouvé', status=404)
                
        except Exception as e:
            logger.error(f'Erreur CinetPay notify: {e}')
            return HttpResponse(f'Erreur: {str(e)}', status=500)
    
    return HttpResponse('Méthode non autorisée', status=405)

@csrf_exempt
def cinetpay_return_view(request):
    """Endpoint de retour après paiement CinetPay"""
    if request.method == 'GET':
        try:
            transaction_id = request.GET.get('cpm_trans_id')
            
            if transaction_id:
                logger.info(f'CinetPay return: transaction_id={transaction_id}')
                return JsonResponse({
                    'success': True,
                    'transaction_id': transaction_id,
                    'message': 'Paiement traité'
                })
            
            return JsonResponse({
                'success': False,
                'message': 'transaction_id manquant'
            }, status=400)
            
        except Exception as e:
            logger.error(f'Erreur CinetPay return: {e}')
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=500)
    
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
