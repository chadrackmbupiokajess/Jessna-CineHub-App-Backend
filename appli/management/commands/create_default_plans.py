from django.core.management.base import BaseCommand
from appli.models import SubscriptionPlan

class Command(BaseCommand):
    help = 'Crée les plans d\'abonnement par défaut'

    def handle(self, *args, **options):
        plans = [
            {
                'name': 'Mensuel',
                'description': 'Accès illimité à tous les films et séries pendant 30 jours',
                'price': 9.99,
                'duration_days': 30,
                'features': [
                    'Accès illimité aux films et séries',
                    'Qualité HD',
                    '2 écrans simultanés',
                    'Téléchargement hors ligne'
                ]
            },
            {
                'name': 'Trimestriel',
                'description': 'Accès illimité à tous les films et séries pendant 90 jours avec économie',
                'price': 24.99,
                'duration_days': 90,
                'features': [
                    'Accès illimité aux films et séries',
                    'Qualité Full HD',
                    '4 écrans simultanés',
                    'Téléchargement hors ligne',
                    'Économie de 17%'
                ]
            },
            {
                'name': 'Annuel',
                'description': 'Meilleur offre: accès illimité pendant 365 jours avec économie maximale',
                'price': 79.99,
                'duration_days': 365,
                'features': [
                    'Accès illimité aux films et séries',
                    'Qualité 4K Ultra HD',
                    'Écrans illimités',
                    'Téléchargement hors ligne illimité',
                    'Économie de 33%',
                    'Support prioritaire'
                ]
            }
        ]

        for plan_data in plans:
            plan, created = SubscriptionPlan.objects.get_or_create(
                name=plan_data['name'],
                defaults={
                    'description': plan_data['description'],
                    'price': plan_data['price'],
                    'duration_days': plan_data['duration_days'],
                    'features': plan_data['features']
                }
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f'Plan créé: {plan.name}'))
            else:
                self.stdout.write(self.style.WARNING(f'Plan existe déjà: {plan.name}'))

        self.stdout.write(self.style.SUCCESS('Plans d\'abonnement créés avec succès!'))
