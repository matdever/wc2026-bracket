#!/usr/bin/env python3
"""
Auto-update the "results" profile in pool.json from ESPN's public FIFA World Cup feed.
GROUP stage (1-72): matched by team pair. KNOCKOUT (73-104): the bracket is resolved
(standings -> best-8 thirds via the official 495 table -> home/away per tie -> winners/
penalties propagating forward), then each tie is matched to its ESPN game by the two teams,
so scores land with the correct orientation. Player profiles are never touched.

Test flags: WC_DRYRUN=1 (don't write), WC_POOL=path.
"""
import json, os, re, sys, unicodedata, urllib.request
from datetime import datetime, timezone

POOL_PATH=os.environ.get("WC_POOL","pool.json")
DRYRUN=bool(os.environ.get("WC_DRYRUN"))
ESPN="https://site.api.espn.com/apis/site/v2/sports/soccer/fifa.world/scoreboard?dates={d}"
GROUP_DATES=[f"202606{d:02d}" for d in range(11,28)]
KO_DATES=[f"202606{d:02d}" for d in range(28,31)]+[f"202607{d:02d}" for d in range(1,20)]

GROUPS={
    'A': ['Mexico', 'South Africa', 'South Korea', 'Czech Republic'],
    'B': ['Canada', 'Bosnia and Herzegovina', 'Qatar', 'Switzerland'],
    'C': ['Brazil', 'Morocco', 'Haiti', 'Scotland'],
    'D': ['United States', 'Paraguay', 'Australia', 'Turkey'],
    'E': ['Germany', 'Curaçao', 'Ivory Coast', 'Ecuador'],
    'F': ['Netherlands', 'Japan', 'Sweden', 'Tunisia'],
    'G': ['Belgium', 'Egypt', 'Iran', 'New Zealand'],
    'H': ['Spain', 'Cape Verde', 'Saudi Arabia', 'Uruguay'],
    'I': ['France', 'Senegal', 'Iraq', 'Norway'],
    'J': ['Argentina', 'Algeria', 'Austria', 'Jordan'],
    'K': ['Portugal', 'DR Congo', 'Uzbekistan', 'Colombia'],
    'L': ['England', 'Croatia', 'Ghana', 'Panama'],
}
GROUP_FIXTURES={
    1: ('Mexico', 'South Africa'),
    2: ('South Korea', 'Czech Republic'),
    3: ('Canada', 'Bosnia and Herzegovina'),
    4: ('United States', 'Paraguay'),
    5: ('Haiti', 'Scotland'),
    6: ('Australia', 'Turkey'),
    7: ('Brazil', 'Morocco'),
    8: ('Qatar', 'Switzerland'),
    9: ('Ivory Coast', 'Ecuador'),
    10: ('Germany', 'Curaçao'),
    11: ('Netherlands', 'Japan'),
    12: ('Sweden', 'Tunisia'),
    13: ('Saudi Arabia', 'Uruguay'),
    14: ('Spain', 'Cape Verde'),
    15: ('Iran', 'New Zealand'),
    16: ('Belgium', 'Egypt'),
    17: ('France', 'Senegal'),
    18: ('Iraq', 'Norway'),
    19: ('Argentina', 'Algeria'),
    20: ('Austria', 'Jordan'),
    21: ('Ghana', 'Panama'),
    22: ('England', 'Croatia'),
    23: ('Portugal', 'DR Congo'),
    24: ('Uzbekistan', 'Colombia'),
    25: ('Czech Republic', 'South Africa'),
    26: ('Switzerland', 'Bosnia and Herzegovina'),
    27: ('Canada', 'Qatar'),
    28: ('Mexico', 'South Korea'),
    29: ('Brazil', 'Haiti'),
    30: ('Scotland', 'Morocco'),
    31: ('Turkey', 'Paraguay'),
    32: ('United States', 'Australia'),
    33: ('Germany', 'Ivory Coast'),
    34: ('Ecuador', 'Curaçao'),
    35: ('Netherlands', 'Sweden'),
    36: ('Tunisia', 'Japan'),
    37: ('Uruguay', 'Cape Verde'),
    38: ('Spain', 'Saudi Arabia'),
    39: ('Belgium', 'Iran'),
    40: ('New Zealand', 'Egypt'),
    41: ('Norway', 'Senegal'),
    42: ('France', 'Iraq'),
    43: ('Argentina', 'Austria'),
    44: ('Jordan', 'Algeria'),
    45: ('England', 'Ghana'),
    46: ('Panama', 'Croatia'),
    47: ('Portugal', 'Uzbekistan'),
    48: ('Colombia', 'DR Congo'),
    49: ('Scotland', 'Brazil'),
    50: ('Morocco', 'Haiti'),
    51: ('Switzerland', 'Canada'),
    52: ('Bosnia and Herzegovina', 'Qatar'),
    53: ('Czech Republic', 'Mexico'),
    54: ('South Africa', 'South Korea'),
    55: ('Curaçao', 'Ivory Coast'),
    56: ('Ecuador', 'Germany'),
    57: ('Japan', 'Sweden'),
    58: ('Tunisia', 'Netherlands'),
    59: ('Turkey', 'United States'),
    60: ('Paraguay', 'Australia'),
    61: ('Norway', 'France'),
    62: ('Senegal', 'Iraq'),
    63: ('Egypt', 'Iran'),
    64: ('New Zealand', 'Belgium'),
    65: ('Cape Verde', 'Saudi Arabia'),
    66: ('Uruguay', 'Spain'),
    67: ('Panama', 'England'),
    68: ('Croatia', 'Ghana'),
    69: ('Algeria', 'Austria'),
    70: ('Jordan', 'Argentina'),
    71: ('Colombia', 'Portugal'),
    72: ('DR Congo', 'Uzbekistan'),
}
WINORDER=['A', 'B', 'D', 'E', 'G', 'I', 'K', 'L']
THIRD={"ABCDEFGH":"HGBCAFDE","ABCDEFGI":"CGBDAFEI","ABCDEFGJ":"CGBDAFEJ","ABCDEFGK":"CGBDAFEK","ABCDEFGL":"CGBDAFLE","ABCDEFHI":"HEBCAFDI","ABCDEFHJ":"HJBCAFDE","ABCDEFHK":"HEBCAFDK","ABCDEFHL":"HFBCADLE","ABCDEFIJ":"CJBDAFEI","ABCDEFIK":"CEBDAFIK","ABCDEFIL":"CEBDAFLI","ABCDEFJK":"CJBDAFEK","ABCDEFJL":"CJBDAFLE","ABCDEFKL":"CEBDAFLK","ABCDEGHI":"HGBCADEI","ABCDEGHJ":"HGBCADEJ","ABCDEGHK":"HGBCADEK","ABCDEGHL":"HGBCADLE","ABCDEGIJ":"EGBCADIJ","ABCDEGIK":"EGBCADIK","ABCDEGIL":"EGBCADLI","ABCDEGJK":"EGBCADJK","ABCDEGJL":"EGBCADLJ","ABCDEGKL":"EGBCADLK","ABCDEHIJ":"HJBCADEI","ABCDEHIK":"HEBCADIK","ABCDEHIL":"HEBCADLI","ABCDEHJK":"HJBCADEK","ABCDEHJL":"HJBCADLE","ABCDEHKL":"HEBCADLK","ABCDEIJK":"EJBCADIK","ABCDEIJL":"EJBCADLI","ABCDEIKL":"EIBCADLK","ABCDEJKL":"EJBCADLK","ABCDFGHI":"HGBCAFDI","ABCDFGHJ":"HGBCAFDJ","ABCDFGHK":"HGBCAFDK","ABCDFGHL":"CGBDAFLH","ABCDFGIJ":"CGBDAFIJ","ABCDFGIK":"CGBDAFIK","ABCDFGIL":"CGBDAFLI","ABCDFGJK":"CGBDAFJK","ABCDFGJL":"CGBDAFLJ","ABCDFGKL":"CGBDAFLK","ABCDFHIJ":"HJBCAFDI","ABCDFHIK":"HFBCADIK","ABCDFHIL":"HFBCADLI","ABCDFHJK":"HJBCAFDK","ABCDFHJL":"CJBDAFLH","ABCDFHKL":"HFBCADLK","ABCDFIJK":"CJBDAFIK","ABCDFIJL":"CJBDAFLI","ABCDFIKL":"CIBDAFLK","ABCDFJKL":"CJBDAFLK","ABCDGHIJ":"HGBCADIJ","ABCDGHIK":"HGBCADIK","ABCDGHIL":"HGBCADLI","ABCDGHJK":"HGBCADJK","ABCDGHJL":"HGBCADLJ","ABCDGHKL":"HGBCADLK","ABCDGIJK":"CJBDAGIK","ABCDGIJL":"CJBDAGLI","ABCDGIKL":"IGBCADLK","ABCDGJKL":"CJBDAGLK","ABCDHIJK":"HJBCADIK","ABCDHIJL":"HJBCADLI","ABCDHIKL":"HIBCADLK","ABCDHJKL":"HJBCADLK","ABCDIJKL":"IJBCADLK","ABCEFGHI":"HGBCAFEI","ABCEFGHJ":"HGBCAFEJ","ABCEFGHK":"HGBCAFEK","ABCEFGHL":"HGBCAFLE","ABCEFGIJ":"EGBCAFIJ","ABCEFGIK":"EGBCAFIK","ABCEFGIL":"EGBCAFLI","ABCEFGJK":"EGBCAFJK","ABCEFGJL":"EGBCAFLJ","ABCEFGKL":"EGBCAFLK","ABCEFHIJ":"HJBCAFEI","ABCEFHIK":"HEBCAFIK","ABCEFHIL":"HEBCAFLI","ABCEFHJK":"HJBCAFEK","ABCEFHJL":"HJBCAFLE","ABCEFHKL":"HEBCAFLK","ABCEFIJK":"EJBCAFIK","ABCEFIJL":"EJBCAFLI","ABCEFIKL":"EIBCAFLK","ABCEFJKL":"EJBCAFLK","ABCEGHIJ":"HJBCAGEI","ABCEGHIK":"EGBCAHIK","ABCEGHIL":"EGBCAHLI","ABCEGHJK":"HJBCAGEK","ABCEGHJL":"HJBCAGLE","ABCEGHKL":"EGBCAHLK","ABCEGIJK":"EJBCAGIK","ABCEGIJL":"EJBCAGLI","ABCEGIKL":"EGBAICLK","ABCEGJKL":"EJBCAGLK","ABCEHIJK":"EJBCAHIK","ABCEHIJL":"EJBCAHLI","ABCEHIKL":"EIBCAHLK","ABCEHJKL":"EJBCAHLK","ABCEIJKL":"EJBAICLK","ABCFGHIJ":"HGBCAFIJ","ABCFGHIK":"HGBCAFIK","ABCFGHIL":"HGBCAFLI","ABCFGHJK":"HGBCAFJK","ABCFGHJL":"HGBCAFLJ","ABCFGHKL":"HGBCAFLK","ABCFGIJK":"CJBFAGIK","ABCFGIJL":"CJBFAGLI","ABCFGIKL":"IGBCAFLK","ABCFGJKL":"CJBFAGLK","ABCFHIJK":"HJBCAFIK","ABCFHIJL":"HJBCAFLI","ABCFHIKL":"HIBCAFLK","ABCFHJKL":"HJBCAFLK","ABCFIJKL":"IJBCAFLK","ABCGHIJK":"HJBCAGIK","ABCGHIJL":"HJBCAGLI","ABCGHIKL":"IGBCAHLK","ABCGHJKL":"HJBCAGLK","ABCGIJKL":"IJBCAGLK","ABCHIJKL":"IJBCAHLK","ABDEFGHI":"HGBDAFEI","ABDEFGHJ":"HGBDAFEJ","ABDEFGHK":"HGBDAFEK","ABDEFGHL":"HGBDAFLE","ABDEFGIJ":"EGBDAFIJ","ABDEFGIK":"EGBDAFIK","ABDEFGIL":"EGBDAFLI","ABDEFGJK":"EGBDAFJK","ABDEFGJL":"EGBDAFLJ","ABDEFGKL":"EGBDAFLK","ABDEFHIJ":"HJBDAFEI","ABDEFHIK":"HEBDAFIK","ABDEFHIL":"HEBDAFLI","ABDEFHJK":"HJBDAFEK","ABDEFHJL":"HJBDAFLE","ABDEFHKL":"HEBDAFLK","ABDEFIJK":"EJBDAFIK","ABDEFIJL":"EJBDAFLI","ABDEFIKL":"EIBDAFLK","ABDEFJKL":"EJBDAFLK","ABDEGHIJ":"HJBDAGEI","ABDEGHIK":"EGBDAHIK","ABDEGHIL":"EGBDAHLI","ABDEGHJK":"HJBDAGEK","ABDEGHJL":"HJBDAGLE","ABDEGHKL":"EGBDAHLK","ABDEGIJK":"EJBDAGIK","ABDEGIJL":"EJBDAGLI","ABDEGIKL":"EGBAIDLK","ABDEGJKL":"EJBDAGLK","ABDEHIJK":"EJBDAHIK","ABDEHIJL":"EJBDAHLI","ABDEHIKL":"EIBDAHLK","ABDEHJKL":"EJBDAHLK","ABDEIJKL":"EJBAIDLK","ABDFGHIJ":"HGBDAFIJ","ABDFGHIK":"HGBDAFIK","ABDFGHIL":"HGBDAFLI","ABDFGHJK":"HGBDAFJK","ABDFGHJL":"HGBDAFLJ","ABDFGHKL":"HGBDAFLK","ABDFGIJK":"FJBDAGIK","ABDFGIJL":"FJBDAGLI","ABDFGIKL":"IGBDAFLK","ABDFGJKL":"FJBDAGLK","ABDFHIJK":"HJBDAFIK","ABDFHIJL":"HJBDAFLI","ABDFHIKL":"HIBDAFLK","ABDFHJKL":"HJBDAFLK","ABDFIJKL":"IJBDAFLK","ABDGHIJK":"HJBDAGIK","ABDGHIJL":"HJBDAGLI","ABDGHIKL":"IGBDAHLK","ABDGHJKL":"HJBDAGLK","ABDGIJKL":"IJBDAGLK","ABDHIJKL":"IJBDAHLK","ABEFGHIJ":"HJBFAGEI","ABEFGHIK":"EGBFAHIK","ABEFGHIL":"EGBFAHLI","ABEFGHJK":"HJBFAGEK","ABEFGHJL":"HJBFAGLE","ABEFGHKL":"EGBFAHLK","ABEFGIJK":"EJBFAGIK","ABEFGIJL":"EJBFAGLI","ABEFGIKL":"EGBAIFLK","ABEFGJKL":"EJBFAGLK","ABEFHIJK":"EJBFAHIK","ABEFHIJL":"EJBFAHLI","ABEFHIKL":"EIBFAHLK","ABEFHJKL":"EJBFAHLK","ABEFIJKL":"EJBAIFLK","ABEGHIJK":"EJBAHGIK","ABEGHIJL":"EJBAHGLI","ABEGHIKL":"EGBAIHLK","ABEGHJKL":"EJBAHGLK","ABEGIJKL":"EJBAIGLK","ABEHIJKL":"EJBAIHLK","ABFGHIJK":"HJBFAGIK","ABFGHIJL":"HJBFAGLI","ABFGHIKL":"HGBAIFLK","ABFGHJKL":"HJBFAGLK","ABFGIJKL":"IJBFAGLK","ABFHIJKL":"HJBAIFLK","ABGHIJKL":"HJBAIGLK","ACDEFGHI":"HGECAFDI","ACDEFGHJ":"HGJCAFDE","ACDEFGHK":"HGECAFDK","ACDEFGHL":"HGFCADLE","ACDEFGIJ":"CGJDAFEI","ACDEFGIK":"CGEDAFIK","ACDEFGIL":"CGEDAFLI","ACDEFGJK":"CGJDAFEK","ACDEFGJL":"CGJDAFLE","ACDEFGKL":"CGEDAFLK","ACDEFHIJ":"HJECAFDI","ACDEFHIK":"HEFCADIK","ACDEFHIL":"HEFCADLI","ACDEFHJK":"HJECAFDK","ACDEFHJL":"HJFCADLE","ACDEFHKL":"HEFCADLK","ACDEFIJK":"CJEDAFIK","ACDEFIJL":"CJEDAFLI","ACDEFIKL":"CEIDAFLK","ACDEFJKL":"CJEDAFLK","ACDEGHIJ":"HGJCADEI","ACDEGHIK":"HGECADIK","ACDEGHIL":"HGECADLI","ACDEGHJK":"HGJCADEK","ACDEGHJL":"HGJCADLE","ACDEGHKL":"HGECADLK","ACDEGIJK":"EGJCADIK","ACDEGIJL":"EGJCADLI","ACDEGIKL":"EGICADLK","ACDEGJKL":"EGJCADLK","ACDEHIJK":"HJECADIK","ACDEHIJL":"HJECADLI","ACDEHIKL":"HEICADLK","ACDEHJKL":"HJECADLK","ACDEIJKL":"EJICADLK","ACDFGHIJ":"HGJCAFDI","ACDFGHIK":"HGFCADIK","ACDFGHIL":"HGFCADLI","ACDFGHJK":"HGJCAFDK","ACDFGHJL":"CGJDAFLH","ACDFGHKL":"HGFCADLK","ACDFGIJK":"CGJDAFIK","ACDFGIJL":"CGJDAFLI","ACDFGIKL":"CGIDAFLK","ACDFGJKL":"CGJDAFLK","ACDFHIJK":"HJFCADIK","ACDFHIJL":"HJFCADLI","ACDFHIKL":"HFICADLK","ACDFHJKL":"HJFCADLK","ACDFIJKL":"CJIDAFLK","ACDGHIJK":"HGJCADIK","ACDGHIJL":"HGJCADLI","ACDGHIKL":"HGICADLK","ACDGHJKL":"HGJCADLK","ACDGIJKL":"IGJCADLK","ACDHIJKL":"HJICADLK","ACEFGHIJ":"HGJCAFEI","ACEFGHIK":"HGECAFIK","ACEFGHIL":"HGECAFLI","ACEFGHJK":"HGJCAFEK","ACEFGHJL":"HGJCAFLE","ACEFGHKL":"HGECAFLK","ACEFGIJK":"EGJCAFIK","ACEFGIJL":"EGJCAFLI","ACEFGIKL":"EGICAFLK","ACEFGJKL":"EGJCAFLK","ACEFHIJK":"HJECAFIK","ACEFHIJL":"HJECAFLI","ACEFHIKL":"HEICAFLK","ACEFHJKL":"HJECAFLK","ACEFIJKL":"EJICAFLK","ACEGHIJK":"EGJCAHIK","ACEGHIJL":"EGJCAHLI","ACEGHIKL":"EGICAHLK","ACEGHJKL":"EGJCAHLK","ACEGIJKL":"EJICAGLK","ACEHIJKL":"EJICAHLK","ACFGHIJK":"HGJCAFIK","ACFGHIJL":"HGJCAFLI","ACFGHIKL":"HGICAFLK","ACFGHJKL":"HGJCAFLK","ACFGIJKL":"IGJCAFLK","ACFHIJKL":"HJICAFLK","ACGHIJKL":"HJICAGLK","ADEFGHIJ":"HGJDAFEI","ADEFGHIK":"HGEDAFIK","ADEFGHIL":"HGEDAFLI","ADEFGHJK":"HGJDAFEK","ADEFGHJL":"HGJDAFLE","ADEFGHKL":"HGEDAFLK","ADEFGIJK":"EGJDAFIK","ADEFGIJL":"EGJDAFLI","ADEFGIKL":"EGIDAFLK","ADEFGJKL":"EGJDAFLK","ADEFHIJK":"HJEDAFIK","ADEFHIJL":"HJEDAFLI","ADEFHIKL":"HEIDAFLK","ADEFHJKL":"HJEDAFLK","ADEFIJKL":"EJIDAFLK","ADEGHIJK":"EGJDAHIK","ADEGHIJL":"EGJDAHLI","ADEGHIKL":"EGIDAHLK","ADEGHJKL":"EGJDAHLK","ADEGIJKL":"EJIDAGLK","ADEHIJKL":"EJIDAHLK","ADFGHIJK":"HGJDAFIK","ADFGHIJL":"HGJDAFLI","ADFGHIKL":"HGIDAFLK","ADFGHJKL":"HGJDAFLK","ADFGIJKL":"IGJDAFLK","ADFHIJKL":"HJIDAFLK","ADGHIJKL":"HJIDAGLK","AEFGHIJK":"EGJFAHIK","AEFGHIJL":"EGJFAHLI","AEFGHIKL":"EGIFAHLK","AEFGHJKL":"EGJFAHLK","AEFGIJKL":"EJIFAGLK","AEFHIJKL":"EJIFAHLK","AEGHIJKL":"EJIAHGLK","AFGHIJKL":"HJIFAGLK","BCDEFGHI":"CGBDHFEI","BCDEFGHJ":"HGBCJFDE","BCDEFGHK":"CGBDHFEK","BCDEFGHL":"CGBDHFLE","BCDEFGIJ":"CGBDJFEI","BCDEFGIK":"CGBDEFIK","BCDEFGIL":"CGBDEFLI","BCDEFGJK":"CGBDJFEK","BCDEFGJL":"CGBDJFLE","BCDEFGKL":"CGBDEFLK","BCDEFHIJ":"CJBDHFEI","BCDEFHIK":"CEBDHFIK","BCDEFHIL":"CEBDHFLI","BCDEFHJK":"CJBDHFEK","BCDEFHJL":"CJBDHFLE","BCDEFHKL":"CEBDHFLK","BCDEFIJK":"CJBDEFIK","BCDEFIJL":"CJBDEFLI","BCDEFIKL":"CEBDIFLK","BCDEFJKL":"CJBDEFLK","BCDEGHIJ":"HGBCJDEI","BCDEGHIK":"EGBCHDIK","BCDEGHIL":"EGBCHDLI","BCDEGHJK":"HGBCJDEK","BCDEGHJL":"HGBCJDLE","BCDEGHKL":"EGBCHDLK","BCDEGIJK":"EGBCJDIK","BCDEGIJL":"EGBCJDLI","BCDEGIKL":"EGBCIDLK","BCDEGJKL":"EGBCJDLK","BCDEHIJK":"EJBCHDIK","BCDEHIJL":"EJBCHDLI","BCDEHIKL":"EIBCHDLK","BCDEHJKL":"EJBCHDLK","BCDEIJKL":"EJBCIDLK","BCDFGHIJ":"HGBCJFDI","BCDFGHIK":"CGBDHFIK","BCDFGHIL":"CGBDHFLI","BCDFGHJK":"HGBCJFDK","BCDFGHJL":"CGBDHFLJ","BCDFGHKL":"CGBDHFLK","BCDFGIJK":"CGBDJFIK","BCDFGIJL":"CGBDJFLI","BCDFGIKL":"CGBDIFLK","BCDFGJKL":"CGBDJFLK","BCDFHIJK":"CJBDHFIK","BCDFHIJL":"CJBDHFLI","BCDFHIKL":"CIBDHFLK","BCDFHJKL":"CJBDHFLK","BCDFIJKL":"CJBDIFLK","BCDGHIJK":"HGBCJDIK","BCDGHIJL":"HGBCJDLI","BCDGHIKL":"HGBCIDLK","BCDGHJKL":"HGBCJDLK","BCDGIJKL":"IGBCJDLK","BCDHIJKL":"HJBCIDLK","BCEFGHIJ":"HGBCJFEI","BCEFGHIK":"EGBCHFIK","BCEFGHIL":"EGBCHFLI","BCEFGHJK":"HGBCJFEK","BCEFGHJL":"HGBCJFLE","BCEFGHKL":"EGBCHFLK","BCEFGIJK":"EGBCJFIK","BCEFGIJL":"EGBCJFLI","BCEFGIKL":"EGBCIFLK","BCEFGJKL":"EGBCJFLK","BCEFHIJK":"EJBCHFIK","BCEFHIJL":"EJBCHFLI","BCEFHIKL":"EIBCHFLK","BCEFHJKL":"EJBCHFLK","BCEFIJKL":"EJBCIFLK","BCEGHIJK":"EJBCHGIK","BCEGHIJL":"EJBCHGLI","BCEGHIKL":"EGBCIHLK","BCEGHJKL":"EJBCHGLK","BCEGIJKL":"EJBCIGLK","BCEHIJKL":"EJBCIHLK","BCFGHIJK":"HGBCJFIK","BCFGHIJL":"HGBCJFLI","BCFGHIKL":"HGBCIFLK","BCFGHJKL":"HGBCJFLK","BCFGIJKL":"IGBCJFLK","BCFHIJKL":"HJBCIFLK","BCGHIJKL":"HJBCIGLK","BDEFGHIJ":"HGBDJFEI","BDEFGHIK":"EGBDHFIK","BDEFGHIL":"EGBDHFLI","BDEFGHJK":"HGBDJFEK","BDEFGHJL":"HGBDJFLE","BDEFGHKL":"EGBDHFLK","BDEFGIJK":"EGBDJFIK","BDEFGIJL":"EGBDJFLI","BDEFGIKL":"EGBDIFLK","BDEFGJKL":"EGBDJFLK","BDEFHIJK":"EJBDHFIK","BDEFHIJL":"EJBDHFLI","BDEFHIKL":"EIBDHFLK","BDEFHJKL":"EJBDHFLK","BDEFIJKL":"EJBDIFLK","BDEGHIJK":"EJBDHGIK","BDEGHIJL":"EJBDHGLI","BDEGHIKL":"EGBDIHLK","BDEGHJKL":"EJBDHGLK","BDEGIJKL":"EJBDIGLK","BDEHIJKL":"EJBDIHLK","BDFGHIJK":"HGBDJFIK","BDFGHIJL":"HGBDJFLI","BDFGHIKL":"HGBDIFLK","BDFGHJKL":"HGBDJFLK","BDFGIJKL":"IGBDJFLK","BDFHIJKL":"HJBDIFLK","BDGHIJKL":"HJBDIGLK","BEFGHIJK":"EJBFHGIK","BEFGHIJL":"EJBFHGLI","BEFGHIKL":"EGBFIHLK","BEFGHJKL":"EJBFHGLK","BEFGIJKL":"EJBFIGLK","BEFHIJKL":"EJBFIHLK","BEGHIJKL":"EJIBHGLK","BFGHIJKL":"HJBFIGLK","CDEFGHIJ":"CGJDHFEI","CDEFGHIK":"CGEDHFIK","CDEFGHIL":"CGEDHFLI","CDEFGHJK":"CGJDHFEK","CDEFGHJL":"CGJDHFLE","CDEFGHKL":"CGEDHFLK","CDEFGIJK":"CGEDJFIK","CDEFGIJL":"CGEDJFLI","CDEFGIKL":"CGEDIFLK","CDEFGJKL":"CGEDJFLK","CDEFHIJK":"CJEDHFIK","CDEFHIJL":"CJEDHFLI","CDEFHIKL":"CEIDHFLK","CDEFHJKL":"CJEDHFLK","CDEFIJKL":"CJEDIFLK","CDEGHIJK":"EGJCHDIK","CDEGHIJL":"EGJCHDLI","CDEGHIKL":"EGICHDLK","CDEGHJKL":"EGJCHDLK","CDEGIJKL":"EGICJDLK","CDEHIJKL":"EJICHDLK","CDFGHIJK":"CGJDHFIK","CDFGHIJL":"CGJDHFLI","CDFGHIKL":"CGIDHFLK","CDFGHJKL":"CGJDHFLK","CDFGIJKL":"CGIDJFLK","CDFHIJKL":"CJIDHFLK","CDGHIJKL":"HGICJDLK","CEFGHIJK":"EGJCHFIK","CEFGHIJL":"EGJCHFLI","CEFGHIKL":"EGICHFLK","CEFGHJKL":"EGJCHFLK","CEFGIJKL":"EGICJFLK","CEFHIJKL":"EJICHFLK","CEGHIJKL":"EJICHGLK","CFGHIJKL":"HGICJFLK","DEFGHIJK":"EGJDHFIK","DEFGHIJL":"EGJDHFLI","DEFGHIKL":"EGIDHFLK","DEFGHJKL":"EGJDHFLK","DEFGIJKL":"EGIDJFLK","DEFHIJKL":"EJIDHFLK","DEGHIJKL":"EJIDHGLK","DFGHIJKL":"HGIDJFLK","EFGHIJKL":"EJIFHGLK"}
ALIASES={"bosniaherzegovina":"bosniaandherzegovina","congodr":"drcongo","czechia":"czechrepublic","turkiye":"turkey"}

