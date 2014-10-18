project (something)

cmake_minimum_required (VERSION 2.8)

find_package(OpenGL REQUIRED)
find_package(GLUT REQUIRED)
include_directories( ${OPENGL_INCLUDE_DIRS}  ${GLUT_INCLUDE_DIRS} )


file(GLOB SRC_FILES
    "*.cpp"
)

# copy shaders to binary folder
#file( COPY "${PROJECT_SOURCE_DIR}/glsl/" DESTINATION "${PROJECT_BINARY_DIR}/glsl/")

add_definitions(-std=c++11)
add_executable (Main ${SRC_FILES})
target_link_libraries (Main ${OPENGL_LIBRARIES} ${GLUT_LIBRARY})