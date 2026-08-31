#include <gtest/gtest.h>

#include "ReaderButtonGestureDetector.h"
#include "ReaderButtonProfile.h"

TEST(ReaderButtonProfile, FactoryDefaultsPreserveSingleClickLayout) {
  EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Back, ReaderButtonGesture::Single),
            ReaderAction::ReaderBack);
  EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Confirm, ReaderButtonGesture::Single),
            ReaderAction::OpenReaderMenu);
  EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Left, ReaderButtonGesture::Single),
            ReaderAction::PreviousPage);
  EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(ReaderPhysicalButton::Right, ReaderButtonGesture::Single),
            ReaderAction::NextPage);

  for (size_t button = 0; button < READER_PHYSICAL_BUTTON_COUNT; ++button) {
    EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(static_cast<ReaderPhysicalButton>(button), ReaderButtonGesture::Double),
              ReaderAction::None);
    EXPECT_EQ(FACTORY_READER_BUTTON_PROFILE.get(static_cast<ReaderPhysicalButton>(button), ReaderButtonGesture::Hold),
              ReaderAction::None);
  }
}

TEST(ReaderButtonGestureDetector, SingleFiresOnlyAfterDoubleClickWindow) {
  ReaderButtonGestureDetector detector(400, 600);
  detector.onPressed(ReaderPhysicalButton::Left, 1000);
  EXPECT_FALSE(detector.onReleased(ReaderPhysicalButton::Left, 1060).has_value());
  EXPECT_FALSE(detector.poll(1460).has_value());

  const auto event = detector.poll(1461);
  ASSERT_TRUE(event.has_value());
  EXPECT_EQ(event->button, ReaderPhysicalButton::Left);
  EXPECT_EQ(event->gesture, ReaderButtonGesture::Single);
}

TEST(ReaderButtonGestureDetector, DoubleSuppressesPendingSingle) {
  ReaderButtonGestureDetector detector(400, 600);
  detector.onPressed(ReaderPhysicalButton::Right, 1000);
  EXPECT_FALSE(detector.onReleased(ReaderPhysicalButton::Right, 1040).has_value());
  detector.onPressed(ReaderPhysicalButton::Right, 1200);

  const auto event = detector.onReleased(ReaderPhysicalButton::Right, 1240);
  ASSERT_TRUE(event.has_value());
  EXPECT_EQ(event->button, ReaderPhysicalButton::Right);
  EXPECT_EQ(event->gesture, ReaderButtonGesture::Double);
  EXPECT_FALSE(detector.poll(1700).has_value());
}

TEST(ReaderButtonGestureDetector, HoldFiresOnceAndSuppressesRelease) {
  ReaderButtonGestureDetector detector(400, 600);
  detector.onPressed(ReaderPhysicalButton::Confirm, 1000);
  EXPECT_FALSE(detector.onHeld(ReaderPhysicalButton::Confirm, 1599).has_value());

  const auto hold = detector.onHeld(ReaderPhysicalButton::Confirm, 1600);
  ASSERT_TRUE(hold.has_value());
  EXPECT_EQ(hold->gesture, ReaderButtonGesture::Hold);
  EXPECT_FALSE(detector.onHeld(ReaderPhysicalButton::Confirm, 1700).has_value());
  EXPECT_FALSE(detector.onReleased(ReaderPhysicalButton::Confirm, 1750).has_value());
  EXPECT_FALSE(detector.poll(2200).has_value());
}

TEST(ReaderButtonGestureDetector, PhysicalButtonsHaveIndependentPendingSingles) {
  ReaderButtonGestureDetector detector(400, 600);
  detector.onPressed(ReaderPhysicalButton::Left, 1000);
  detector.onReleased(ReaderPhysicalButton::Left, 1020);
  detector.onPressed(ReaderPhysicalButton::Right, 1100);
  detector.onReleased(ReaderPhysicalButton::Right, 1120);

  auto first = detector.poll(1421);
  ASSERT_TRUE(first.has_value());
  EXPECT_EQ(first->button, ReaderPhysicalButton::Left);

  auto second = detector.poll(1521);
  ASSERT_TRUE(second.has_value());
  EXPECT_EQ(second->button, ReaderPhysicalButton::Right);
}

TEST(ReaderAction, GroupsKeepMenusStepsAndTogglesDistinct) {
  EXPECT_EQ(readerActionGroup(ReaderAction::OpenFontMenu), ReaderActionGroup::Menu);
  EXPECT_EQ(readerActionGroup(ReaderAction::FontNext), ReaderActionGroup::Immediate);
  EXPECT_EQ(readerActionGroup(ReaderAction::ToggleHyphenation), ReaderActionGroup::Toggle);
  EXPECT_EQ(readerActionGroup(ReaderAction::None), ReaderActionGroup::None);
}
