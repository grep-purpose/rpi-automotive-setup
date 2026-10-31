#!/usr/bin/env python3
"""MIRA V25: Anrufliste und Kontakte nach dem freigegebenen Mockup."""
from pathlib import Path
from datetime import datetime
import ast
import base64
import copy
import fcntl
import hashlib
import json
import shutil
import subprocess
import sys
import time
import xml.etree.ElementTree as ET
HOME=Path.home()
SKIN=HOME/'.kodi/addons/skin.estuary.custom/xml'
SCRIPTS=HOME/'.kodi/userdata/scripts'
ROOT=HOME/'.cache/mira-phone'
STOP=ROOT/'popup-v11.stop'
BACKUPS=HOME/'.kodi/userdata/mira-backups'
LATEST=BACKUPS/'phone-lists-v25-latest'
ASSETS={'mira/phone-list-v25-outgoing.png': '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', 'mira/phone-list-v25-incoming.png': 'iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAFaUlEQVR4nO2bTYgcRRTH/6+qp3tnsmOikSCCOYgoLEiM+dIQEE8asxCj9GriQQi44kmCBAKydNogbshBJF7innLJoQdBRMRoQCQRE9mYHAzkIB4Ej4lr9qNn+qOeh9nBsDtr7I/pmWnqB3NYZrur5jevql5NvwI0Go1Go9FoNBqNRqPRaDRrwCAwU7+7MXwwk82e7Pxpe7Z02BH97NLwcFfEjc86tTevfbyh23tpKfW34LAjQMSvX3Iefu3qhzOjZN70o4XfDl6f/uLVn9xdIGLHyRaJpZ0PbM+TjYmJ+MD59zZVHnxg1hodeSRc8MEMGFUTKlZR3Az3ejunLnT+N007pRTosCNcctWhi8fuj2uj56VZ2REttgKAK+2PzKFRs8xwKbiJP+Itnn08JCJO01bphvDd8lStft6omjuiRT8GwQQRgUAgMsOlQBmW8YR8VGwlIra9fxeZJJRK4Ep5slrZEdzxI5DoKoeEgAJqWdo0slw8SKwlj4hWf0ZmJU2Dw2Z4G3LpFzCoAVulabcUEZhQHoOIrfU1CVZuY/vJv+2GJ5ByDhz6CEwsTwiWIxXp37pzpPGM82n7+nQrMDDkq3BSeSSFklVThov+ZGPX8ZnO9Vn6kE8EMghgpB0GaUgtb96fbDx7fGZy9kzFpbfDrP3INgd29pgEBhEXtcfMKu85/t74bHt2eUCWIcxMnYgbn3VqG+UG8+zWI3Mr38ubPOT9QM9HefUnXbQsC+rlHrMbgyYPSBOBy79gHLj6/kMm1S6bo9XNvdhjrmQQ5QEpItBGQ4CIjdA6Ydarm5t/LbRUGDNHisN5PyDAYMWn7V8d07PTJacrGVR5QFKBzNSgifjwpaN1CBoP5n0mdN9jwsdTWfaYHQZZHpByDmyyNEAw2unLakgKEkLUs3Vt8OUBSQUSscOOOLdneg4x3zBGKgCh+zAVItPcNwzygLSrMIEJ9J+d41ilTpGGRR6QIZHmHm0Dh0keMGC/xgybPGCABA6jPGBABA6rPGAABA6zPKDPAoddHtBHgWWQB/RJYFnkAX0QWCZ5QMECyyYPKFBgGeUBBQksqzygEIE3ZFnlAb1+sM6gBrlBWeUBPYxAZhgg8MvfHdtYVnlAjyKQBAEtLIzPOrURMr+V1crTZZQH9CACCUwqjFkY2FSN5VfGqFVaeUAvIlAQRa1IEXDWGKmsb91eVCTKKQ/ohUAGiCBIyvWRHyoStDrKSyIP6OUiEsVM1OX+JZIH9DIPJFr9zKSLvG2zZyqp5Q3AyaPiCizb8shYZ8lgbvGdxm535sWvP7Hqv1+IxlNWdLVr+wi2Z8sxe4yz1vqloSiBDCFYmIYfzC2+1djtngOAb156t5XlpkVWha1FYRFIgkS0FEQk5aGJKx9MMqDWeCR/bwQABSDix5q8sO7g9emLgd/66HOiK47jCNctLhKLEkgcKQhD3Gess/ZB5RMkcRCBFUNUxH5TWPsmfj6x1825KuxeZBGY7FsmgBVzOO/nFh0MImJQOO+HRs0yWfFp23O2eLYdFrWyJK7Ocsnlw5eO1kF4PA4igBPdgwCSeb0IEHmfPEpKmtWP29VZVOc4p7GYE3mcPEpK4uos27PluT3Tc8R82ahZBCCXYu1MMMfSlBw2w1uM5ZNHORV33ovEEThmjzEILCieioNYGTXLZIbq54sMKfM6eZSUdHPtcr71yo9TL5i1kVMAPSlknx4xty3+qcL4pLdz6rSjsh+eSUL6Gr5OvuU44o391jYmHo1aUXGJUYR2W2TGTf/2tS/3nJrH8mHggnqQHduzC1np/g9FrborySNdItuzBWDncKt0NGxbFb2F02g0Go1Go9FoNBrN0PIPV3x45c0KuUYAAAAASUVORK5CYII=', 'mira/phone-list-v25-missed.png': 'iVBORw0KGgoAAAANSUhEUgAAAFAAAABQCAYAAACOEfKtAAAJ9UlEQVR4nO2cXWxjRxXH/2fmftiOvfnwdmm3sJUotGIlxEdbkHhg06ftqis+Hu5Ck4VCSG5ZoYJAogiqymsVURBPaCtVONuiom1a5QpphXgoFVKJitQWtvBSUtRthSoILe0mcTYftu+dmcOD7Y2TzZcT29kY/yVLsZy51/PTmXPOnDnXQEcdddRRR20jBogBavXYthB7nqz9ux4YOxnbVpo67if43u/0VN/XA2L12K2oLSgzM+H0aZp9c+pHFsn7mJEQAufn2Hrgxg/unwUAymbNVeMAgucJBONm9uR9D1pE5bHA+cuaf3Dw6dw0ABDA691bNG9arRF7niQinn7jPz/sTaQeZub3a+a+pBsfSpjoGcpmDSYn1/Ztvm9REOhL9wxneuNdDzOjPDYeH3LIPHU6kyFkMhsa2Z62QAaIAH5taCh1oCQvOlLuL2kNlA0j6nEcZyGKRnvO5Xz2PIkgMFVr4kzGomxWvTswPJKy7VxB6ciwkSAiYlZxy7aXIvPp/U//8s/seZKCQK/1Hfa8BQJAouhaxBzXzAAgqAzWyYeh7nbckfxJP0dBoOF5ggGqhdfjOLmiUsaALSISBJABSBJBsk5udu89DZAAZs+Th8Yey2ui892xuAQ4qvlcThcLqttxR2aqEH1/BbxFpbRiJqqsRsOs0rGYtaiii0Wr+DIzE4LgKv9ZldWKiTZVlck5wvnefKHwvh7HPToXhgqVuRGRNV0sqHQ8PjIzOCIolxueHhgeSTlublFFWhkjBFEVnt5nO1ZB6YsaGLzh3LlFvvlmQcC6APe0D6yq6gsBIH/Sz3U77sh0saCIqNZAdNK25XwY/hHAZy0hKDIGNfBUrxuzllT0l3xR3XUoeHyGMxmxVvSuVVsABADOZAQmJ4mCQK8HkZlN0nbEoorAYFBl+rXwZrU4etPYY7MbBY5atQ1AYDmvoyDQMyf9XK/jjsyUihqArPkfjUqgAQDDbPrcmFisgTfuefLEFuABbQYQWAkxP+ifjdvWN+bD0BDRVQGTmU3CsoUy5kK+pI4eCh6fqQce0IYAgQpE37col4umB0ae77Lt/gUVaVppiWwTQRK9+4/izK23B8Hc80eOWHdOTKh67rWn05h1lclIyuWi9waG/YQlb19SkcGquRJAipkFifTNTs9PAaC/v9/UW0RoOwtcmSS7uSUVQTFz1ecxmAl0Zd4McDoWp9lScbRvjR3LZmorgOz7NuVy0YokuSbPY2ZjSykirZmoBiKzSsfi1lxYWt72HT7Mm6UwQBsBrOZs5ST5aniGjemyHbEURdOutNKhUQZYDiyrIQIr88v11BYAOZMRADD75tsPxaQ8XVLKKGaqTZL73Jg1H4WvREp9jqR8KB2Lf3O6sLQyTwSrXidmLSo1Pq/Mtw6O5aZBG5ez9jzAasJ7aXDkwXQi+eOZpQXFgKzd267eYQDAzKCf63XXTLajdFeXfWlx8blHP3zjsdNYu5ZY1Z4GyACBGRdPfjuVRvH1cjlLEVWWpmHWvW5M1u4wnj9yxOrv7zeUzZorO5ZSUVFtXYA5amk5azcOYxhMOHJEEhFrd5EJ3KWZJbC8bFO2swLeuOfJOycmFLJZZs+TPedy/lxYGu11XIt5uYrTsnIWg4k9TxLA1dJS1R81U2XnTkwTE4qHvp+6XmtpGL/eZ9vlUFvxeaHR/7yyt81kRHWHQQAjCMwyxPA36USXzcyKmaP9sXjzy1nVSSCAZt9PoBR36Mlf5Jc/21oeVfd9K9H2rS8PHeyz7ex8dPkuNo4rBV6fK5XeFUTppO1YodavLkTR12965olyYSCbXbEECWA+fJg5kxH/mvy3b4tiImHbxyQIBaVe1cBQ08pZVUDVSTBwVBtOxCz5p3yp+MgNz/zq5a2Uguq+b8UXvfHFkweu60pc2Oe6H7gchgAAhwQAXlhU+ieuLV58+79vvXjLs8+WNvseK0phX73vUxKi68Jbky/cOTGhmpLGVH3de4P+9S7RS/tc59B8GMIwI2nZiNioUqSO9YyN/mGrJaEt3bdqeQOnenul+b0r5R3zURQCbJdjCetux7EuR+Er+586e3vtmK3NiUGgK7C2OrZ+fzU+Lso+jx/e57qHLhUKpdBoVsycj8KQQJYmPvOql3EwPt4QC1wNL2HZd1wOQ02AQyAigASRdTkMTZdl3zb9pZHPACBMTm7JQMrzIR73PFk9VN/q6qkLIANEJ07o14aGUgJ8fD4sMRFdmQQBzkIUmpi0br3eeufjRMS1J/7b0VrwZktFJYjWuS6xkORiGz74RBBoCgJdj//eVsRMFF0LDGu91EWSICk4tZ1r12oDeFcFP2Y2rmXxkgqnOcJfGdgwejZKdQEkgDmTEYfGHssbwt/jUgLrRijake+rCx7AIOKk40o2lO0LcnPwPNGsTKBW27LAis/YuPDIvO3Euh54hpkFwEnLlvlC4bv7nx59lDMZ0ajgtZl2cKy5fUAbXrVOeJYQpsuy5HwY+umxs6PNSJ820jVVkd4uvHwVnu/brYQHXEMAdwLvQNnyLMrlorWu3UxdEwAbAi+breswqFHadYB7GR6wywD3OjxgFwG2AzxglwC2CzxgFwC2EzygxQDbDR7QQoDtCA9oEcB2hQe0BqBsV3hAkwEyQBQEYbvCA5oIkIS2CODJL3wl3a7wgCZ16QsiaM0LU8f9RCpFzyUs+5PtCA9ohgUSKDKaDYkDsW78LmU7bQsPaIIFChAVlDJEeDIuZfel4pIRJNoSHtAEgAyAiIQk6l5SkREkrrLydoEHNDGIKGZeqzO+neABzYzCaxx5LsOz5XwF3oVyGX5b8K6FR/Rb9qwcA2wLQUnblrOl0qnrxs6O8v33u8E776jtdnRVzz/q6WlutFoCkAEWALtCFmZLxZHrxh4fAwA6c6a0k+tOHfcTB9Ot6QpbTy2zQEEkFlSkCDQwPTjs8wYtY5uJUKXEH8rrQlfh3lMv5EvFR6hJXWEbqSUAKw+1wBZiX9K27zbcGCMpaQPNBjaJz/e4sbvzAyPHKJttaFfYZto+QK7PggjlyJwPw4ZZBzETE1E+CqOkbTuq3BX2MYyfjmqepWmq6u7OQjbLrw0NpUC4pWRMXdeodHDJRr1QeUSfAGchrHSFybc/0YiusK2q7uhHAJd/owApzQ1aiw2SJAEpkGjlPevvzqr8RgETvZS0LALQ8m6A1WJA70ZrG7CdRPrw4XJHvqCHSkqbpGU55cb43XkZZmOTkLvR2gbssMl86p7ho92W9XMQPmqRWPEYfavEYGiDqdDon/U9lTvT6jRmxz18GUA88LVTtwmD5ILSrf0ZEAuQgJ7Kq7995LdPzO9GIr0jjbco0m1FrYq6q7Xj9cYABZ4nvEZ8m+2qjgekO+qoo4466qijjjrqqKOOOvq/1/8APKrAoy9+134AAAAASUVORK5CYII=', 'mira/phone-list-v25-person.png': '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', 'mira/phone-list-v25-search.png': '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', 'mira/phone-list-v25-focus.png': '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JswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAmJswAAAAm9oRhNp/v9A/7QgAAAH4cVNX39NaQJFcuXaykKqlOpTab1Xyx2BVnAAAAP0CbzXoYx3Feqe5O9bgdkmTo7vqz4/PLPfb/STKk+/bMxhdvelivh6Emvm4AAIDnvKGqFocOb7bJbam8JN1d1Y9me/hPkmQ4c+bMsH/ixCapP0sySzLPtl+0Wm/HaS8dAADg+WPMsOle3ZnuY+lUJ9++cOgF306S4fjx45Ukw2z4w6QrqepheNXueLGH9crEDAAA4FnabjdDzw9f685PpXMsVbOq+tLfP/Gyg+VyORvuvvvuMUm24/aPurPq5Folr91s6kU1X6yGKnEGAADwLIxj9+7qyqIqJ5LaJJlX14NJcvz48Rqqauzu2p6/7StJvjx0ZmOPL+ps78ri2JXtdmNLfQAAgGdoO5sNtThy9WB9+eVJfqaTdafPZ8y5JDl37tw4JMmZMxlOnfrp1TCb/btOH6rOQXfeub3y7aM1zLamZgAAAM/MsF7Vkfnha+M43tfp3UpuyVAfe+fb7/pfy+Vytr+/fz3MTp68PjVbP/K1T6byx6lUql+R7erdhxa3XegeZ1PfDAAAwHPNOj3fnR+9cOnSN96S7renczWVS/Nx+LdJcvLkyU5uvMesKn19anZqNavZbyZ9a499PpX3Xrn4zZ9dL+aPVHo+5Q0BAAA8l/Q4n82G3csHBxf/alW9L1WrqtxR6d95x1vf8D+Xy+WsqsYk+a4lisvlcvbwwyf7b77pgV/v7l+sqkeTXqdn79ssjj50KAe39/UH1QAAAHgS6/R8NuxervX62Ha8+q+SekU6qeqvLVbjfV/4wpvPnz6drqpOHhdm3V1J8qlPff7Y1fn2Y0l+Mp1VVQ4qwz89csvxB1frC7dtt5uhhtl2gvsDAAD4kbXdbIbh8KHa3e5c2GwO/spqe/VfpvPKqrrU6cPzzfAL77j3roe6e7g5LUtuLGW86Uat1b33vuHCfDv+SqXOV2renZ2u/o3LV775nlXPrmb32MUk6XE72242g81BAACAH0frddVQVTfbqBZHrh6uW759sLr0xvXm6r8fUq+oqktJbk3nfe+4966HlsuePTbKksdNzG5aLpezU6dObT98/2d/OpUPVupFSc6ncmuP/YWq4T8uDt/yX7fXcnncOVgMWcxz40J+GDcPAAAwtZ2dnb623mwXh45sjszHaxdXtaj1tZeP4+q+St52fVv87FSnUvkn7/o7bzyzd/bsfP/Eie95POxJJ1034+zjZx984Xp97f2VeluS85XMOz2k6isZ83tVs4fS+cZwaPf8sO7VbDaYngEAAM9rV5PsbNbDNrmte7yze/NTVTnR3a+uyqI7V4eq2zv58lD9a79wz5u+ePbs2fmJJ4iy5CnCLEkeu+7xdz7zwD/q7vcm/eJOXa5OJdlN5WoqF9P99aQuV5WpGQAA8LzW3d2deQ15STrH0n0sySZVq3QfraEudtcnjtXOv7jnntecvzn4erLz/aXTrZsbglRVf+Qzn39BevOeTv5uJS/pZKxkk06nKp0e0k/nrAAAAM9RN5qnkk6nrwdQzzs1T/p8Kp+o9faD7/r5t3wlSfa6h/3HPVP2eE87oR5beB//+NkXbg7t/u1Ov6a6XpXq453cUV1D6nqmPZv7BAAA+JFW3dffCN3nU/Vodz9cQx4cs3PuF+953VeT6w118uTJ8eaW+E95uu/nu7u7zpw5Mzx2BLdcLme59aW37dTwskrPx+6OV1EDAADPZ5ukh+2Q7eE/ufPQxW+fOHHi4OZH3T2cPn06+/v7Tzkle6zvK6FulN72eqBlSM7kRqQ9cuMHAADgx85yuZwdP368zp07Nz5+K/yn4/8B4dYDwILtaj4AAAAASUVORK5CYII='}
ROW_HELPER="def _mira_phone_row_v25(mode, record):\n    numbers=record.get('numbers',[])\n    if mode=='calls':\n        kind=record.get('kind','Anruf') or 'Anruf'\n        icon={'Ausgehend':'outgoing','Eingehend':'incoming','Verpasst':'missed'}.get(kind)\n        stamp=str(record.get('time','') or '').strip()\n        right=stamp\n        parts=stamp.rsplit(' ',1)\n        if len(parts)==2:\n            date=parts[0].split('.')\n            if len(date)==3 and all(x.isdigit() for x in date):\n                right='%s.%s. · %s'%(date[0],date[1],parts[1])\n        return ('mira/phone-list-v25-'+icon+'.png' if icon else 'mira/phone-footer-v17-receiver.png'),kind,right\n    if len(numbers)==1:\n        number=numbers[0]\n        left=str(number.get('display') or number.get('number') or '')\n        right=str(number.get('label') or 'Telefon')\n    elif len(numbers)>1:\n        left='%d Rufnummern'%len(numbers);right='Auswählen'\n    else:\n        left='Keine Rufnummer';right=''\n    return 'mira/phone-list-v25-person.png',left,right\n"