# knockout structure: match -> {h: spec, a: spec}; spec ('W'/'R'/'3'/'Wm'/'Lm', arg)
R32={
 73:(('R','A'),('R','B')),74:(('W','E'),('3','E')),75:(('W','F'),('R','C')),76:(('W','C'),('R','F')),
 77:(('W','I'),('3','I')),78:(('R','E'),('R','I')),79:(('W','A'),('3','A')),80:(('W','L'),('3','L')),
 81:(('W','D'),('3','D')),82:(('W','G'),('3','G')),83:(('R','K'),('R','L')),84:(('W','H'),('R','J')),
 85:(('W','B'),('3','B')),86:(('W','J'),('R','H')),87:(('W','K'),('3','K')),88:(('R','D'),('R','G'))}
FEED={
 89:(('Wm',74),('Wm',77)),90:(('Wm',73),('Wm',75)),91:(('Wm',76),('Wm',78)),92:(('Wm',79),('Wm',80)),
 93:(('Wm',83),('Wm',84)),94:(('Wm',81),('Wm',82)),95:(('Wm',86),('Wm',88)),96:(('Wm',85),('Wm',87)),
 97:(('Wm',89),('Wm',90)),98:(('Wm',93),('Wm',94)),99:(('Wm',91),('Wm',92)),100:(('Wm',95),('Wm',96)),
 101:(('Wm',97),('Wm',98)),102:(('Wm',99),('Wm',100)),103:(('Lm',101),('Lm',102)),104:(('Wm',101),('Wm',102))}

