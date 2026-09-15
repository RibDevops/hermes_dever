from django.db import models

class AgendaItem(models.Model):
    date = models.CharField(max_length=50)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    download_url = models.URLField(max_length=500, blank=True, null=True)
    completed = models.BooleanField(default=False)
    external_id = models.CharField(max_length=255, unique=True, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.date} - {self.title} ({'Concluído' if self.completed else 'Pendente'})"
