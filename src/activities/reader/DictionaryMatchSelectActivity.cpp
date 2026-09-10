#include "DictionaryMatchSelectActivity.h"

#include "activities/ActivityResult.h"
#include "components/UITheme.h"

namespace fui = freeink::ui;

DictionaryMatchSelectActivity::DictionaryMatchSelectActivity(GfxRenderer& renderer, MappedInputManager& mappedInput,
                                                             std::vector<std::string> headwords)
    : UiListActivity("DictionaryMatchSelect", renderer, mappedInput), headwords(std::move(headwords)) {
  rows.resize(this->headwords.size());
  for (size_t i = 0; i < this->headwords.size(); ++i) {
    rows[i].label = this->headwords[i].c_str();
    rows[i].actionValue = static_cast<int16_t>(i);
  }
}

void DictionaryMatchSelectActivity::buildScreen(UiScreen& screen) {
  const auto& metrics = UITheme::getInstance().getMetrics();
  const Rect safe = UITheme::getInstance().getScreenSafeArea(renderer, true, false);
  screen.setContentMargin(fui::Insets{static_cast<int16_t>(safe.y + metrics.topPadding + metrics.headerHeight),
                                      static_cast<int16_t>(renderer.getScreenWidth() - (safe.x + safe.width)),
                                      static_cast<int16_t>(renderer.getScreenHeight() - (safe.y + safe.height)),
                                      static_cast<int16_t>(safe.x)});
  screen.spacer(static_cast<int16_t>(metrics.verticalSpacing));
  if (rows.empty()) return;
  fui::ListProps props;
  props.count = static_cast<uint16_t>(rows.size());
  props.items = rows.data();
  props.action = ACTION_ROW;
  props.inputMask = fui::InputTouch;
  syncListViewport(screen, props);
  screen.list(props);
}

void DictionaryMatchSelectActivity::activateIndex(const int index) {
  if (index < 0 || index >= static_cast<int>(headwords.size())) return;
  app.clearTapFlash();
  setResult(DictionaryHeadwordResult{headwords[index]});
  finish();
}
