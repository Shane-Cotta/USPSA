from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from classification.models import ShooterProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_profile(sender, instance, created, **kwargs):
    if created:
        ShooterProfile.objects.get_or_create(user=instance, defaults={"uspsa_number": f"AUTO-{instance.pk}"})
