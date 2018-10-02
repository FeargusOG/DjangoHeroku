from celery.decorators import task
from celery.utils.log import get_task_logger

from .psn_library import PSNLibrary

logger = get_task_logger(__name__)

@task(name="task_sync_psn_library_with_psn_store")
def task_sync_psn_library_with_psn_store(p_library_id):
    """
    Celery task for syncing the local PSN library with the PSN store.

    Can be scheduled to run or called directly.
    """
    psn_library = PSNLibrary()
    logger.info("Started syncing the PSN library with the PSN store.")
    psn_library.sync_library_with_store(p_library_id)
    logger.info("Finished syncing the PSN library with the PSN store.")

@task(name="task_update_psn_weighted_ratings")
def task_update_psn_weighted_ratings(p_library_id):
    """
    Celery task for updating the weighted rating for each game in the library.

    Can be scheduled to run or called directly.
    """
    psn_library = PSNLibrary()
    logger.info("Started applying weighting to the PSN library.")
    psn_library.update_weighted_ratings(p_library_id)
    logger.info("Finished applying weighting to the PSN library.")

@task(name="task_update_psn_game_thumbnails")
def task_update_psn_game_thumbnails(p_library_id):
    """
    Celery task for updating the stored game thumbnails.

    Can be scheduled to run or called directly.
    """
    psn_library = PSNLibrary()
    logger.info("Started update of the thumbnails in the PSN library.")
    psn_library.upload_thumbnails_to_cloudinary(p_library_id)
    logger.info("Finished update of the thumbnails in the PSN library.")
