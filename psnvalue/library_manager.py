#from .psn_library import PSNLibrary
from .tasks import user_update_psn_library, user_update_weighted_rating, user_update_game_thumbnails

def update_library(p_library_id):
    print("Gonna update the lib: ", p_library_id)
    user_update_psn_library.delay(p_library_id)

def update_weighted_rating(p_library_id):
    print("Gonna update the rating weightings in lib: ", p_library_id)
    user_update_weighted_rating.delay(p_library_id)

def update_psn_game_thumbnails(p_library_id):
    print("Gonna update the image thumbnails in lib: ", p_library_id)
    user_update_game_thumbnails.delay(p_library_id)