MARKER='MIRA_PHONE_LISTS_V25'
NAME_FONT='MiraPhoneListNameV25'
DETAIL_FONT='MiraPhoneListDetailV25'

def put(node,key,value):
    child=node.find(key)
    if child is None:child=ET.SubElement(node,key)
    child.text=str(value)
    return child

def make(parent,kind,**values):
    node=ET.SubElement(parent,'control',{'type':kind})
    for key,value in values.items():put(node,key,value)
    return node

def patch_fonts(source):
    root=ET.fromstring(source,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)));sets=root.findall('fontset')
    if not sets:raise RuntimeError('Keine Schriftsets vorhanden.')
    for fontset in sets:
        if any(n.findtext('name') in (NAME_FONT,DETAIL_FONT) for n in fontset.findall('font')):
            raise RuntimeError('V25-Schriften existieren bereits.')
        base=[n for n in fontset.findall('font') if n.findtext('name')=='font45']
        if len(base)!=1 or base[0].findtext('size')!='45':raise RuntimeError('Unerwartete Schriftgrundlage.')
        for name,size,bold in ((NAME_FONT,52,True),(DETAIL_FONT,36,False)):
            node=copy.deepcopy(base[0]);put(node,'name',name);put(node,'size',size)
            for child in node.findall('style'):node.remove(child)
            if bold:put(node,'style','bold')
            fontset.append(node)
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def patch_ui(source):
    if MARKER in source:raise RuntimeError('V25 ist bereits installiert.')
    tree=ast.parse(source)
    renders=[n for n in tree.body if isinstance(n,ast.FunctionDef) and n.name=='render']
    if len(renders)!=1:raise RuntimeError('Listenaufbau ist nicht eindeutig.')
    render=ast.get_source_segment(source,renders[0])
    if "Container(50).CurrentItem" not in render or "MiraPhoneKey" not in render:
        raise RuntimeError('Erwartete Container-Auswahl fehlt; nichts geändert.')
    old="        item=xbmcgui.ListItem(label=record['name'],label2=detail)"
    addition="\n        row_icon,row_left,row_right=_mira_phone_row_v25(mode,record)\n        item.setProperty('MiraPhoneRowIcon',row_icon)\n        item.setProperty('MiraPhoneRowLeft',row_left)\n        item.setProperty('MiraPhoneRowRight',row_right)"
    if render.count(old)!=1:raise RuntimeError('Datensatzaufbau hat einen unbekannten Stand.')
    render=render.replace(old,old+addition,1)
    az="        item.setProperty('MiraPhoneAction','az');items.append(item)"
    if render.count(az)!=1:raise RuntimeError('A-Z-Eintrag hat einen unbekannten Stand.')
    render=render.replace(az,"        item.setProperty('MiraPhoneAction','az')\n        item.setProperty('MiraPhoneRowIcon','mira/phone-list-v25-search.png')\n        item.setProperty('MiraPhoneRowLeft','Alphabet öffnen')\n        items.append(item)",1)
    old_render=ast.get_source_segment(source,renders[0])
    source=source.replace(old_render,ROW_HELPER+'\n'+render,1)
    source='# '+MARKER+'\n'+source
    ast.parse(source);return source

