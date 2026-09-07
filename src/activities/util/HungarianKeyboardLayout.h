#pragma once
#include <FreeInkUI.h>
namespace keyboard_layouts { namespace hu_keyboard {
namespace fui = freeink::ui;
#define HUK(label, output, value) fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, 2, true, nullptr }
#define HUKW(label, output, value, units) fui::KeyboardKey { label, output, fui::KeyKind::Normal, fui::StateNormal, value, units, true, nullptr }
#define HUKS(label, kind, value, units) fui::KeyboardKey { label, nullptr, kind, fui::StateNormal, value, units, true, nullptr }

inline const fui::KeyboardKey NUM_ROW[] = {HUK("1","1",'1'),HUK("2","2",'2'),HUK("3","3",'3'),HUK("4","4",'4'),HUK("5","5",'5'),HUK("6","6",'6'),HUK("7","7",'7'),HUK("8","8",'8'),HUK("9","9",'9'),HUK("0","0",'0'),HUK("-","-",'-')};
inline const fui::KeyboardKey ROW1[] = {HUK("Q","q",'q'),HUK("w","w",'w'),HUK("E","e",'e'),HUK("R","r",'r'),HUK("T","t",'t'),HUK("Z","z",'z'),HUK("U","u",'u'),HUK("I","i",'i'),HUK("O","o",'o'),HUK("P","p",'p'),HUK("Ö","ö",1303)};
inline const fui::KeyboardKey ROW2[] = {HUK("A","a",'a'),HUK("S","s",'s'),HUK("D","d",'d'),HUK("F","f",'f'),HUK("G","g",'g'),HUK("H","h",'h'),HUK("J","j",'j'),HUK("K","k",'k'),HUK("L","l",'l'),HUK("É","é",1301),HUK("Á","á",1302)};
inline const fui::KeyboardKey ROW3[] = {HUKS("Sh",fui::KeyKind::Shift,fui::QWERTY_KEY_SHIFT,3),HUK("Y","y",'y'),HUK("X","x",'x'),HUK("C","c",'c'),HUK("V","v",'v'),HUK("B","b",'b'),HUK("N","n",'n'),HUK("M","m",'m'),HUK("Ü","ü",1304),HUKS("Del",fui::KeyKind::Delete,fui::QWERTY_KEY_BACKSPACE,3)};
inline const fui::KeyboardKey SHIFT_ROW1[] = {HUK("Q","Q",'Q'),HUK("w","W",'W'),HUK("E","E",'E'),HUK("R","R",'R'),HUK("T","T",'T'),HUK("Z","Z",'Z'),HUK("U","U",'U'),HUK("I","I",'I'),HUK("O","O",'O'),HUK("P","P",'P'),HUK("Ö","Ö",1353)};
inline const fui::KeyboardKey SHIFT_ROW2[] = {HUK("A","A",'A'),HUK("S","S",'S'),HUK("D","D",'D'),HUK("F","F",'F'),HUK("G","G",'G'),HUK("H","H",'H'),HUK("J","J",'J'),HUK("K","K",'K'),HUK("L","L",'L'),HUK("É","É",1351),HUK("Á","Á",1352)};
inline const fui::KeyboardKey SHIFT_ROW3[] = {HUKS("Sh",fui::KeyKind::Shift,fui::QWERTY_KEY_SHIFT,3),HUK("Y","Y",'Y'),HUK("X","X",'X'),HUK("C","C",'C'),HUK("V","V",'V'),HUK("B","B",'B'),HUK("N","N",'N'),HUK("M","M",'M'),HUK("Ü","Ü",1354),HUKS("Del",fui::KeyKind::Delete,fui::QWERTY_KEY_BACKSPACE,3)};

// CPHUN-71 bottom row: Fn, language, ?, Space, comma, period, OK.
inline const fui::KeyboardKey BOTTOM[] = {HUKS("Fn",fui::KeyKind::Mode,fui::QWERTY_KEY_MODE,3),HUK("?","?",'?'),HUKS("Space",fui::KeyKind::Space,fui::QWERTY_KEY_SPACE,10),HUK(",",",",','),HUK(".",".",'.'),HUKS("OK",fui::KeyKind::Ok,fui::QWERTY_KEY_ENTER,3)};
inline const fui::KeyboardKey BOTTOM_LANG[] = {HUKS("Fn",fui::KeyKind::Mode,fui::QWERTY_KEY_MODE,3),HUKS(nullptr,fui::KeyKind::Lang,fui::QWERTY_KEY_LANG,2),HUK("?","?",'?'),HUKS("Space",fui::KeyKind::Space,fui::QWERTY_KEY_SPACE,8),HUK(",",",",','),HUK(".",".",'.'),HUKS("OK",fui::KeyKind::Ok,fui::QWERTY_KEY_ENTER,3)};

inline const fui::KeyboardKey SYMBOL_ROW1[] = {HUK("1","1",'1'),HUK("2","2",'2'),HUK("3","3",'3'),HUK("4","4",'4'),HUK("5","5",'5'),HUK("6","6",'6'),HUK("7","7",'7'),HUK("8","8",'8'),HUK("9","9",'9'),HUK("0","0",'0'),HUK("-","-",'-')};
inline const fui::KeyboardKey SYMBOL_ROW2[] = {HUK("/","/",'/'),HUK(":",":",':'),HUK(";",";",';'),HUK("(","(",'('),HUK(")",")",')'),HUK("€","€",1401),HUK("$","$",'$'),HUK("&","&",'&'),HUK("@","@",'@'),HUK("„","„",1402),HUK("”","”",1403)};
inline const fui::KeyboardKey SYMBOL_ROW3[] = {HUKS("#+=",fui::KeyKind::Shift,fui::QWERTY_KEY_SHIFT,4),HUK(".",".",'.'),HUK(",",",",','),HUK("?","?",'?'),HUK("!","!",'!'),HUK("'","'",'\''),HUK("\"","\"",'"'),HUK("#","#",'#'),HUK("…","…",1404),HUKS("Del",fui::KeyKind::Delete,fui::QWERTY_KEY_BACKSPACE,4)};
inline const fui::KeyboardKey SYMBOL2_ROW1[] = {HUK("[","[",'['),HUK("]","]",']'),HUK("{","{",'{'),HUK("}","}",'}'),HUK("<","<",'<'),HUK(">",">",'>'),HUK("^","^",'^'),HUK("*","*",'*'),HUK("+","+",'+'),HUK("=","=",'='),HUK("_","_",'_')};
inline const fui::KeyboardKey SYMBOL2_ROW2[] = {HUK("\\","\\",'\\'),HUK("|","|",'|'),HUK("~","~",'~'),HUK("`","`",'`'),HUK("%","%",'%'),HUK("–","–",1410),HUK("—","—",1411),HUK("±","±",1412),HUK("§","§",1413),HUK("°","°",1414),HUK("#","#",'#')};
inline const fui::KeyboardKey SYMBOL2_ROW3[] = {HUKS("123",fui::KeyKind::Shift,fui::QWERTY_KEY_SHIFT,4),HUK(".",".",'.'),HUK(",",",",','),HUK("?","?",'?'),HUK("!","!",'!'),HUK("'","'",'\''),HUK("\"","\"",'"'),HUK(":",":",':'),HUK(";",";",';'),HUKS("Del",fui::KeyKind::Delete,fui::QWERTY_KEY_BACKSPACE,4)};
inline const fui::KeyboardKey SYMBOL_BOTTOM[] = {HUKS("ABC",fui::KeyKind::Mode,fui::QWERTY_KEY_MODE,4),HUK(",",",",','),HUKS("Space",fui::KeyKind::Space,fui::QWERTY_KEY_SPACE,10),HUK(".",".",'.'),HUKS("OK",fui::KeyKind::Ok,fui::QWERTY_KEY_ENTER,4)};

inline const fui::KeyboardRow ROWS[]={{NUM_ROW,11,0},{ROW1,11,0},{ROW2,11,0},{ROW3,10,0},{BOTTOM,6,0}};
inline const fui::KeyboardRow ROWS_LANG[]={{NUM_ROW,11,0},{ROW1,11,0},{ROW2,11,0},{ROW3,10,0},{BOTTOM_LANG,7,0}};
inline const fui::KeyboardRow SHIFT_ROWS[]={{NUM_ROW,11,0},{SHIFT_ROW1,11,0},{SHIFT_ROW2,11,0},{SHIFT_ROW3,10,0},{BOTTOM,6,0}};
inline const fui::KeyboardRow SHIFT_ROWS_LANG[]={{NUM_ROW,11,0},{SHIFT_ROW1,11,0},{SHIFT_ROW2,11,0},{SHIFT_ROW3,10,0},{BOTTOM_LANG,7,0}};
inline const fui::KeyboardRow SYMBOL_ROWS[]={{SYMBOL_ROW1,11,0},{SYMBOL_ROW2,11,0},{SYMBOL_ROW3,10,0},{SYMBOL_BOTTOM,5,0}};
inline const fui::KeyboardRow SYMBOL2_ROWS[]={{SYMBOL2_ROW1,11,0},{SYMBOL2_ROW2,11,0},{SYMBOL2_ROW3,10,0},{SYMBOL_BOTTOM,5,0}};
inline const fui::KeyboardLayout LAYOUT{ROWS,5}; inline const fui::KeyboardLayout LAYOUT_LANG{ROWS_LANG,5}; inline const fui::KeyboardLayout SHIFT_LAYOUT{SHIFT_ROWS,5}; inline const fui::KeyboardLayout SHIFT_LAYOUT_LANG{SHIFT_ROWS_LANG,5}; inline const fui::KeyboardLayout SYMBOL_LAYOUT{SYMBOL_ROWS,4}; inline const fui::KeyboardLayout SYMBOL2_LAYOUT{SYMBOL2_ROWS,4};
inline const fui::KeyboardLayout& layout(bool shifted,bool symbols,bool langKey){if(symbols)return shifted?SYMBOL2_LAYOUT:SYMBOL_LAYOUT;if(shifted)return langKey?SHIFT_LAYOUT_LANG:SHIFT_LAYOUT;return langKey?LAYOUT_LANG:LAYOUT;}
inline bool isHungarianLetterLayout(const fui::KeyboardLayout& current){return &current==&LAYOUT||&current==&LAYOUT_LANG||&current==&SHIFT_LAYOUT||&current==&SHIFT_LAYOUT_LANG;}
inline bool isShiftedLetterLayout(const fui::KeyboardLayout& current){return &current==&SHIFT_LAYOUT||&current==&SHIFT_LAYOUT_LANG;}
inline const char* altOutputFor(const fui::KeyboardLayout& current,const int16_t value){if(!isHungarianLetterLayout(current))return nullptr;switch(value){case '1':return "!";case '2':return "@";case '3':return "#";case '4':return "$";case '5':return "%";case '6':return "^";case '7':return "&";case '8':return "*";case '9':return "(";case '0':return ")";case '-':return "_";default:break;}if(isShiftedLetterLayout(current)){switch(value){case 'A':return "Á";case 'E':return "É";case 'I':return "Í";case 'O':return "Ó";case 'U':return "Ú";case 1353:return "Ő";case 1354:return "Ű";default:return nullptr;}}switch(value){case 'a':return "á";case 'e':return "é";case 'i':return "í";case 'o':return "ó";case 'u':return "ú";case 1303:return "ő";case 1304:return "ű";default:return nullptr;}}
#undef HUK
#undef HUKW
#undef HUKS
} }
