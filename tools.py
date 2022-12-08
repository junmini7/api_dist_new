import re
from datetime import datetime as dt
from datetime import timedelta as td
from datetime import date
from iso639 import languages
import json


def ends_with_jong(kstr):
    k = kstr[-1]
    if "가" <= k <= "힣":
        return (ord(k) - ord("가")) % 28 > 0
    else:
        return


def eun(kstr):
    josa = "은" if ends_with_jong(kstr) else "는"
    return f"{kstr}{josa}"


def yi(kstr):
    josa = "이" if ends_with_jong(kstr) else "가"
    return f"{kstr}{josa}"


def gwa(kstr):
    josa = "과" if ends_with_jong(kstr) else "와"
    return f"{kstr}{josa}"


def eul(kstr):
    josa = "을" if ends_with_jong(kstr) else "를"
    return f"{kstr}{josa}"


def onlyyi(kstr):
    return "이" if ends_with_jong(kstr) else "가"


def onlyeul(kstr):
    return "을" if ends_with_jong(kstr) else "를"


def onlyeun(kstr):
    return "은" if ends_with_jong(kstr) else "는"


def is_valid_login(login):
    return bool(re.match("^[A-Za-z0-9_-]*$", login)) and login and login[0] != '_'


def clear_name(dirty_name):
    new_name = re.sub('[^A-Za-z가-힣]', '', dirty_name)
    # ''.join([j for j in dirty_name.lower() if not j.isdigit() and not j in ['_', ' ']])
    if new_name:
        return new_name
    else:
        return dirty_name


def now():
    return dt.now()


def is_valid_logins(logins):
    for i in logins:
        if not is_valid_login(i):
            return False
    return True


def remove_all(l, x):
    l[:] = list(filter((x).__ne__, l))


def collect_valid_logins(logins):
    valid_logins, invalid_logins = [], []
    for i in logins:
        if is_valid_login(i):
            valid_logins.append(i)
        else:
            invalid_logins.append(i)
    return valid_logins, invalid_logins


def dttoko(ti: dt):
    datedifference = (date.today() - ti.date()).days
    if datedifference < 3:
        datename = ['오늘', '어제', '엊그저께'][datedifference]
    elif datedifference < 10:
        datename = '%d일전' % datedifference
    else:
        datename = str(ti.date())
    ex = '오전'
    ho = ti.hour
    if ti.hour > 12:
        ex = '오후'
        ho = ti.hour - 12
    return '%s %s %d시 %d분' % (datename, ex, ho, ti.minute)


def tdtoko(ti: td):
    ms, s, d = ti.microseconds, ti.seconds, ti.days

    if d > 365.25:
        return f'{int(d / 365.25)}년'
    if d > 365 / 12:
        return f'{int(d / (365 / 12))}달'
    if d > 0:
        return f'{d}일'
    if s > 3600:
        return f'{int(s / 3600)}시간'
    if s > 60:
        return f'{int(s / 60)}분'
    if s > 0:
        return f'{s}초'
    if ms > 1000:
        return f'{int(ms / 1000)}ms'
    return f'{ms}us'


def twitch_parse(t):
    return dt.strptime(t, '%Y-%m-%dT%H:%M:%SZ') + td(hours=9)


def timedelta_to_ko(time_delta):
    return '%d 시간 %d 분 %d 초' % (time_delta.seconds // 3600, (time_delta.seconds // 60) % 60, (time_delta.seconds % 60))


def json_print(data):
    print(json.dumps(data, indent=4, sort_keys=True))


def langcode_to_langname(
        lang):  # {'', 'sv', 'fr', 'uk', 'it', 'zh-hk', 'zh', 'en', 'tl', 'da', 'sk', 'hu', 'ro', 'el', 'ru', 'id',
    # 'no', 'ko', 'pl', 'th', 'de', 'cs', 'ar', 'pt', 'ja', 'es', 'fi', 'tr', 'other'}
    try:
        return languages.get(alpha2=lang).name
    except:
        return 'other'


def langcode_to_country(langcode):
    langname = langcode_to_langname(langcode)
    langtocountry = {'Modern Greek (1453-)': '그리스', 'Tagalog': '타갈로그어권 (필리핀 등지)', 'Swedish': '스웨덴어권',
                     'Spanish': '스페인어권 (남미, 스페인 등지)', 'Chinese': '중국', 'French': '프랑스', 'Polish': '폴란드',
                     'Danish': '덴마크', 'Hungarian': '헝가리', 'Romanian': '루마니아', 'Russian': '러시아', 'Norwegian': '노르웨이',
                     'Japanese': '일본어',
                     'Italian': '이탈리아', 'German': '독일', 'Korean': '한국', 'Ukrainian': '우크라이나', 'English': '영어권',
                     'Indonesian': '인도네시아', 'Arabic': '아랍어권',
                     'other': '기타 국가', 'Turkish': '튀르키예 (터키)'}
    if langname in langtocountry:
        return langtocountry[langname]
    return langname
