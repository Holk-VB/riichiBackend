from rest_framework.response import Response
from rest_framework import generics, status
from rest_framework.decorators import authentication_classes, permission_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated


@authentication_classes([TokenAuthentication])
@permission_classes([IsAuthenticated])
class UserViewSet(generics.RetrieveAPIView):

    def get(self, request, *args, **kwargs):
        data = {
            'id': self.request.user.id,
            'username': self.request.user.username,
            'first_name': self.request.user.first_name,
            'last_name': self.request.user.last_name,
        }
        return Response(data, status.HTTP_200_OK)
