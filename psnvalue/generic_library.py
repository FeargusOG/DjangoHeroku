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

class GenericLibrary:

    def get_all_game_objs(self, p_library_obj):
        return GameList.objects.all()

    def game_exists_in_db(self, p_library_obj, p_game_id):
        return (GameList.objects.filter(game_id=p_game_id, library_fk=p_library_obj).count() != 0)
