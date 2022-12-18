from django.db.models.signals import post_save
from django.dispatch import receiver
from games.models import Hand
import time


@receiver(post_save, sender=Hand)
def call_phase_timer(sender, instance: Hand, created, **kwargs):
    if instance.in_call_phase:
        time.sleep(10)  # works synchronously
        instance.end_call_phase()
