# Ajoutez cette fonction à la fin du fichier backend auth/appli/views.py
# Ensuite, ajoutez cette ligne à backend auth/jessnatech/urls.py:
# path('api/update-profile/', views.update_profile_view, name='update-profile'),

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
                    'message': 'Nom d\'utilisateur requis'
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
                        'message': 'Cet email est déjà utilisé'
                    }, status=400)
                user.email = email
                user.save()

            return JsonResponse({
                'success': True,
                'message': 'Profil mis à jour avec succès',
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
                'message': 'Utilisateur non trouvé'
            }, status=404)
        except Exception as e:
            logger.error(f"Erreur mise à jour profil: {e}")
            return JsonResponse({
                'success': False,
                'message': str(e)
            }, status=400)
    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'}, status=405)
