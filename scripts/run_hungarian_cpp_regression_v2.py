#!/usr/bin/env python3
from pathlib import Path
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
DICT_CPP=ROOT/"src/util/Dictionary.cpp"
CASES=[ROOT/"tests/hungarian_stemming_cases.tsv",ROOT/"tests/hungarian_stemming_cases_v16.tsv"]
FIXTURES=[ROOT/"tests/hungarian_dictionary_headwords_fixture.txt",ROOT/"tests/hungarian_dictionary_headwords_extra.txt"]

src=DICT_CPP.read_text(encoding="utf-8")
start_marker="void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out) {"
end_marker="\nbool Dictionary::lookup("
start=src.index(start_marker)
end=src.index(end_marker,start)
fn=src[start:end]
fn=fn.replace("void Dictionary::stemVariants(const std::string& word, std::vector<std::string>& out)","void stemVariants(const std::string& word, std::vector<std::string>& out)",1)

cpp=r'''#include <algorithm>
#include <cstring>
#include <fstream>
#include <iostream>
#include <string>
#include <unordered_set>
#include <utility>
#include <vector>

'''+fn+r'''
static std::string lookup(const std::string& word,const std::unordered_set<std::string>& headwords){
  if(headwords.count(word)) return word;
  std::vector<std::string> variants;
  stemVariants(word,variants);
  for(const auto& v:variants) if(headwords.count(v)) return v;
  return {};
}

static std::string huLower(std::string word){
  for(char& c:word) if((unsigned char)c<0x80) c=(char)std::tolower((unsigned char)c);
  static constexpr const char* pairs[][2]={{"Á","á"},{"É","é"},{"Í","í"},{"Ó","ó"},{"Ö","ö"},{"Ő","ő"},{"Ú","ú"},{"Ü","ü"},{"Ű","ű"}};
  for(const auto& p:pairs){
    size_t pos=0;
    while((pos=word.find(p[0],pos))!=std::string::npos){word.replace(pos,strlen(p[0]),p[1]);pos+=strlen(p[1]);}
  }
  return word;
}

int main(int argc,char** argv){
  if(argc!=3) return 2;
  std::unordered_set<std::string> headwords;
  std::ifstream hw(argv[1]);
  std::string s;
  while(std::getline(hw,s)) if(!s.empty()) headwords.insert(s);
  std::ifstream cases(argv[2]);
  std::string line;
  int pass=0,fail=0,total=0;
  while(std::getline(cases,line)){
    if(line.empty()) continue;
    auto tab=line.find('\t');
    if(tab==std::string::npos) continue;
    std::string word=line.substr(0,tab),expected=line.substr(tab+1),lowered=huLower(word);
    std::string actual=lookup(lowered,headwords);
    ++total;
    if(actual==expected){++pass;std::cout<<"PASS  "<<word<<" -> "<<actual<<"\n";}
    else{++fail;std::cout<<"FAIL  "<<word<<" -> "<<(actual.empty()?"None":actual)<<"; expected "<<expected<<"\n";}
  }
  std::cout<<"------------------------------------------------------------\n";
  std::cout<<"PASS: "<<pass<<"  FAIL: "<<fail<<"  TOTAL: "<<total<<"\n";
  std::cout<<"RESULT: "<<pass<<"/"<<total<<" C++ firmware stemmer cases\n";
  return fail?1:0;
}
'''

with tempfile.TemporaryDirectory() as td:
    td=Path(td)
    cpp_path=td/"hungarian_cpp_regression.cpp"
    exe_path=td/"hungarian_cpp_regression"
    merged=td/"headwords.txt"
    words=[]
    for fixture in FIXTURES:
        if fixture.exists(): words.extend(x.strip() for x in fixture.read_text(encoding="utf-8").splitlines() if x.strip())
    merged.write_text("\n".join(dict.fromkeys(words))+"\n",encoding="utf-8")
    cpp_path.write_text(cpp,encoding="utf-8")
    subprocess.run(["g++","-std=c++17","-O2","-Wall","-Wextra","-pedantic",str(cpp_path),"-o",str(exe_path)],check=True)
    combined=td/"cases.tsv"
    combined.write_text("".join(case.read_text(encoding="utf-8").rstrip()+"\n" for case in CASES),encoding="utf-8")
    result=subprocess.run([str(exe_path),str(merged),str(combined)])
    raise SystemExit(result.returncode)
