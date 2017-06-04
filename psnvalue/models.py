import datetime

from django.db import models
from django.utils import timezone

def last_day_timedate():
    return timezone.now() - datetime.timedelta(days=1)

class Library(models.Model):
    library_name = models.TextField(unique=True)
    last_updated = models.DateTimeField()
    total_results = models.IntegerField()
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
    image_url = models.TextField()
    age_rating = models.IntegerField(default=0)
    library_name = models.ForeignKey(Library, on_delete=models.CASCADE)

    def __str__(self):
        return self.game_id + ": " + self.game_name

class GamePrice(models.Model):
    game_id = models.OneToOneField(GameList, on_delete=models.CASCADE)
    last_updated = models.DateTimeField()
    base_price = models.FloatField(default=0.0)
    base_discount = models.IntegerField(default=0)
    plus_discount = models.IntegerField(default=0)

    def __str__(self):
        return self.game_id

    def was_updated_within_last_day(self):
        return self.last_updated >= last_day_timedate()

class GameRatings(models.Model):
    game_id = models.OneToOneField(GameList, on_delete=models.CASCADE)
    last_updated = models.DateTimeField()
    rating = models.FloatField(default=0.0)
    rating_count = models.IntegerField(default=0)
    weighted_rating = models.FloatField(default=0.0)

    def __str__(self):
        return self.game_id

    def was_updated_within_last_day(self):
        return self.last_updated >= last_day_timedate()

class GameValue(models.Model):
    game_id = models.OneToOneField(GameList, on_delete=models.CASCADE)
    value_score = models.IntegerField(default=0)

    def __str__(self):
        return self.game_id

class ContentDescriptors(models.Model):
    content_name = models.TextField()
    content_description = models.TextField()

    def __str__(self):
        return self.content_name

class GameContent(models.Model):
    game_id = models.ForeignKey(GameList, on_delete=models.CASCADE)
    content_name = models.ForeignKey(ContentDescriptors, on_delete=models.CASCADE)

    def __str__(self):
        return self.game_id + " - " + self.content_name
