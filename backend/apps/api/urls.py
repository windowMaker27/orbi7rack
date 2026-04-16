from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

urlpatterns = [
    # Auth
    path('auth/token/',         TokenObtainPairView.as_view(),  name='token_obtain'),
    path('auth/token/refresh/', TokenRefreshView.as_view(),     name='token_refresh'),
    # Parcels — à compléter en phase 2
]
