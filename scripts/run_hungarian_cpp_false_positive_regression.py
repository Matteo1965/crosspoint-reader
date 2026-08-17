#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
DICT_CPP = ROOT / "src" / "util" / "Dictionary.cpp"
CASES = ROOT / "tests" / "hungarian_false_positive_tails.tsv"

src = DICT_CPP.read_text(encoding="utf-8")
start_marker = "void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {"
end_marker = "\nbool Dictionary::lookup("
start = src.index(start_marker)
end = src.index(end_marker, start)
fn = src[start:end]
fn = fn.replace(
    "void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out)",
    "void stemVariants(const std::string& word, std::vector<std::string>& out)",
    1,
)

cpp = r'''#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <vector>

''' + fn + r'''

int main(int argc, char** argv) {
  if (argc != 2) return 2;
  std::ifstream cases(argv[1]);
  std::string line;
  int pass = 0, fail = 0, total = 0;
  while (std::getline(cases, line)) {
    if (line.empty() || line[0] == '#') continue;
    auto tab = line.find('\t');
    if (tab == std::string::npos) continue;
    std::string word = line.substr(0, tab);
    std::string forbidden = line.substr(tab + 1);
    std::string lowered = word;
    for (char& c : lowered) {
      if ((unsigned char)c < 0x80) c = (char)std::tolower((unsigned char)c);
    }
    std::vector<std::string> variants;
    stemVariants(lowered, variants);
    bool bad = std::find(variants.begin(), variants.end(), forbidden) != variants.end();
    ++total;
    if (!bad) {
      ++pass;
      std::cout << "PASS  " << word << " does not emit " << forbidden << "\n";
    } else {
      ++fail;
      std::cout << "FAIL  " << word << " emits forbidden tail " << forbidden << "\n";
    }
  }
  std::cout << "------------------------------------------------------------\n";
  std::cout << "PASS: " << pass << "  FAIL: " << fail << "  TOTAL: " << total << "\n";
  std::cout << "RESULT: " << pass << "/" << total << " false-positive guards\n";
  return fail ? 1 : 0;
}
'''

with tempfile.TemporaryDirectory() as td:
    td = Path(td)
    cpp_path = td / "hungarian_cpp_false_positive.cpp"
    exe_path = td / "hungarian_cpp_false_positive"
    cpp_path.write_text(cpp, encoding="utf-8")
    subprocess.run(
        ["g++", "-std=c++17", "-O2", "-Wall", "-Wextra", "-pedantic", str(cpp_path), "-o", str(exe_path)],
        check=True,
    )
    result = subprocess.run([str(exe_path), str(CASES)])
    raise SystemExit(result.returncode)