def patch_phone(source):
    if MARKER.encode() in source:raise RuntimeError('V25 ist bereits installiert.')
    root=ET.fromstring(source,parser=ET.XMLParser(target=ET.TreeBuilder(insert_comments=True)))
    if root.get('id')!='1189':raise RuntimeError('Unerwartetes Telefonfenster.')
    lists=root.findall(".//control[@id='50']")
    if len(lists)!=1 or lists[0].get('type')!='list':raise RuntimeError('Telefonliste nicht eindeutig.')
    listing=lists[0]
    expected=dict(left='75',top='250',width='857',height='640')
    if any(listing.findtext(k)!=v for k,v in expected.items()):raise RuntimeError('Listengeometrie unterscheidet sich von der Diagnose; nichts geändert.')
    if listing.findtext('onclick')!='RunScript(/home/pi/.kodi/userdata/scripts/mira_phone_ui.py,select)':
        raise RuntimeError('Abweichende Auswahlaktion; nichts geändert.')
    for tag in ('itemlayout','focusedlayout'):
        node=listing.find(tag)
        if node is None or node.get('height')!='110':raise RuntimeError('Unerwartetes Listenlayout.')
    for key,value in dict(left=70,top=245,width=870,height=750).items():put(listing,key,value)
    for tag in ('itemlayout','focusedlayout'):
        old=listing.find(tag);position=list(listing).index(old);listing.remove(old)
        layout=ET.Element(tag,{'width':'870','height':'150'});listing.insert(position,layout)
        if tag=='focusedlayout':
            make(layout,'image',left=0,top=3,width=870,height=144,texture='mira/phone-list-v25-focus.png',visible='Control.HasFocus(50)')
        has_icon='!String.IsEmpty(ListItem.Property(MiraPhoneRowIcon))'
        make(layout,'image',left=20,top=35,width=80,height=80,aspectratio='keep',texture='$INFO[ListItem.Property(MiraPhoneRowIcon)]',visible=has_icon)
        make(layout,'label',left=120,top=9,width=730,height=65,font=NAME_FONT,textcolor='FFF0F2F5',aligny='center',scroll='true' if tag=='focusedlayout' else 'false',label='$INFO[ListItem.Label]',visible=has_icon)
        make(layout,'label',left=120,top=78,width=380,height=50,font=DETAIL_FONT,textcolor='FFCAD1DA',aligny='center',scroll='false',label='$INFO[ListItem.Property(MiraPhoneRowLeft)]',visible=has_icon)
        make(layout,'label',left=510,top=78,width=340,height=50,font=DETAIL_FONT,textcolor='FFCAD1DA',align='right',aligny='center',scroll='false',label='$INFO[ListItem.Property(MiraPhoneRowRight)]',visible=has_icon)
        make(layout,'label',left=24,top=9,width=822,height=125,font=DETAIL_FONT,textcolor='FFCAD1DA',aligny='center',scroll='true',label='$INFO[ListItem.Label]',visible='String.IsEmpty(ListItem.Property(MiraPhoneRowIcon))')
    root.append(ET.Comment(MARKER))
    ET.indent(root,space='    ')
    return ET.tostring(root,encoding='utf-8',xml_declaration=True)

