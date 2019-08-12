from django.db import models
from django.utils.timezone import now

class ExportedOrder(models.Model):
    id = models.AutoField()
    order_id = models.IntegerField()
    created = models.DateTimeField(default=now, editable=False)

