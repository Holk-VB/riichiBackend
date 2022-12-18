from django.urls import path
from api.views import UserViewSet

urlpatterns = [
    path('user/', UserViewSet.as_view(), name='user'),
]