def quiet():
    result=subprocess.run(['/usr/bin/python3',str(SCRIPTS/'mira_phone_call_backend.py')],input='{"action":"status"}',capture_output=True,text=True,timeout=25)
    try:status=json.loads(result.stdout)
    except ValueError:status={}
    if not status.get('ok'):raise RuntimeError('Anrufstatus konnte nicht sicher geprüft werden; nichts geändert.')
    if status.get('calls'):raise RuntimeError('Bitte laufenden Anruf oder Simulation zuerst beenden.')
    ROOT.mkdir(parents=True,exist_ok=True,mode=0o700);STOP.write_text('stop')
    lock=None
    try:
        subprocess.run(['kodi-send','--action=Dialog.Close(1190)'],capture_output=True,check=False)
        subprocess.run(['kodi-send','--action=ActivateWindow(Home)'],capture_output=True,check=True)
        lock=(ROOT/'call-watch.lock').open('a');deadline=time.monotonic()+35
        while True:
            try:fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB);return lock
            except BlockingIOError:
                if time.monotonic()>=deadline:raise RuntimeError('Anrufbeobachter konnte nicht angehalten werden. Keine Dateien geändert.')
                time.sleep(0.2)
    except Exception:
        if lock is not None:lock.close()
        STOP.unlink(missing_ok=True);raise

