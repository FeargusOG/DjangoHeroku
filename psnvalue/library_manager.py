#from .psn_library import PSNLibrary
from .tasks import user_update_psn_library

def update_library(p_library_id):
    print("Gonna update the lib: ", p_library_id)
    # TODO For the moment, only PSN is supported
    user_update_psn_library.delay(p_library_id)