TEAM_GROUP={t:g for g,ts in GROUPS.items() for t in ts}
GROUP_MATCHES={g:[n for n in GROUP_FIXTURES if TEAM_GROUP[GROUP_FIXTURES[n][0]]==g] for g in GROUPS}

def norm(s):
    s=unicodedata.normalize("NFKD",s or "").encode("ascii","ignore").decode()
    s=re.sub(r"[^a-z0-9]","",s.lower()); return ALIASES.get(s,s)
def fetch(url):
    return json.load(urllib.request.urlopen(urllib.request.Request(url,headers={"User-Agent":"wc2026-bot"}),timeout=25))
def played(r): return bool(r) and r.get("h") is not None and r.get("a") is not None

def standings(g,results):
    teams=GROUPS[g]; S={t:dict(team=t,GF=0,GA=0,GD=0,Pts=0,draw=i) for i,t in enumerate(teams)}
    for n in GROUP_MATCHES[g]:
        r=results.get(str(n))
        if not played(r): continue
        h,a=r["h"],r["a"]; H=S[GROUP_FIXTURES[n][0]]; A=S[GROUP_FIXTURES[n][1]]
        H["GF"]+=h;H["GA"]+=a;A["GF"]+=a;A["GA"]+=h
        if h>a:H["Pts"]+=3
        elif a>h:A["Pts"]+=3
        else:H["Pts"]+=1;A["Pts"]+=1
    for x in S.values(): x["GD"]=x["GF"]-x["GA"]
    arr=sorted(S.values(),key=lambda x:(-x["Pts"],-x["GD"],-x["GF"],x["draw"]))
    out=[];i=0
    while i<len(arr):
        j=i+1
        while j<len(arr) and (arr[j]["Pts"],arr[j]["GD"],arr[j]["GF"])==(arr[i]["Pts"],arr[i]["GD"],arr[i]["GF"]): j+=1
        tie=arr[i:j]
        if len(tie)>1:
            h2h=h2h_among(g,[t["team"] for t in tie],results)
            tie.sort(key=lambda t:(-h2h[t["team"]]["pts"],-h2h[t["team"]]["gd"],-h2h[t["team"]]["gf"],t["draw"]))
        out.extend(tie); i=j
    return out
