from django.urls import include, path
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from apps.api.views import ParcelViewSet
from apps.users.views import register

router = DefaultRouter()
router.register("parcels", ParcelViewSet, basename="parcel")

urlpatterns = [
    path("auth/token/", TokenObtainPairView.as_view(), name="token_obtain"),
    path("auth/token/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("auth/register/", register, name="register"),
    path("", include(router.urls)),
]