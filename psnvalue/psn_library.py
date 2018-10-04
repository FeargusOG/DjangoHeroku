import json
import collections
import traceback
import base64
import cloudinary
import cloudinary.uploader
import cloudinary.api
from django.db import transaction
from django.utils import timezone
from datetime import datetime
from celery.utils.log import get_task_logger
from .psn_library_dao import PSNLibraryDAO
from .psn_store_api import PSNStoreAPI

#PSN Library Name
PSN_MODEL_LIBRARY_NAME = 'PS4'
#PSN Default Rating Value
PSN_MODEL_RATING_DEFAULT_VALUE = 1
#PSN Default Rating Count
PSN_MODEL_RATING_DEFAULT_COUNT = 0
#PSN Default Age Rating
PSN_DEFAULT_AGE_RATING = 0

###############################################################
#   These elements below are part of the PSN library's JSON   #
###############################################################
#PSN Each Game JSON element
PSN_JSON_ELEM_EACH_GAME = 'links'
#PSN Sub-Base Game JSON element i.e. bundles etc.
PSN_JSON_ELEM_SUB_GAME = 'parent_name'
#PSN Game release date
PSN_JSON_ELEM_RELEASE_DATE = 'release_date'
#PSN Game ID JSON element
PSN_JSON_ELEM_GAME_ID = 'id'
#PSN Game Name JSON element
PSN_JSON_ELEM_GAME_NAME = 'name'
#PSN Game Full Detials URL JSON element
PSN_JSON_ELEM_GAME_URL = 'url'
#PSN Game Image list JSON element
PSN_JSON_ELEM_GAME_IMAGES = 'images'
#PSN Game Image type JSON element
PSN_JSON_ELEM_GAME_IMGTYPE = 'type'
#PSN Game Image large thumb
PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_LRG = 1
#PSN Game Image small thumb
PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_SML = 2
#PSN Main Game details block - This element is part of both the library and game JSON!
PSN_JSON_ELEM_GAME_PRICE_BLOCK = 'default_sku'

####################################################################
#   These elements below are part of each individual game's JSON   #
####################################################################
# Element - The price of the game before discounts are applied
PSN_JSON_ELEM_GAME_PRICE = 'price'
# Parent Element - Block that contains the details of any discounts
PSN_JSON_ELEM_GAME_REWARDS = 'rewards'
# Element - The discount on the game for non-PSPlus members
PSN_JSON_ELEM_GAME_BASE_DISCOUNT = 'discount'
# Element - The price of the game after applying discount for non-PSPlus members
PSN_JSON_ELEM_GAME_BASE_PRICE = 'price'
# Element - The discount on the game for PSPlus members
PSN_JSON_ELEM_GAME_BONUS_DISCOUNT = 'bonus_discount'
# Element - The price of the game after applying discount for PSPlus members
PSN_JSON_ELEM_GAME_BONUS_PRICE = 'bonus_price'

# Parent Element - Block that contains all rating info
PSN_JSON_ELEM_GAME_RATING_BLOCK = 'star_rating'
# Element - The rating for this game
PSN_JSON_ELEM_GAME_RATING_VALUE = 'score'
# Element - The number of rating votes this game has recieved
PSN_JSON_ELEM_GAME_RATING_COUNT = 'total'

# Element - The age limit of this game
PSN_JSON_ELEM_GAME_AGERATING = 'age_limit'

# Parent Element - Block that contains list of content descriptors
PSN_JSON_ELEM_EACH_GAME_CONTENT = 'content_descriptors'
# Element - Name of content e.g. Language
PSN_JSON_ELEM_GAME_CONTENT_NAME = 'name'
# Element - Description of content e.g. Language
PSN_JSON_ELEM_GAME_CONTENT_DESCR = 'description'

