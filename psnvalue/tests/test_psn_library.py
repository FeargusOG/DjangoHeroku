import os
import json
import datetime
from django.test import TestCase
from django.utils import timezone
from ..models import Library, GameList
from ..psn_library import PSNLibrary
from ..psn_library_dao import PSNLibraryDAO

# Create your tests here.
class PSNLibraryTestCase(TestCase):

    TEST_LIBRARY = None
    TEST_LIBRARY_NAME = "test_lib"
    TEST_LIBRARY_STDEV = 0.81955041074842
    TEST_LIBRARY_MEAN = 4.02023510971787
    TEST_URL = "test_url"
    TEST_TIME_DELTA_MIN = 1

    DARK_SOULS_III_FILENAME = 'test_data/DarkSoulsIII_FullGame.json'
    DARK_SOULS_III_GAME = None
    DARK_SOULS_III_DETAILED_GAME_JSON = None
    DARK_SOULS_III_ID = "EP0700-CUSA03365_00-DARKSOULS3000000"
    DARK_SOULS_III_NAME = "DARK SOULS™ III"
    DARK_SOULS_III_AGE_RATING = 16
    DARK_SOULS_III_PRICE = 6999
    DARK_SOULS_III_DISCOUNT = 0
    DARK_SOULS_III_RATING = 4.80
    DARK_SOULS_III_RATING_COUNT = 10316
    DARK_SOULS_III_WEIGHTED_RATING = 91.898
    DARK_SOULS_III_VALUE = 131

    DRAGON_AGE_INQUISITION_FILENAME = 'test_data/DragonAgeInquisition_FullGame.json'
    DRAGON_AGE_INQUISITION_GAME = None
    DRAGON_AGE_INQUISITION_DETAILED_GAME_JSON = None
    DRAGON_AGE_INQUISITION_ID = "EP0006-CUSA00503_00-DAINQUISITION000"
    DRAGON_AGE_INQUISITION_NAME = "Dragon Age™: Inquisition"
    DRAGON_AGE_INQUISITION_AGE_RATING = 18
    DRAGON_AGE_INQUISITION_PRICE = 1999
    DRAGON_AGE_INQUISITION_BASE_PRICE = 799
    DRAGON_AGE_INQUISITION_PLUS_PRICE = 599
    DRAGON_AGE_INQUISITION_BASE_DISCOUNT = 60
    DRAGON_AGE_INQUISITION_PLUS_DISCOUNT = 70
    DRAGON_AGE_INQUISITION_RATING = 4.57
    DRAGON_AGE_INQUISITION_RATING_COUNT = 20281
    DRAGON_AGE_INQUISITION_WEIGHTED_RATING = 169.888
    DRAGON_AGE_INQUISITION_BASE_VALUE = 3402
    DRAGON_AGE_INQUISITION_PLUS_VALUE = 4822

    def setUp(self):
        self.TEST_LIBRARY = Library.objects.create(library_name=self.TEST_LIBRARY_NAME, library_url=self.TEST_URL, library_rating_stdev=self.TEST_LIBRARY_STDEV, library_rating_mean=self.TEST_LIBRARY_MEAN)
        self.DARK_SOULS_III_GAME = GameList.objects.create(game_id=self.DARK_SOULS_III_ID, game_name=self.DARK_SOULS_III_NAME, json_url=self.TEST_URL, image_url=self.TEST_URL, image_datastore_url=self.TEST_URL, age_rating=self.DARK_SOULS_III_AGE_RATING, library_fk=self.TEST_LIBRARY)
        self.DRAGON_AGE_INQUISITION_GAME = GameList.objects.create(game_id=self.DRAGON_AGE_INQUISITION_ID, game_name=self.DRAGON_AGE_INQUISITION_NAME, json_url=self.TEST_URL, image_url=self.TEST_URL, image_datastore_url=self.TEST_URL, age_rating=self.DRAGON_AGE_INQUISITION_AGE_RATING, library_fk=self.TEST_LIBRARY)

        dark_souls_III_file = os.path.join(os.path.dirname(__file__), self.DARK_SOULS_III_FILENAME)
        with open(dark_souls_III_file) as data_file:
            self.DARK_SOULS_III_DETAILED_GAME_JSON = json.load(data_file)

        dragon_age_inquisition_file = os.path.join(os.path.dirname(__file__), self.DRAGON_AGE_INQUISITION_FILENAME)
        with open(dragon_age_inquisition_file) as data_file:
            self.DRAGON_AGE_INQUISITION_DETAILED_GAME_JSON = json.load(data_file)

    def test_update_game_with_discounts(self):
        psn_library = PSNLibrary()
        psn_library_dao = PSNLibraryDAO()

        self.assertTrue(self.DRAGON_AGE_INQUISITION_GAME != None)
        psn_library.update_game(self.TEST_LIBRARY, self.DRAGON_AGE_INQUISITION_DETAILED_GAME_JSON, self.DRAGON_AGE_INQUISITION_GAME)
        game = psn_library_dao.get_game(self.TEST_LIBRARY, self.DRAGON_AGE_INQUISITION_ID)

        self.assertTrue(game != None)
        self.assertEqual(game.game_id, self.DRAGON_AGE_INQUISITION_ID)
        self.assertEqual(game.game_name, self.DRAGON_AGE_INQUISITION_NAME)
        self.assertEqual(game.age_rating, self.DRAGON_AGE_INQUISITION_AGE_RATING)
        self.assertEqual(game.library_fk, self.TEST_LIBRARY)
        self.assertTrue((timezone.now() - game.last_updated) < datetime.timedelta(minutes=self.TEST_TIME_DELTA_MIN))
        self.assertEqual(game.json_url, self.TEST_URL)
        self.assertEqual(game.image_url, self.TEST_URL)
        self.assertEqual(game.image_datastore_url, self.TEST_URL)
        self.assertEqual(game.price, self.DRAGON_AGE_INQUISITION_PRICE)
        self.assertEqual(game.base_price, self.DRAGON_AGE_INQUISITION_BASE_PRICE)
        self.assertEqual(game.plus_price, self.DRAGON_AGE_INQUISITION_PLUS_PRICE)
        self.assertEqual(game.base_discount, self.DRAGON_AGE_INQUISITION_BASE_DISCOUNT)
        self.assertEqual(game.plus_discount, self.DRAGON_AGE_INQUISITION_PLUS_DISCOUNT)
        self.assertEqual(game.rating, self.DRAGON_AGE_INQUISITION_RATING)
        self.assertEqual(game.rating_count, self.DRAGON_AGE_INQUISITION_RATING_COUNT)
        self.assertEqual(game.weighted_rating, self.DRAGON_AGE_INQUISITION_WEIGHTED_RATING)
        self.assertEqual(game.base_value_score, self.DRAGON_AGE_INQUISITION_BASE_VALUE)
        self.assertEqual(game.plus_value_score, self.DRAGON_AGE_INQUISITION_PLUS_VALUE)

    def test_update_game_without_discounts(self):
        psn_library = PSNLibrary()
        psn_library_dao = PSNLibraryDAO()

        self.assertTrue(self.DARK_SOULS_III_DETAILED_GAME_JSON != None)
        psn_library.update_game(self.TEST_LIBRARY, self.DARK_SOULS_III_DETAILED_GAME_JSON, self.DARK_SOULS_III_GAME)
        game = psn_library_dao.get_game(self.TEST_LIBRARY, self.DARK_SOULS_III_ID)

        self.assertTrue(game != None)
        self.assertEqual(game.game_id, self.DARK_SOULS_III_ID)
        self.assertEqual(game.game_name, self.DARK_SOULS_III_NAME)
        self.assertEqual(game.age_rating, self.DARK_SOULS_III_AGE_RATING)
        self.assertEqual(game.library_fk, self.TEST_LIBRARY)
        self.assertTrue((timezone.now() - game.last_updated) < datetime.timedelta(minutes=self.TEST_TIME_DELTA_MIN))
        self.assertEqual(game.json_url, self.TEST_URL)
        self.assertEqual(game.image_url, self.TEST_URL)
        self.assertEqual(game.image_datastore_url, self.TEST_URL)
        self.assertEqual(game.price, self.DARK_SOULS_III_PRICE)
        self.assertEqual(game.base_price, self.DARK_SOULS_III_PRICE)
        self.assertEqual(game.plus_price, self.DARK_SOULS_III_PRICE)
        self.assertEqual(game.base_discount, self.DARK_SOULS_III_DISCOUNT)
        self.assertEqual(game.plus_discount, self.DARK_SOULS_III_DISCOUNT)
        self.assertEqual(game.rating, self.DARK_SOULS_III_RATING)
        self.assertEqual(game.rating_count, self.DARK_SOULS_III_RATING_COUNT)
        self.assertEqual(game.weighted_rating, self.DARK_SOULS_III_WEIGHTED_RATING)
        self.assertEqual(game.base_value_score, self.DARK_SOULS_III_VALUE)
        self.assertEqual(game.plus_value_score, self.DARK_SOULS_III_VALUE)
