import json
import requests
import collections
import time
from statistics import pstdev, mean
from django.db import transaction
from psycopg2 import IntegrityError
from django.utils import timezone
from datetime import datetime
from .models import Library, GameList, ContentDescriptors, GameContent

# These were place-in-time values that were determined.
DEFAULT_STDEV = 0.71
DEFAULT_MEAN = 4.11
# DEFAULT_GAME_PRICE - anything less than one causes division by zero errors
DEFAULT_GAME_PRICE = 1
DEFAULT_GAME_WEIGHTED_RATING = 1

class GenericLibrary:

    def get_or_create_content_descriptor(self, p_name, p_description):
        return ContentDescriptors.objects.get_or_create(content_name=p_name, content_description=p_description)[0]

    def get_or_create_game_content(self, p_game_obj, p_content_descriptor):
        return GameContent.objects.get_or_create(game_id_fk=p_game_obj, content_descriptor_fk=p_content_descriptor)[0]

    def get_all_game_objs(self, p_library_obj):
        return GameList.objects.all()

    def get_library_obj(self, p_library_id):
        return Library.objects.get(pk=p_library_id)

    def update_library_statistics(self, p_library_obj):
        list_of_game_ratings = self.get_list_of_all_game_ratings_in_lib(p_library_obj)
        p_library_obj.library_rating_stdev = self.calculate_standard_deviation(list_of_game_ratings)
        p_library_obj.library_rating_mean = self.calculate_mean(list_of_game_ratings)
        p_library_obj.last_updated = timezone.now()
        p_library_obj.save()

    def get_list_of_all_game_ratings_in_lib(self, p_library_obj):
        return GameList.objects.filter(library_fk=p_library_obj).values_list('rating', flat=True)

    def calculate_standard_deviation(self, p_list_of_ratings):
        if p_list_of_ratings:
            return pstdev(p_list_of_ratings)
        else:
            return DEFAULT_STDEV

    def calculate_mean(self, p_list_of_ratings):
        if p_list_of_ratings:
            return mean(p_list_of_ratings)
        else:
            return DEFAULT_MEAN

    def game_exists_in_db(self, p_library_obj, p_game_id):
        return (GameList.objects.filter(game_id=p_game_id, library_fk=p_library_obj).count() != 0)

    def get_game_obj(self, p_library_obj, p_game_id):
        game_obj = None
        try:
            game_obj = GameList.objects.get(game_id=p_game_id, library_fk=p_library_obj)
        except GameList.DoesNotExist:
            pass
        return game_obj

    def add_skeleton_game_list_entry_to_db(self, p_g_id, p_g_name, p_g_url, p_g_thumb, p_g_thumb_b64, p_g_age, p_library_obj):
        return GameList.objects.create(game_id=p_g_id, game_name=p_g_name, json_url=p_g_url, image_url=p_g_thumb, image_data=p_g_thumb_b64, age_rating=p_g_age, library_fk=p_library_obj)

    # Calculate value based on the price and discount relative to the weighted rating.
    def calculate_game_value(self, p_game_obj, p_plus):
        game_price = 0.0
        game_rating = 0.0
        discount_weight = 0.0

        # Determine the final price, accounting for free games
        if(p_plus == True):
            game_price = p_game_obj.plus_price
        else:
            game_price = p_game_obj.base_price

        game_price = round(game_price if game_price > 0.0 else DEFAULT_GAME_PRICE)

        # Determine the weight to apply to the discount.
        if(p_plus == True):
            discount_weight = 1+(p_game_obj.plus_discount/100)
        else:
            discount_weight = 1+(p_game_obj.base_discount/100)

        # Apply the discount weight to the weighted rating.
        if(self.rating_above_mean(p_game_obj)):
            game_rating = ((p_game_obj.weighted_rating)*discount_weight)*100
        else:
            game_rating = ((p_game_obj.weighted_rating)/discount_weight)*100

        return round(1/(game_price/game_rating)*100)

    # Apply a weight based on the rating deviation from the mean and the count of ratings.
    def apply_weighted_game_rating(self, p_library_obj, p_game_obj):
        # Determine if this game is above or below the mean rating.
        # Necessary for applying different weighting algorithm.
        aboveMean = self.rating_above_mean(p_game_obj)

        # Determine the weight to apply to rating count.
        countVal = (float(p_game_obj.rating_count)/125)

        # Determine weighting to apply based on rating deviation from the mean.
        ratingConstant = 1 if aboveMean else -1
        ratingVal = round((float(p_game_obj.rating)) * (ratingConstant+((float(p_game_obj.rating) - DEFAULT_MEAN)/DEFAULT_STDEV)),2)

        # Apply different weights depending if the game rating is above or below mean.
        finalVal = 0
        if(aboveMean):
            finalVal = (ratingVal+countVal)
        else:
            finalVal = (ratingVal-countVal)

        # Account for a weighted rating of zero
        return DEFAULT_GAME_WEIGHTED_RATING if finalVal == 0.0 else finalVal

    def rating_above_mean(self, p_game_obj):
        return (((float(p_game_obj.rating) - DEFAULT_MEAN)/DEFAULT_STDEV) > 0)

    def update_game_obj(self, p_game_obj):
        p_game_obj.last_updated = timezone.now()
        p_game_obj.save()
