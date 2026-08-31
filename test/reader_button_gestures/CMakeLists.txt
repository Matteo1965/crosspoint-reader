add_executable(ReaderButtonGestureTest
  ReaderButtonGestureTest.cpp
  ${REPO_ROOT}/src/ReaderButtonGestureDetector.cpp
)

target_include_directories(ReaderButtonGestureTest PRIVATE
  ${REPO_ROOT}/src
)

target_link_libraries(ReaderButtonGestureTest PRIVATE
  crosspoint_test_common
  GTest::gtest_main
)

gtest_discover_tests(ReaderButtonGestureTest)
