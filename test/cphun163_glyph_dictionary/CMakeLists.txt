add_executable(CPHUN163GlyphDictionaryTest CPHUN163GlyphDictionaryTest.cpp)
target_include_directories(CPHUN163GlyphDictionaryTest PRIVATE
  ${REPO_ROOT}/lib/GfxRenderer
  ${REPO_ROOT}/src/util
)
target_link_libraries(CPHUN163GlyphDictionaryTest PRIVATE crosspoint_test_common GTest::gtest_main)
gtest_discover_tests(CPHUN163GlyphDictionaryTest)
