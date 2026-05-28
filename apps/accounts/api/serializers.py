from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


class UsernamePasswordLoginSerializer(serializers.Serializer):
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username = attrs.get("username", "")
        password = attrs.get("password", "")

        authenticated = authenticate(
            request=self.context.get("request"),
            username=username,
            password=password,
        )
        if authenticated is None:
            raise serializers.ValidationError({"username": "Invalid credentials."})

        refresh = RefreshToken.for_user(authenticated)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "user": {
                "id": authenticated.pk,
                "username": authenticated.get_username(),
                "email": authenticated.email,
                "first_name": authenticated.first_name,
                "last_name": authenticated.last_name,
                "avatar_url": getattr(authenticated, "avatar_url", None),
            },
        }


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ("id", "username", "email", "first_name", "last_name", "avatar_url")

