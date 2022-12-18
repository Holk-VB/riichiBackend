from django.db import models


class Log(models.Model):
    name = models.CharField(max_length=255, null=False, blank=False)
    description = models.TextField(null=True, blank=True)
    origin = models.CharField(max_length=255, null=True, blank=True)
    target = models.CharField(max_length=255, null=True, blank=True)

    @staticmethod
    def create(name: str,
               description: str = None,
               origin: str = None,
               target: str = None):

        log = Log(name=name)
        if description:
            log.description = description
        if origin:
            log.origin = origin
        if target:
            log.target = target
        log.save()
        return log
