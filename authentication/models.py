from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError('L\'adresse email est obligatoire')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)

class User(AbstractUser):
    username = None  # On utilise l'email comme identifiant
    email = models.EmailField(unique=True)
    nom = models.CharField(max_length=255) # Pour stocker "Nom Complet"
    role = models.CharField(max_length=50, default='Apprenant') # Interne, Docteur, etc.

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nom']

    objects = UserManager()

    def __str__(self):
        return self.email