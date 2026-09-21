from pathlib import Path

p = Path("src/network/OtaUpdater.cpp")
s = p.read_text(encoding="utf-8")

old = '''constexpr char latestReleaseUrl[] = "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest";
constexpr int CPHUN_OTA_TEST_BASELINE_BUILD = 135;

int parseCphunBuildId(const char* buildId) {
'''
new = '''constexpr char latestReleaseUrl[] = "https://api.github.com/repos/Matteo1965/crosspoint-reader/releases/latest";

int parseCphunBuildId(const char* buildId) {
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-148 OTA constants anchor matches={s.count(old)}")
s = s.replace(old, new, 1)

old = '''  // CPHUN-147 EXP OTA validation:
  // force the comparison baseline to build 135 so this test image can
  // reproduce the user's real #135 -> public v146 update check.
  const int actualBuild = parseCphunBuildId(CPHUN_BUILD_ID);
  const int currentBuild = CPHUN_OTA_TEST_BASELINE_BUILD;
  LOG_DBG("OTA", "Hungarian Edition OTA compare: actual=%d test-baseline=%d latest=%d",
          actualBuild, currentBuild, latestBuild);
  return latestBuild > currentBuild;
'''
new = '''  const int currentBuild = parseCphunBuildId(CPHUN_BUILD_ID);
  if (currentBuild <= 0) {
    LOG_ERR("OTA", "Invalid Hungarian Edition build id: %s", CPHUN_BUILD_ID);
    return false;
  }

  LOG_DBG("OTA", "Hungarian Edition OTA compare: current=%d latest=%d", currentBuild, latestBuild);
  return latestBuild > currentBuild;
'''
if s.count(old) != 1:
    raise SystemExit(f"CPHUN-148 OTA comparison anchor matches={s.count(old)}")
s = s.replace(old, new, 1)

p.write_text(s, encoding="utf-8")
print("CPHUN-148 applied: production Hungarian Edition OTA build comparison")
