from django.contrib.auth import authenticate, get_user_model
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.tokens import RefreshToken


User = get_user_model()


def build_auth_response(user):
    refresh = RefreshToken.for_user(user)
    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        'user': {
            'id': user.pk,
            'username': user.get_username(),
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'avatar_url': getattr(user, 'avatar_url', None),
        },
    }


class EmailPasswordLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        email = attrs.get('email', '').strip().lower()
        password = attrs.get('password', '')

        user = User.objects.filter(email__iexact=email).first()
        if user is None:
            user = User.objects.filter(username__iexact=email).first()

        if user is None:
            raise AuthenticationFailed('Nieprawidłowy e-mail lub hasło.')

        authenticated = authenticate(
            request=self.context.get('request'),
            username=user.get_username(),
            password=password,
        )
        if authenticated is None:
            raise AuthenticationFailed('Nieprawidłowy e-mail lub hasło.')

        return build_auth_response(authenticated)


class RegisterSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, min_length=8)
    display_name = serializers.CharField(max_length=255)

    def validate_email(self, value):
        normalized = value.strip().lower()
        if User.objects.filter(username=normalized).exists():
            raise serializers.ValidationError('Konto z tym adresem e-mail już istnieje.')
        if User.objects.filter(email__iexact=normalized).exists():
            raise serializers.ValidationError('Konto z tym adresem e-mail już istnieje.')
        return normalized

    def create(self, validated_data):
        display_name = validated_data['display_name'].strip()
        parts = display_name.split(maxsplit=1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ''

        user = User.objects.create_user(
            username=validated_data['email'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=first_name,
            last_name=last_name,
        )
        return user


class MeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name', 'avatar_url')


class MeUpdateSerializer(serializers.ModelSerializer):
    display_name = serializers.CharField(required=False, allow_blank=True, write_only=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'avatar_url', 'display_name')
        extra_kwargs = {
            'email': {'required': False},
            'first_name': {'required': False},
            'last_name': {'required': False},
            'avatar_url': {'required': False},
        }

    def validate(self, attrs):
        display_name = attrs.pop('display_name', None)
        if display_name is not None:
            trimmed = display_name.strip()
            if not trimmed:
                raise serializers.ValidationError({'display_name': 'Podaj imię i nazwisko.'})
            parts = trimmed.split(maxsplit=1)
            attrs['first_name'] = parts[0]
            attrs['last_name'] = parts[1] if len(parts) > 1 else ''
        return attrs
