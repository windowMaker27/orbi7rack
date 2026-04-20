from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import get_user_model

User = get_user_model()


@api_view(["POST"])
@permission_classes([AllowAny])
def register(request):
    username = request.data.get("username")
    email = request.data.get("email", "")
    password = request.data.get("password")

    if not username or not password:
        return Response({"error": "username et password requis"}, status=400)

    if User.objects.filter(username=username).exists():
        return Response({"error": "Nom d'utilisateur déjà utilisé"}, status=400)

    User.objects.create_user(username=username, email=email, password=password)
    return Response({"message": "Compte créé"}, status=status.HTTP_201_CREATED)
