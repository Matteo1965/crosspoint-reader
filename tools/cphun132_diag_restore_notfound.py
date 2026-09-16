from pathlib import Path

p = Path("src/activities/reader/DictionaryWordSelectActivity.cpp")
s = p.read_text(encoding="utf-8")
old = '''      case Dictionary::LookupResult::NotFound:
      default:
        showHighlightPrompt(false);
        return;
    }
  }
  popupTime = millis();
  requestUpdate();'''
new = '''      case Dictionary::LookupResult::NotFound:
      default:
        popup = Popup::NotFound;
        popupMsg = StrId::STR_DICT_NOT_FOUND;
        break;
    }
  }
  popupTime = millis();
  requestUpdate();'''
if s.count(old) != 1:
    raise SystemExit(f"Diagnostic NotFound block match count: {s.count(old)}")
p.write_text(s.replace(old, new, 1), encoding="utf-8")
print("CPHUN-132 diagnostic: restored #131 NotFound popup path")
