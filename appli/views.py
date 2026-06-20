from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from .models import SubscriptionPlan, PaymentMethod, Subscription, Payment
import json

@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            password = data.get('password')

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

            if subscription and subscription.is_valid():
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
            payment_method, created = PaymentMethod.objects.get_or_create(
                user=user,
                payment_type=payment_type,
                defaults={
                    'account_number': account_number,
                    'account_name': account_name
                }
            )

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

            # Simuler le traitement du paiement
            payment.status = 'completed'
            payment.payment_date = timezone.now()
            payment.transaction_id = f"TXN{payment.id}{timezone.now().timestamp()}"
            payment.save()

            # Activer l'abonnement
            subscription.status = 'active'
            subscription.save()

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
