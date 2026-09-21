from pathlib import Path

# --- ReleaseJsonParser: detect cphun-build-<N>.json marker asset ----------------
h = Path("lib/JsonParser/ReleaseJsonParser.h")
s = h.read_text(encoding="utf-8")
s = s.replace(
'''  size_t getFirmwareSize() const;

 private:
''',
'''  size_t getFirmwareSize() const;
  int getHungarianEditionBuild() const;

 private:
''', 1)
s = s.replace(
'''  size_t firmwareSize;
  bool tagFound;
  bool firmwareFound;
''',
'''  size_t firmwareSize;
  int hungarianEditionBuild;
  bool tagFound;
  bool firmwareFound;
''', 1)
h.write_text(s, encoding="utf-8")

p = Path("lib/JsonParser/ReleaseJsonParser.cpp")
s = p.read_text(encoding="utf-8")
s = s.replace(
'''  firmwareSize = 0;
  tagFound = false;
''',
'''  firmwareSize = 0;
  hungarianEditionBuild = 0;
  tagFound = false;
''', 1)
s = s.replace(
'''size_t ReleaseJsonParser::getFirmwareSize() const { return firmwareSize; }

void ReleaseJsonParser::commitAsset() {
''',
'''size_t ReleaseJsonParser::getFirmwareSize() const { return firmwareSize; }
int ReleaseJsonParser::getHungarianEditionBuild() const { return hungarianEditionBuild; }

void ReleaseJsonParser::commitAsset() {
''', 1)
old = '''void ReleaseJsonParser::commitAsset() {
  if (strcmp(currentAssetName, firmwareAssetName) == 0) {
    memcpy(firmwareUrl, currentAssetUrl, sizeof(firmwareUrl));
    firmwareSize = currentAssetSize;
    firmwareFound = true;
  }
'''
new = '''void ReleaseJsonParser::commitAsset() {
  constexpr char BUILD_PREFIX[] = "cphun-build-";
  constexpr char BUILD_SUFFIX[] = ".json";
  const size_t nameLen = strlen(currentAssetName);
  const size_t prefixLen = sizeof(BUILD_PREFIX) - 1;
  const size_t suffixLen = sizeof(BUILD_SUFFIX) - 1;

  if (nameLen > prefixLen + suffixLen &&
      strncmp(currentAssetName, BUILD_PREFIX, prefixLen) == 0 &&
      strcmp(currentAssetName + nameLen - suffixLen, BUILD_SUFFIX) == 0) {
    char* end = nullptr;
    const long parsed = strtol(currentAssetName + prefixLen, &end, 10);
    if (parsed > 0 && end == currentAssetName + nameLen - suffixLen) {
      hungarianEditionBuild = static_cast<int>(parsed);
    }
  }

  if (strcmp(currentAssetName, firmwareAssetName) == 0) {
    memcpy(firmwareUrl, currentAssetUrl, sizeof(firmwareUrl));
    firmwareSize = currentAssetSize;
    firmwareFound = true;
  }
'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-147 parser commitAsset anchor mismatch")
s = s.replace(old, new, 1)
p.write_text(s, encoding="utf-8")

# --- OTA updater: point Hungarian Edition to Matteo1965 releases and compare
#     Hungarian Edition build numbers. This EXP test build intentionally uses
#     baseline 135 to reproduce #135 -> public v146 discovery. -----------------
p = Path("src/network/OtaUpdater.cpp")
s = p.read_text(encoding="utf-8")
s = s.replace(
'''#include "FirmwareBoardTag.h"
#include "FirmwareFlasher.h"
''',
'''#include "CPHUNBuildId.h"
#include "FirmwareBoardTag.h"
#include "FirmwareFlasher.h"
''', 1)
s = s.replace(
'''constexpr char latestReleaseUrl[] = "https://api.github.com/repos/crosspoint-reader/crosspoint-reader/releases/latest";
''',
'''constexpr char latestReleaseUrl[] = "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest";
constexpr int CPHUN_OTA_TEST_BASELINE_BUILD = 135;

int parseCphunBuildId(const char* buildId) {
  if (buildId == nullptr) return 0;
  const char* p = buildId;
  int dashCount = 0;
  while (*p != '\0') {
    if (*p == '-') {
      ++dashCount;
      if (dashCount == 2) {
        ++p;
        return atoi(p);
      }
    }
    ++p;
  }
  return 0;
}
''', 1)

old = '''  latestVersion = releaseParser.getTagName();
  otaUrl = releaseParser.getFirmwareUrl();
  otaSize = releaseParser.getFirmwareSize();
  totalSize = otaSize;
  updateAvailable = true;

  LOG_DBG("OTA", "Found update: tag=%s size=%zu", latestVersion.c_str(), otaSize);
'''
new = '''  const int releaseBuild = releaseParser.getHungarianEditionBuild();
  if (releaseBuild <= 0) {
    LOG_ERR("OTA", "Hungarian Edition release marker missing");
    return JSON_PARSE_ERROR;
  }

  latestBuild = releaseBuild;
  latestVersion = "Hungarian Edition v." + std::to_string(releaseBuild);
  otaUrl = releaseParser.getFirmwareUrl();
  otaSize = releaseParser.getFirmwareSize();
  totalSize = otaSize;
  updateAvailable = true;

  LOG_DBG("OTA", "Found Hungarian Edition update: build=%d tag=%s size=%zu", releaseBuild,
          releaseParser.getTagName(), otaSize);
'''
if s.count(old) != 1:
    raise SystemExit("CPHUN-147 updater assignment anchor mismatch")
s = s.replace(old, new, 1)

start = s.index("bool OtaUpdater::isUpdateNewer() const {")
end = s.index("\nconst std::string& OtaUpdater::getLatestVersion()", start)
replacement = '''bool OtaUpdater::isUpdateNewer() const {
  if (!updateAvailable || latestBuild <= 0) {
    return false;
  }

  // CPHUN-147 EXP OTA validation:
  // force the comparison baseline to build 135 so this test image can
  // reproduce the user's real #135 -> public v146 update check.
  const int actualBuild = parseCphunBuildId(CPHUN_BUILD_ID);
  const int currentBuild = CPHUN_OTA_TEST_BASELINE_BUILD;
  LOG_DBG("OTA", "Hungarian Edition OTA compare: actual=%d test-baseline=%d latest=%d",
          actualBuild, currentBuild, latestBuild);
  return latestBuild > currentBuild;
}
'''
s = s[:start] + replacement + s[end:]
p.write_text(s, encoding="utf-8")

h = Path("src/network/OtaUpdater.h")
s = h.read_text(encoding="utf-8")
s = s.replace(
'''  std::string otaUrl;
  size_t otaSize = 0;
''',
'''  std::string otaUrl;
  int latestBuild = 0;
  size_t otaSize = 0;
''', 1)
h.write_text(s, encoding="utf-8")

print("CPHUN-147 OTA test patch applied")
