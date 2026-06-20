from django.contrib import admin
from .models import SubscriptionPlan, PaymentMethod, Subscription, Payment

@admin.register(SubscriptionPlan)
class SubscriptionPlanAdmin(admin.ModelAdmin):
    list_display = ['name', 'price', 'duration_days', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    list_display = ['user', 'payment_type', 'account_number', 'is_default', 'created_at']
    list_filter = ['payment_type', 'is_default', 'created_at']
    search_fields = ['user__username', 'account_number', 'account_name']
    readonly_fields = ['created_at']

@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = ['user', 'plan', 'status', 'start_date', 'end_date', 'auto_renew', 'created_at']
    list_filter = ['status', 'auto_renew', 'plan', 'created_at']
    search_fields = ['user__username', 'plan__name']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'start_date'

@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = ['subscription', 'amount', 'status', 'payment_method', 'payment_date', 'created_at']
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['transaction_id', 'subscription__user__username']
    readonly_fields = ['created_at', 'updated_at']
    date_hierarchy = 'payment_date'

# Register your models here.
