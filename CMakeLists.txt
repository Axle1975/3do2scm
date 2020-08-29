cmake_minimum_required (VERSION 3.4)
project (3do2scm)

# add the required Qt source includes to the cmake path
include_directories(
    ${CMAKE_SOURCE_DIR}
	${CMAKE_SOURCE_DIR}/utfcpp/source
    )

add_subdirectory (rwe)
add_subdirectory (app)
