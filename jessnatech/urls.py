"""
URL configuration for jessnatech project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from appli import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/login/', views.login_view, name='login'),
    path('api/register/', views.register_view, name='register'),
    path('api/subscription-plans/', views.subscription_plans_view, name='subscription-plans'),
    path('api/user-subscription/', views.user_subscription_view, name='user-subscription'),
    path('api/create-subscription/', views.create_subscription_view, name='create-subscription'),
    path('api/payment-methods/', views.user_payment_methods_view, name='payment-methods'),
    path('api/add-payment-method/', views.add_payment_method_view, name='add-payment-method'),
    path('api/subscription-history/', views.subscription_history_view, name='subscription-history'),
    path('api/notifications/', views.notifications_view, name='notifications'),
    path('api/check-subscription-expiry/', views.check_subscription_expiry_view, name='check-subscription-expiry'),
    path('api/payment-webhook/', views.payment_webhook_view, name='payment-webhook'),
    path('api/user-profile/', views.user_profile_view, name='user-profile'),
    path('api/change-password/', views.change_password_view, name='change-password'),
    path('api/watch-history/', views.get_watch_history, name='watch-history'),
    path('api/add-to-watch-history/', views.add_to_watch_history, name='add-to-watch-history'),
    path('api/payment-history/', views.payment_history_view, name='payment-history'),
]