def h2h_among(g,teams,results):
    st={t:dict(pts=0,gd=0,gf=0) for t in teams}; ss=set(teams)
    for n in GROUP_MATCHES[g]:
        r=results.get(str(n))
        if not played(r): continue
        H,A=GROUP_FIXTURES[n]
        if H in ss and A in ss:
            h,a=r["h"],r["a"]; st[H]["gf"]+=h;st[A]["gf"]+=a;st[H]["gd"]+=h-a;st[A]["gd"]+=a-h
            if h>a:st[H]["pts"]+=3
            elif a>h:st[A]["pts"]+=3
            else:st[H]["pts"]+=1;st[A]["pts"]+=1
    return st
def group_complete(g,results): return all(played(results.get(str(n))) for n in GROUP_MATCHES[g])
def all_complete(results): return all(group_complete(g,results) for g in GROUPS)
def pos_team(g,idx,results): return standings(g,results)[idx]["team"] if group_complete(g,results) else None
def third_mapping(results):
    if not all_complete(results): return None
    lst=[]
    for g in GROUPS:
        st=standings(g,results)[2]; lst.append((st["Pts"],st["GD"],st["GF"],g,st["team"]))
    lst.sort(key=lambda x:(-x[0],-x[1],-x[2],x[3]))
    key="".join(sorted(x[3] for x in lst[:8])); v=THIRD.get(key)
    if not v: return None
    return {WINORDER[i]:v[i] for i in range(8)}

