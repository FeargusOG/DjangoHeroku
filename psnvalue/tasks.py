from celery.decorators import task
from celery.utils.log import get_task_logger

from .psn_library import PSNLibrary

logger = get_task_logger(__name__)

@task(name="user_update_psn_library")
def user_update_psn_library(p_library_id):
    logger.info("About to update the PSN library")
    psn_library = PSNLibrary()
    psn_library.update_psn_lib(p_library_id)

@task(name="user_update_weighted_rating")
def user_update_weighted_rating(p_library_id):
    logger.info("About to apply weighting to the PSN library")
    psn_library = PSNLibrary()
    psn_library.update_psn_weighted_ratings(p_library_id)

@task(name="user_update_game_thumbnails")
def user_update_game_thumbnails(p_library_id):
    logger.info("About to update the thumbnails in the PSN library")
    psn_library = PSNLibrary()
    psn_library.update_psn_game_thumbnails(p_library_id)
