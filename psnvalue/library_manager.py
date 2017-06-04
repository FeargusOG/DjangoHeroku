from .psn_library import PSNLibrary

def update_library(p_library_id):
    print("Gonna update the lib: ", p_library_id)
    #For the moment, only psn is supported.
    psn_library_manager = PSNLibrary()
    psn_library_manager.update_psn_lib(p_library_id)






