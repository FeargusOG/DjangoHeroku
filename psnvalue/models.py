import datetime

from django.db import models
from django.utils import timezone

def last_day_timedate():
    return timezone.now() - datetime.timedelta(days=1)

class Library(models.Model):
    library_name = models.TextField(unique=True)
    last_updated = models.DateTimeField(default=timezone.now)
    library_url = models.TextField()
    library_rating_stdev = models.FloatField(default=0.0)
    library_rating_mean = models.FloatField(default=0.0)

    def __str__(self):
        return self.library_name

    def was_updated_within_last_day(self):
        return self.last_updated >= last_day_timedate()

class GameList(models.Model):
    game_id = models.TextField(unique=True)
    game_name = models.TextField()
    json_url = models.TextField()
    age_rating = models.IntegerField(default=0)
    library_fk = models.ForeignKey(Library, on_delete=models.CASCADE)
    last_updated = models.DateTimeField(default=timezone.now)
    # Thumbnail fields
    image_url = models.TextField()
    image_data = models.TextField()
    image_datastore_url = models.TextField(blank=True)
    # Price fields
    price = models.FloatField(default=0.0)
    base_price = models.FloatField(default=0.0)
    plus_price = models.FloatField(default=0.0)
    base_discount = models.IntegerField(default=0)
    plus_discount = models.IntegerField(default=0)
    # Rating fields
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    weighted_rating = models.FloatField(default=0.0)
    # Value fields
    base_value_score = models.IntegerField(default=0)
    plus_value_score = models.IntegerField(default=0)

    def __str__(self):
        return self.game_id + ": " + self.game_name

    def was_updated_within_last_day(self):
        return self.last_updated >= last_day_timedate()

class ContentDescriptors(models.Model):
    content_name = models.TextField(unique=True)
    content_description = models.TextField()

    def __str__(self):
        return self.content_name

class GameContent(models.Model):
    game_id_fk = models.ForeignKey(GameList, on_delete=models.CASCADE)
    content_descriptor_fk = models.ForeignKey(ContentDescriptors, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('game_id_fk', 'content_descriptor_fk',)
