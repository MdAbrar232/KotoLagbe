from django.db import models

class Place(models.Model):
    name = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    area = models.CharField(max_length=150)
    address = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    average_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name