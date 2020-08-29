cmake_policy(SET CMP0020 NEW)


file(GLOB source_files *.cpp *.h)

add_executable (3do2scm
    ${source_files}
    )

set_target_properties(3do2scm PROPERTIES
            CXX_STANDARD 17
            CXX_EXTENSIONS OFF
            )

target_link_libraries (3do2scm LINK_PUBLIC 
    rwe
    )