def fetch_pairs(dates):
    pairs={}
    for d in dates:
        try: j=fetch(ESPN.format(d=d))
        except Exception as e: print("fetch fail",d,e); continue
        for ev in j.get("events",[]):
            c=(ev.get("competitions") or [{}])[0]; st=(c.get("status") or {}).get("type") or {}
            if not st.get("completed"): continue
            comps=c.get("competitors",[])
            if len(comps)!=2: continue
            sc={};ss={};winner=None
            ok=True
            for x in comps:
                nm=norm(x.get("team",{}).get("displayName",""))
                try: sc[nm]=int(x.get("score"))
                except: ok=False
                so=x.get("shootoutScore")
                if so not in (None,""):
                    try: ss[nm]=int(so)
                    except: pass
                if x.get("winner"): winner=nm
            if ok and len(sc)==2:
                pairs[frozenset(sc)]={"scores":sc,"pen":(winner if len(ss)==2 else None)}
    return pairs

def main():
    try: pool=json.load(open(POOL_PATH,encoding="utf-8"))
    except Exception as e: print("read fail",e); return 0
    prof=next((p for p in pool.get("profiles",[]) if p.get("name")==pool.get("resultsName")),None)
    if prof is None: print("no results profile"); return 0
    results=prof.setdefault("results",{})
    now=datetime.now(timezone.utc); changed=0

    # ---- GROUP stage (team-pair match) ----
    gpairs=fetch_pairs(GROUP_DATES)
    glook={frozenset((norm(h),norm(a))):(n,h,a) for n,(h,a) in GROUP_FIXTURES.items()}
    for key,g in gpairs.items():
        hit=glook.get(key)
        if not hit: continue
        n,h,a=hit; sc={"h":g["scores"][norm(h)],"a":g["scores"][norm(a)]}
        if results.get(str(n))!=sc:
            results[str(n)]=sc; changed+=1; print(f"  group M{n}: {h} {sc['h']}-{sc['a']} {a}")

    # ---- KNOCKOUT (resolve bracket, then team-pair match) ----
    kpairs=fetch_pairs(KO_DATES)
    ko_w={};ko_l={}
    def resolve(spec):
        t,arg=spec
        if t=="W": return pos_team(arg,0,results)
        if t=="R": return pos_team(arg,1,results)
        if t=="3":
            m=third_mapping(results); return pos_team(m[arg],2,results) if m else None
        if t=="Wm": return ko_w.get(arg)
        if t=="Lm": return ko_l.get(arg)
    for n in range(73,105):
        spec=R32.get(n) or FEED.get(n)
        home=resolve(spec[0]); away=resolve(spec[1])
        if not home or not away: continue
        g=kpairs.get(frozenset((norm(home),norm(away))))
        if not g: continue
        hs=g["scores"].get(norm(home)); aw=g["scores"].get(norm(away))
        if hs is None or aw is None: continue
        rec={"h":hs,"a":aw}
        if g["pen"]: rec["pen"]="h" if g["pen"]==norm(home) else "a"
        if results.get(str(n))!=rec:
            results[str(n)]=rec; changed+=1; print(f"  KO M{n}: {home} {hs}-{aw} {away}"+(" (pen "+rec['pen']+")" if g["pen"] else ""))
        # propagate
        if rec["h"]>rec["a"]: w=home
        elif rec["a"]>rec["h"]: w=away
        else: w=home if rec.get("pen")=="h" else away
        ko_w[n]=w; ko_l[n]=away if w==home else home

    print(f"updated: {changed}")
    if changed and not DRYRUN:
        json.dump(pool,open(POOL_PATH,"w",encoding="utf-8"),ensure_ascii=False,indent=2)
        open(POOL_PATH,"a",encoding="utf-8").write("\n"); print("pool.json written")
    elif changed: print("[dry-run] would write")
    return 0

if __name__=="__main__": sys.exit(main())