def start():subprocess.run(['kodi-send','--action=RunScript(%s)'%(SCRIPTS/'mira_phone_call_watch.py')],check=False)

def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None

def reload():subprocess.run(['kodi-send','--action=ReloadSkin()'],check=False)

def install():
    phone_path=SKIN/'custom_MiraPhone.xml'
    ui_path=SCRIPTS/'mira_phone_ui.py'
    fonts_path=SKIN/'Font.xml'
    changes={phone_path:patch_phone(phone_path.read_bytes()),
             ui_path:patch_ui(ui_path.read_text()).encode(),
             fonts_path:patch_fonts(fonts_path.read_bytes())}
    for relative,encoded in ASSETS.items():
        path=SKIN.parent/'media'/relative
        if path.exists():raise RuntimeError('Neue Buttontextur existiert bereits: '+str(path))
        data=base64.b64decode(encoded,validate=True)
        if not data.startswith(b'\x89PNG\r\n\x1a\n'):raise RuntimeError('Ungültige Grafik.')
        changes[path]=data
    folder=BACKUPS/('phone-lists-v25-'+datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
    folder.mkdir(parents=True,mode=0o700);records=[]
    for i,(path,data) in enumerate(changes.items()):
        before=digest(path);saved=str(i)+'.bak'
        if before is not None:shutil.copy2(path,folder/saved)
        records.append(dict(path=str(path),before=before,backup=saved,after=hashlib.sha256(data).hexdigest()))
    (folder/'manifest.json').write_text(json.dumps(records,indent=2))
    lock=quiet()
    try:
        try:
            for path,data in changes.items():
                path.parent.mkdir(parents=True,exist_ok=True)
                temp=path.with_suffix('.v25.tmp');temp.write_bytes(data);temp.replace(path)
        except Exception:
            for item in records:
                path=Path(item['path'])
                if item['before'] is None:path.unlink(missing_ok=True)
                else:shutil.copy2(folder/item['backup'],path)
            raise
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    LATEST.unlink(missing_ok=True);LATEST.symlink_to(folder.name)
    reload();print('V25 installiert: Anrufliste und Kontakte mit klarer Typografie, Symbolen und gerahmter Auswahl.')
    print('Backup: '+str(folder));print('Keine Anrufe gestartet oder verändert. Uhrzeit, Empfang und Akku bleiben an ihrem Platz.')

def rollback():
    folder=LATEST.resolve(strict=True);records=json.loads((folder/'manifest.json').read_text())
    for item in records:
        if digest(Path(item['path']))!=item['after']:raise RuntimeError('Datei inzwischen geändert: '+item['path'])
    lock=quiet()
    try:
        for item in records:
            path=Path(item['path'])
            if item['before'] is None:path.unlink(missing_ok=True)
            else:shutil.copy2(folder/item['backup'],path)
    finally:
        lock.close();STOP.unlink(missing_ok=True);start()
    reload();print('V25 zurückgenommen; vorherige Listenansicht wieder aktiv.')

def backup_git():
    repo=HOME/'rpi-automotive-setup'
    def git(*args):return subprocess.run(['git','-C',str(repo),*args],check=True,capture_output=True,text=True)
    if git('branch','--show-current').stdout.strip()!='main':raise RuntimeError('Nicht auf main.')
    git('fetch','origin');git('merge-base','--is-ancestor','origin/main','HEAD')
    mappings=[(SKIN/name,'mira/skin.estuary.custom/xml/'+name) for name in ('custom_MiraPhone.xml','Font.xml')]
    mappings += [(SCRIPTS/'mira_phone_ui.py','mira/userdata/scripts/mira_phone_ui.py')]
    mappings += [(SKIN.parent/'media'/relative,'mira/skin.estuary.custom/media/'+relative) for relative in ASSETS]
    mappings += [(Path(__file__).resolve(),'tools/mira_phone_lists_v25.py')]
    paths=[r for s,r in mappings];status=git('status','--porcelain','--',*paths).stdout
    if status.strip():raise RuntimeError('Exportziele haben lokale Änderungen:\n'+status)
    for source,relative in mappings:
        target=repo/relative;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target)
    git('add','--',*paths)
    result=subprocess.run(['git','-C',str(repo),'diff','--cached','--quiet','--',*paths])
    if result.returncode==1:print(git('commit','--only','-m','MIRA: Anrufliste und Kontakte im einheitlichen OEM-Stil','--',*paths).stdout)
    elif result.returncode:raise RuntimeError('Git-Diff fehlgeschlagen.')
    result=git('push','origin','main');print(result.stdout+result.stderr);print('GitHub-Sicherung abgeschlossen.')

if __name__=='__main__':
    try:
        if len(sys.argv)==1:install()
        elif sys.argv[1:]==['--rollback']:rollback()
        elif sys.argv[1:]==['--backup-git']:backup_git()
        else:raise RuntimeError('Optionen: --rollback oder --backup-git')
    except Exception as error:raise SystemExit('Abgebrochen: '+str(error))
