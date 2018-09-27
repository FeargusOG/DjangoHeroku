from celery.decorators import task
from celery.utils.log import get_task_logger

from .psn_library import PSNLibrary

logger = get_task_logger(__name__)

@task(name="user_update_psn_library")
def user_update_psn_library(p_library_id):
    psn_library = PSNLibrary()
    logger.info("Started update of the PSN library")
    psn_library.update_psn_lib(p_library_id)
    logger.info("Finished update of the PSN library")

@task(name="user_update_weighted_rating")
def user_update_weighted_rating(p_library_id):
    psn_library = PSNLibrary()
    logger.info("Started applying weighting to the PSN library")
    psn_library.update_psn_weighted_ratings(p_library_id)
    logger.info("Finished applying weighting to the PSN library")

@task(name="user_update_game_thumbnails")
def user_update_game_thumbnails(p_library_id):
    psn_library = PSNLibrary()
    logger.info("Started update of the thumbnails in the PSN library")
    psn_library.upload_thumbnails_to_cloudinary(p_library_id)
    logger.info("Finished update of the thumbnails in the PSN library")
