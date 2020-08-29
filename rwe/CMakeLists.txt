file(GLOB source_files *.cpp *.h)
add_library (rwe ${source_files})

set_target_properties(rwe PROPERTIES
            CXX_STANDARD 17
            CXX_EXTENSIONS OFF
            )