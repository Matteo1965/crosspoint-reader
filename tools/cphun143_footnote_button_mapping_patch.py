from pathlib import Path

p = Path("src/activities/reader/FootnotePopupActivity.cpp")
s = p.read_text(encoding="utf-8")

old = '''  if (mappedInput.wasReleased(MappedInputManager::Button::Up)) {
    if (canNavigateSiblings_) {
      setResult(FootnotePopupNavResult{-1});
      finish();
      return;
    }
    if (firstLine_ > 0) {
      --firstLine_;
      requestUpdate();
    }
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (canNavigateSiblings_) {
      setResult(FootnotePopupNavResult{1});
      finish();
      return;
    }
    if (firstLine_ + 1 < static_cast<int>(lines_.size())) {
      ++firstLine_;
      requestUpdate();
    }
    return;
  }
'''

new = '''  // Side Up/Down buttons always scroll the current footnote text.
  if (mappedInput.wasReleased(MappedInputManager::Button::Up)) {
    if (firstLine_ > 0) {
      --firstLine_;
      requestUpdate();
    }
    return;
  }
  if (mappedInput.wasReleased(MappedInputManager::Button::Down)) {
    if (firstLine_ + 1 < static_cast<int>(lines_.size())) {
      ++firstLine_;
      requestUpdate();
    }
    return;
  }

  // Front bottom buttons 3/4 are the Left/Right roles. Their labels are
  // already orientation-aware via mapLabels(), so mirror the semantic action
  // when that axis is swapped as well.
  if (canNavigateSiblings_ &&
      mappedInput.wasReleased(MappedInputManager::Button::Left)) {
    setResult(FootnotePopupNavResult{mappedInput.isNavDirectionSwapped() ? 1 : -1});
    finish();
    return;
  }
  if (canNavigateSiblings_ &&
      mappedInput.wasReleased(MappedInputManager::Button::Right)) {
    setResult(FootnotePopupNavResult{mappedInput.isNavDirectionSwapped() ? -1 : 1});
    finish();
    return;
  }
'''

if s.count(old) != 1:
    raise SystemExit(f"CPHUN-143 popup navigation anchor matches={s.count(old)}")

p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("CPHUN-143 applied: front buttons 3/4 navigate footnotes, side Up/Down scroll text")