class PSNLibrary:

    psn_library_dao = PSNLibraryDAO()
    psn_store_api = PSNStoreAPI()

    """
    Celery Task - Sync PSN library with PSN Store.
    """
    def sync_library_with_store(self, library_id):
        """
        Syncs the local PSN library with the PSN store.

        Requests the full PSN Store JSON, which contains a list of all PS4 games in
        the PSN Store. This JSON is then used to update the local PSN library.

        Args:
            library_id: The ID of the local library to update.
        """
        # Get the PSN Library from the DB
        psn_library = self.psn_library_dao.get_library(library_id)

        if psn_library != None:
            try:
                # Get the PSN Store JSON
                psn_lib_json = self.psn_store_api.request_psn_lib_json(psn_library.library_url)

                # Update the PSN library with the PSN Store JSON
                self.update_psn_library(psn_library, psn_lib_json)

            except Exception as e:
                traceback.print_exc()

    def update_psn_library(self, library, library_json):
        """
        Update the PSN Library using the PSN Store JSON.

        The PSN Store JSON contains a list of all games. Each game entry contains a url
        to the full details for that game. The details at this url are used to add new
        games to the PSN library, or update games already contained within it.

        Args:
            library: The PSN library object from the DB.
            library_json: The full library JSON returned by the PSN Store API.
        """
        for simple_game_json in library_json[PSN_JSON_ELEM_EACH_GAME]:
            try:
                if self.game_is_valid(simple_game_json):

                    print(simple_game_json[PSN_JSON_ELEM_GAME_NAME])
                    detailed_game_json_url = simple_game_json[PSN_JSON_ELEM_GAME_URL]
                    detailed_game_json = self.psn_store_api.request_psn_game_json(detailed_game_json_url)
                    game = self.psn_library_dao.get_game(library, detailed_game_json[PSN_JSON_ELEM_GAME_ID])

                    if game == None:
                        self.add_game(library, detailed_game_json, detailed_game_json_url)
                    else:
                        self.update_game(library, detailed_game_json, game)

            except Exception as e:
                # The PSN store has some inconsistencies. When I've seen KeyErrors for the PSN_JSON_ELEM_GAME_PRICE_BLOCK element
                # its been because a game was still listed in the store for pre-order after it already came out. So ignore these.
                if PSN_JSON_ELEM_GAME_PRICE_BLOCK not in str(e):
                    print("Exception processing game: ", simple_game_json[PSN_JSON_ELEM_GAME_NAME])
                    traceback.print_exc()

        # Update Library statistics, such as std dev, for rating weighting
        self.psn_library_dao.update_library_statistics(library)

    @transaction.atomic
    def add_game(self, library, detailed_game_json, detailed_game_json_url):
        """
        Add a new game to the PSN Library.

        First add a skeleton record with basic (unchanging) game info to the DB. Then add game
        content records for this game (these are also unchanging). Finally, send the skeleton
        record to the update method to add all of the variable game data e.g. price, rating etc.

        This operation is an atomic transaction.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            detailed_game_json_url: The url contained in the library JSON
                                    that returns the detailed game json.
        """
        game = self.add_skeleton_game_record(library, detailed_game_json, detailed_game_json_url)
        self.set_psn_game_content(game, detailed_game_json)
        self.update_game(library, detailed_game_json, game)

    def add_skeleton_game_record(self, library, detailed_game_json, detailed_game_json_url):
        """
        Add a skeleton record with basic (unchanging) game info to the DB.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            detailed_game_json_url: The url contained in the library JSON
                                    that returns the detailed game json.
        """
        url = detailed_game_json_url
        id = detailed_game_json[PSN_JSON_ELEM_GAME_ID]
        name = detailed_game_json[PSN_JSON_ELEM_GAME_NAME]
        thumb = self.get_game_thumbnail(detailed_game_json[PSN_JSON_ELEM_GAME_IMAGES])
        thumb_datastore = self.upload_thumb_to_cloudinary(thumb)
        age = detailed_game_json[PSN_JSON_ELEM_GAME_AGERATING]
        return self.psn_library_dao.add_skeleton_game_record(id, name, url, thumb, thumb_datastore, age, library)

    def set_psn_game_content(self, game, detailed_game_json):
        """
        Set the content descriptors for the game.

        Content descriptors are not mandatory for a game. Some examples are 'Online', 'Drugs', 'Violence' etc.

        Args:
            game: The game in the PSN library to add content descriptors for.
            detailed_game_json: The full detailed game info JSON.
        """
        # Check if there is a content descriptors json block
        if (PSN_JSON_ELEM_EACH_GAME_CONTENT in detailed_game_json) and (detailed_game_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]):
            for eachContentDescr in detailed_game_json[PSN_JSON_ELEM_EACH_GAME_CONTENT]:
                content_descriptor = self.psn_library_dao.get_or_create_content_descriptor(eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_NAME], eachContentDescr[PSN_JSON_ELEM_GAME_CONTENT_DESCR])
                self.psn_library_dao.get_or_create_game_content(game, content_descriptor)

    @transaction.atomic
    def update_game(self, library, detailed_game_json, game):
        """
        Update a game's details in the PSN library.

        Variable data, such as price, ratings and the resulting value, is updated with
        data from the PSN store.

        This operation is an atomic transaction.

        Args:
            library: The PSN library object from the DB.
            detailed_game_json: The full detailed game info JSON.
            game: The game in the PSN libray to update.
        """
        # Set the price
        self.set_game_price(game, detailed_game_json)
        # Set the ratings (both new ratings in psn and updated weighting)
        self.set_game_ratings(library, game, detailed_game_json[PSN_JSON_ELEM_GAME_RATING_BLOCK])
        # Set the game value
        self.set_game_value(library, game)
        # Update the game object in the DB
        self.psn_library_dao.update_game(game)

    def set_game_price(self, game, detailed_game_json):
        """
        Set the price details for a game in the PSN library

        Args:
            game: The game to set price details for.
            detailed_game_json: The full detailed game info JSON.
        """
        game.price = detailed_game_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK][PSN_JSON_ELEM_GAME_PRICE]
        discount_dtls_tuple = self.get_game_discounts(detailed_game_json[PSN_JSON_ELEM_GAME_PRICE_BLOCK])
        game.base_discount = discount_dtls_tuple.rates.base
        game.plus_discount = discount_dtls_tuple.rates.plus
        game.base_price = discount_dtls_tuple.prices.base
        game.plus_price = discount_dtls_tuple.prices.plus

    def set_game_ratings(self, library, game, game_rating_block_json):
        """
        Set the ratings details for a game in the PSN library.

        These ratings include both the ratings info from the PSN store, and also
        a weighted rating based on global statistics for the PSN library.

        Args:
            library: The PSN library object from the DB.
            game: The game to set ratings details for.
            game_rating_block_json: The block of JSON containing the ratings data.
        """
        game.rating = game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] if game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_VALUE] else PSN_MODEL_RATING_DEFAULT_VALUE
        game.rating_count = game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] if game_rating_block_json[PSN_JSON_ELEM_GAME_RATING_COUNT] else PSN_MODEL_RATING_DEFAULT_COUNT
        game.weighted_rating = self.determine_weighted_game_rating(library, game)

    def set_game_value(self, library, game):
        """
        Calculate and set both the PS+ and non-PS+ value for this game.

        Args:
            library: The PSN library object from the DB.
            game: The game to set value details for.
        """
        game.base_value_score = self.calculate_game_value(library, game, False)
        game.plus_value_score = self.calculate_game_value(library, game, True)

    def get_game_discounts(self, game_price_block_json):
        """
        Extract the details of any discounts from the detailed game JSON.

        Checks for both regular discounts and also PS+ discounts.

        Args:
            game_price_block_json: The block of JSON containing the discounts data.
        Returns:
            namedtuple: A tuple containing the following two tuples:
                            1) A tuple containing the discount rate for both PS+ and non-PS+.
                            2) A tuple containing the discounted price for both PS+ and non-PS+.
        """
        psn_discount_dtls = collections.namedtuple('psn_discount_dtls', ['rates', 'prices'])
        psn_discount_rates = collections.namedtuple('psn_discount_rates', ['base', 'plus'])
        psn_discount_prices = collections.namedtuple('psn_discount_prices', ['base', 'plus'])
        base_discount = 0
        plus_discount = 0

        # Use the standard game price as default, and only overwrite if there are discounts.
        base_price = game_price_block_json[PSN_JSON_ELEM_GAME_PRICE]
        plus_price = game_price_block_json[PSN_JSON_ELEM_GAME_PRICE]

        # Check if there is a discount json block
        if (PSN_JSON_ELEM_GAME_REWARDS in game_price_block_json) and (game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS]):

            # Check for discounts that apply to PS+ and non-PS+ members
            if PSN_JSON_ELEM_GAME_BASE_DISCOUNT in game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
                base_discount = game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BASE_DISCOUNT]
                base_price = game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BASE_PRICE]
                plus_discount = base_discount
                plus_price = base_price

            # Now check for discounts that apply only to PS Plus members
            if PSN_JSON_ELEM_GAME_BONUS_DISCOUNT in game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0]:
                plus_discount = game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BONUS_DISCOUNT]
                plus_price = game_price_block_json[PSN_JSON_ELEM_GAME_REWARDS][0][PSN_JSON_ELEM_GAME_BONUS_PRICE]

        discount_rates_tuple = psn_discount_rates(base=base_discount, plus=plus_discount)
        discount_prices_tuple = psn_discount_prices(base=base_price, plus=plus_price)
        discount_dtls_tuple = psn_discount_dtls(rates=discount_rates_tuple, prices=discount_prices_tuple)
        return discount_dtls_tuple

    def get_game_thumbnail(self, image_list):
        """
        Get a thumbnail to use for the game in the PSN library.

        Args:
            image_list: The list of available thumbnails from the PSN store.
        Returns:
            string: Return a string containing the url to the small thumbnail in the PSN Store.
        """
        game_thumb = None
        for eachGameImg in image_list:
            if eachGameImg[PSN_JSON_ELEM_GAME_IMGTYPE] == PSN_JSON_ELEM_GAME_IMGTYPE_THUMB_SML:
                game_thumb = eachGameImg[PSN_JSON_ELEM_GAME_URL]
                break
        return game_thumb

    def upload_thumb_to_cloudinary(self, thumbnail_url):
        """
        Upload a thumbnail to the cloudinary datastore.

        Take the url for a thumbnail in the PSN store and store the image in cloudinary.
        Thumbnails will then be accessed from cloudinary when displaying the PSN libray,
        rather than hitting the PSN store for them.

        Args:
            thumbnail_url: The url of the thumbnail to upload to cloudinary.
        Returns:
            string: Return the url of the image now stored in cloudinary.
        """
        upload_result = cloudinary.uploader.upload(thumbnail_url)
        return upload_result['url']

    def game_is_valid(self, game_json):
        """
        Check if a game is valid for addition to the PSN library.

        Bundles, pre-releases etc are invalid. Different editions of
        a game, however, are valid.

        Args:
            game_json: The simple JSON for the game from the PSN Store.
        Returns:
            boolean: Return true if the game is valid, else false.
        """
        game_valid = True
        # We're just looking for base games i.e. ignore bundles etc.
        if PSN_JSON_ELEM_SUB_GAME in game_json:
            game_valid = False
        # Check to make sure the game is released - otherwise we can get games without prices etc.
        elif self.game_is_released(game_json) == False:
            game_valid = False

        return game_valid

    def game_is_released(self, game_json):
        """
        Check if the game is released.

        Args:
            game_json: The simple JSON for the game from the PSN Store.
        Returns:
            boolean: Return true if the game is released, else false.
        """
        is_released = False
        release_date = datetime.strptime(game_json[PSN_JSON_ELEM_RELEASE_DATE], '%Y-%m-%dT%H:%M:%SZ')
        if release_date < datetime.now():
            is_released = True
        return is_released

    """
    PSN Library Statistics
    """
    DEFAULT_GAME_PRICE = 1
    DEFAULT_GAME_WEIGHTED_RATING = 1
    RATING_COUNT_WEIGHTING = 125

    def determine_weighted_game_rating(self, library, game):
        """
        Determine the weighted rating of a game.

        The rating, the count of ratings made and the rating's deviation from the mean are factored in.

        Args:
            library: The PSN library object from the DB.
            game: The game to determine the weighted rating for.
        Returns:
            float: The weighted rating for this game.
        """
        # Determine if this game is above or below the mean rating. Necessary for applying different weighting algorithm.
        aboveMean = self.rating_above_mean(library, game)

        # Determine how much weight to put on the rating as a result of the number of ratings.
        ratingCountVal = (float(game.rating_count)/self.RATING_COUNT_WEIGHTING)

        # Determine weighting to apply based on rating deviation from the mean.
        ratingConstant = 1 if aboveMean else -1
        ratingVal = round((float(game.rating)) * (ratingConstant+((float(game.rating) - library.library_rating_mean)/library.library_rating_stdev)), 2)

        # Apply different weights depending if the game rating is above or below mean.
        finalVal = 0
        if aboveMean:
            finalVal = (ratingVal+ratingCountVal)
        else:
            finalVal = (ratingVal-ratingCountVal)

        # Account for a weighted rating of zero
        return self.DEFAULT_GAME_WEIGHTED_RATING if finalVal == 0.0 else finalVal

    def calculate_game_value(self, library, game, is_plus):
        """
        Calculate the value for a game.

        Calculate the value based on the weighted rating, the price and the discount.

        Args:
            library: The PSN library object from the DB.
            game: The game to determine the value for.
            is_plus: True if we are calculating the PS+ value, else false for non-PS+.
        """
        game_price = 0.0
        game_rating = 0.0
        discount_weight = 0.0

        if is_plus == True:
            game_price = game.plus_price
        else:
            game_price = game.base_price

        # Use DEFAULT_GAME_PRICE for anything less than 1 (stops division by zero errors).
        game_price = round(game_price if game_price > 0.0 else self.DEFAULT_GAME_PRICE)

        # Determine the weight to apply to the discount.
        if is_plus == True:
            discount_weight = 1+(game.plus_discount/100)
        else:
            discount_weight = 1+(game.base_discount/100)

        # Apply the discount weight to the weighted rating.
        if self.rating_above_mean(library, game):
            game_rating = ((game.weighted_rating)*discount_weight)*100
        else:
            game_rating = ((game.weighted_rating)/discount_weight)*100

        return round(1/(game_price/game_rating)*100)

    def rating_above_mean(self, library, game):
        """
        Determine if a game's rating is above or below the mean rating for the library.

        Args:
            library: The PSN library object from the DB.
            game: The game to determine if it is above or below the mean.
        Returns:
            boolean: True if above the mean, else false.
        """
        return (float(game.rating) - library.library_rating_mean) > 0

    """
    Celery Task - Update Thumbnails
    """
    def upload_thumbnails_to_cloudinary(self, library_id):
        """
        View used for updating the stored game thumbnails.

        Each game in the library is iterated over and the game thumbnail is retrieved using the thumbnail
        URL stored in the DB. The image at this URL is then stored in the library storage. This update is
        performed asynchronously. Update can only be triggered through this view by an admin user.

        Args:
            request: The HTTP request
            library_id: The ID of the local libray whose games we want to update.
        Returns:
            The HTTP response.
        """
        # Get the Library Object from the DB
        library_obj = self.psn_library_dao.get_library(library_id)

        # Get all games from the DB
        all_games = self.psn_library_dao.get_all_games()

        for each_game_obj in all_games:
            print(each_game_obj.game_name)
            each_game_obj.image_datastore_url = self.upload_thumb_to_cloudinary(each_game_obj.image_url)
            super().update_game_obj(each_game_obj)

    """
    Celery Task - Update Weighted Ratings
    """
    def update_weighted_ratings(self, library_id):
        """
        View used for updating the weighted rating for each game in the library.

        Each game in the library is iterated over and the weighted rating of the game, and its
        corresponding value are calculated and updated in the DB. This allows for changes in the
        value formula to be applied quickly. This update is performed asynchronously. Update can
        only be triggered through this view by an admin user.

        Args:
            request: The HTTP request
            library_id: The ID of the local libray whose games we want to update.
        Returns:
            The HTTP response.
        """
        # Get the Library Object from the DB
        library = self.psn_library_dao.get_library(library_id)

        # Get all games from the DB
        all_games = self.psn_library_dao.get_all_games()

        for each_game in all_games:
            print(each_game.game_name)
            each_game.weighted_rating = self.determine_weighted_game_rating(library, each_game)
            self.set_game_value(library, each_game)
            self.psn_library_dao.update_game(each_game)
