from pathlib import Path


def replace_once(path: str, old: str, new: str) -> None:
    p = Path(path)
    text = p.read_text(encoding="utf-8")
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"Expected one match in {path}, found {count}")
    p.write_text(text.replace(old, new, 1), encoding="utf-8")


replace_once("src/CPHUNBuildId.h", 'CPHUN-260910-89', 'CPHUN-260910-90')
replace_once("lib/Epub/Epub/Section.cpp", "constexpr uint8_t SECTION_FILE_VERSION = 55;",
             "constexpr uint8_t SECTION_FILE_VERSION = 56;")

old = r'''// CPHUN-89: fixed-width leading marker spacing. Besides the existing dialogue
// dash, protect one source space after common paragraph-leading list markers:
// 1. / 12. / 1) / 12) / a) / bullet.
bool isAsciiDigitsToken(const std::string& token) {
  if (token.empty()) return false;
  for (const unsigned char c : token)
    if (c < '0' || c > '9') return false;
  return true;
}

bool isSingleAsciiAlphaToken(const std::string& token) {
  return token.size() == 1 &&
         ((token[0] >= 'a' && token[0] <= 'z') || (token[0] >= 'A' && token[0] <= 'Z'));
}

template <typename WordContainer>
bool isFixedLeadingMarkerBoundary(const WordContainer& tokens, const size_t boundary) {
  if (boundary == 1 && !tokens.empty()) {
    if (isStandaloneDialogueDash(tokens[0])) return true;
    const uint32_t cp = firstCodepoint(tokens[0]);
    if (cp == 0x2022 && cp == lastCodepoint(tokens[0])) return true;
  }
  if (boundary == 2 && tokens.size() >= 2) {
    const std::string& leader = tokens[0];
    const std::string& suffix = tokens[1];
    if ((suffix == "." && isAsciiDigitsToken(leader)) ||
        (suffix == ")" && (isAsciiDigitsToken(leader) || isSingleAsciiAlphaToken(leader)))) {
      return true;
    }
  }
  return false;
}
'''

new = r'''// CPHUN-90: fixed-width leading marker spacing. Protect exactly one source
// space after paragraph-leading list markers, regardless of whether the EPUB
// tokenizer keeps the marker together ("12.", "A.)") or splits punctuation
// into separate tokens ("12" + ".", "A" + ".)" or "A" + "." + ")").
bool isAsciiDigitsToken(const std::string& token) {
  if (token.empty()) return false;
  for (const unsigned char c : token)
    if (c < '0' || c > '9') return false;
  return true;
}

bool isSingleAsciiAlphaToken(const std::string& token) {
  return token.size() == 1 &&
         ((token[0] >= 'a' && token[0] <= 'z') || (token[0] >= 'A' && token[0] <= 'Z'));
}

bool isCompleteAsciiListMarker(const std::string& token) {
  if (token.size() < 2) return false;

  size_t leaderEnd = 0;
  bool numeric = false;
  if (token[0] >= '0' && token[0] <= '9') {
    numeric = true;
    while (leaderEnd < token.size() && token[leaderEnd] >= '0' && token[leaderEnd] <= '9') ++leaderEnd;
  } else if ((token[0] >= 'a' && token[0] <= 'z') || (token[0] >= 'A' && token[0] <= 'Z')) {
    leaderEnd = 1;
  } else {
    return false;
  }

  const std::string suffix = token.substr(leaderEnd);
  if (numeric) return suffix == "." || suffix == ")" || suffix == ".)";
  return suffix == ")" || suffix == ".)";
}

template <typename WordContainer>
bool isFixedLeadingMarkerBoundary(const WordContainer& tokens, const size_t boundary) {
  if (boundary == 1 && !tokens.empty()) {
    if (isStandaloneDialogueDash(tokens[0])) return true;
    const uint32_t cp = firstCodepoint(tokens[0]);
    if (cp == 0x2022 && cp == lastCodepoint(tokens[0])) return true;
    if (isCompleteAsciiListMarker(tokens[0])) return true;
  }

  if (boundary == 2 && tokens.size() >= 2) {
    const std::string& leader = tokens[0];
    const std::string& suffix = tokens[1];
    if (isAsciiDigitsToken(leader) && (suffix == "." || suffix == ")" || suffix == ".)")) return true;
    if (isSingleAsciiAlphaToken(leader) && (suffix == ")" || suffix == ".)")) return true;
  }

  if (boundary == 3 && tokens.size() >= 3 && tokens[1] == "." && tokens[2] == ")") {
    return isAsciiDigitsToken(tokens[0]) || isSingleAsciiAlphaToken(tokens[0]);
  }
  return false;
}
'''

replace_once("lib/Epub/Epub/ParsedText.cpp", old, new)
