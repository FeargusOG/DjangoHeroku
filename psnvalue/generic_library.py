import json
import requests
import collections
import time
from statistics import pstdev, mean
from django.db import transaction
from psycopg2 import IntegrityError
from django.utils import timezone
from datetime import datetime
from .models import Library, GameList, GamePrice, GameRatings, GameValue

# These were place-in-time values that were determined.
DEFAULT_STDEV = 0.71
DEFAULT_MEAN = 4.11

class GenericLibrary:
    m_stdev = DEFAULT_STDEV
    m_mean = DEFAULT_MEAN

    def get_id_for_game_id(self, p_game_id):
        return GameList.objects.get(game_id=p_game_id).id

    def get_list_of_all_game_ratings(self):
        return GameRatings.objects.values_list('rating', flat=True)

    def calculate_standard_deviation(self, p_list_of_ratings):
        return pstdev(p_list_of_ratings)

    def set_standard_deviation(self, p_library_id, p_new_stdev):
        lib_obj = Library.objects.get(id=p_library_id)
        lib_obj.library_rating_stdev = p_new_stdev
        lib_obj.save()

    def get_standard_deviation(self, p_library_id):
        return Library.objects.get(id=p_library_id).library_rating_stdev

    def calculate_mean(self, p_list_of_ratings):
        return mean(p_list_of_ratings)

    def set_mean(self, p_library_id, p_new_mean):
        lib_obj = Library.objects.get(id=p_library_id)
        lib_obj.library_rating_mean = p_new_mean
        lib_obj.save()

    def get_mean(self, p_library_id):
        return Library.objects.get(id=p_library_id).library_rating_mean

    def game_exists_in_db(self, p_library_id, p_game_id):
        return (GameList.objects.filter(game_id=p_game_id, library_name=p_library_id).count() != 0)

    def add_game_list_entry_to_db(self, p_g_id, p_g_name, p_g_url, p_g_thumb, p_g_age, p_library_obj):
        g_list_entry = None
        try:
            g_list_entry = GameList.objects.create(game_id=p_g_id, game_name=p_g_name, json_url=p_g_url, image_url=p_g_thumb, age_rating=p_g_age, library_name=p_library_obj)
        except Exception as e:
            g_list_entry = GameList.objects.get(game_id=p_g_id)        
        return g_list_entry

    def get_game_price(self, p_game_entry):
        g_game_price_obj = GamePrice.objects.get(game_id=p_game_entry)
        g_game_price = g_game_price_obj.base_price

        if(g_game_price_obj.plus_discount > 0):
            g_game_price = self.apply_game_discount(g_game_price, g_game_price_obj.plus_discount)
        elif(g_game_price_obj.base_discount > 0):
            g_game_price = self.apply_game_discount(g_game_price, g_game_price_obj.base_discount)

        return g_game_price

    def calculate_game_value(self, p_game_rating, p_game_price):
        fixed_price = round(p_game_price)
        fixed_rating = p_game_rating * 100
        return round(1/(fixed_price/fixed_rating)*100) 

    def apply_weighted_game_rating(self, p_game_rating):
        print("USING STDEV: ", self.m_stdev)
        return round((p_game_rating*10) + ((p_game_rating - self.m_mean)/self.m_stdev),2)

    def add_game_rating_entry(self, p_game_entry, p_rating_value, p_rating_count, p_weighted_rating):
        return GameRatings.objects.create(game_id=p_game_entry, last_updated=timezone.now(), rating=p_rating_value, rating_count=p_rating_count, weighted_rating=p_weighted_rating)

    def update_game_rating_entry(self, p_game_id, p_rating_value, p_rating_count, p_weighted_rating):
        game_obj = GameRatings.objects.get(game_id=p_game_id)
        game_obj.rating = p_rating_value
        game_obj.rating_count = p_rating_count
        game_obj.weighted_rating = p_weighted_rating
        game_obj.last_updated = timezone.now()
        game_obj.save()

    def add_game_price_entry(self, p_game_entry, p_price, p_base_discount, p_plus_discount):
        return GamePrice.objects.create(game_id=p_game_entry, last_updated=timezone.now(), base_price=p_price, base_discount=p_base_discount, plus_discount=p_plus_discount)

    def update_game_price_entry(self, p_game_id, p_price, p_base_discount, p_plus_discount):
        game_obj = GamePrice.objects.get(game_id=p_game_id)
        game_obj.base_price = p_price
        game_obj.base_discount = p_base_discount
        game_obj.plus_discount = p_plus_discount
        game_obj.last_updated = timezone.now()
        game_obj.save()

    def apply_game_discount(self, p_base_price, p_discount_percentage):
        return ((p_base_price*(100-p_discount_percentage))/100)

    def get_game_rating(self, p_game_entry):
        return GameRatings.objects.get(game_id=p_game_entry).rating

    def get_game_weighted_rating(self, p_game_entry):
        return GameRatings.objects.get(game_id=p_game_entry).weighted_rating

    def add_game_value_entry(self, p_game_entry, p_game_value):
        return GameValue.objects.create(game_id=p_game_entry, value_score=p_game_value)

    def update_game_value_entry(self, p_game_id, p_game_value):
        game_obj = GameValue.objects.get(game_id=p_game_id)
        game_obj.value_score = p_game_value
        game_obj.save()

    def set_game_age_rating(self, p_game_entry, p_new_age_rating):
        p_game_entry.age_rating = p_new_age_rating
        p_game_entry.save()

    def get_game_details_url_from_db(self, p_game_id):
        return GameList.objects.get(game_id=p_game_id).json_url

    def get_lib_url_from_db(self, p_lib_name):
        return Library.objects.get(library_name=p_lib_name).library_url
