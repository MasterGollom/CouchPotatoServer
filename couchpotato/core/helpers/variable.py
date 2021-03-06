from couchpotato.core.helpers.encoding import simplifyString, toSafeString, ss
from couchpotato.core.logger import CPLog
import collections
import hashlib
import os
import platform
import random
import re
import string
import sys

log = CPLog(__name__)

def fnEscape(pattern):
    return pattern.replace('[','[[').replace(']','[]]').replace('[[','[[]')

def link(src, dst):
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.kernel32.CreateHardLinkW(unicode(dst), unicode(src), 0) == 0: raise ctypes.WinError()
    else:
        os.link(src, dst)

def symlink(src, dst):
    if os.name == 'nt':
        import ctypes
        if ctypes.windll.kernel32.CreateSymbolicLinkW(unicode(dst), unicode(src), 1 if os.path.isdir(src) else 0) in [0, 1280]: raise ctypes.WinError()
    else:
        os.symlink(src, dst)

def getUserDir():
    try:
        import pwd
        os.environ['HOME'] = pwd.getpwuid(os.geteuid()).pw_dir
    except:
        pass

    return os.path.expanduser('~')

def getDownloadDir():
    user_dir = getUserDir()

    # OSX
    if 'darwin' in platform.platform().lower():
        return os.path.join(user_dir, 'Downloads')

    if os.name == 'nt':
        return os.path.join(user_dir, 'Downloads')

    return user_dir

def getDataDir():

    # Windows
    if os.name == 'nt':
        return os.path.join(os.environ['APPDATA'], 'CouchPotato')

    user_dir = getUserDir()

    # OSX
    if 'darwin' in platform.platform().lower():
        return os.path.join(user_dir, 'Library', 'Application Support', 'CouchPotato')

    # FreeBSD
    if 'freebsd' in sys.platform:
        return os.path.join('/usr/local/', 'couchpotato', 'data')

    # Linux
    return os.path.join(user_dir, '.couchpotato')

def isDict(object):
    return isinstance(object, dict)

def mergeDicts(a, b, prepend_list = False):
    assert isDict(a), isDict(b)
    dst = a.copy()

    stack = [(dst, b)]
    while stack:
        current_dst, current_src = stack.pop()
        for key in current_src:
            if key not in current_dst:
                current_dst[key] = current_src[key]
            else:
                if isDict(current_src[key]) and isDict(current_dst[key]):
                    stack.append((current_dst[key], current_src[key]))
                elif isinstance(current_src[key], list) and isinstance(current_dst[key], list):
                    current_dst[key] = current_src[key] + current_dst[key] if prepend_list else current_dst[key] + current_src[key]
                    current_dst[key] = removeListDuplicates(current_dst[key])
                else:
                    current_dst[key] = current_src[key]
    return dst

def removeListDuplicates(seq):
    checked = []
    for e in seq:
        if e not in checked:
            checked.append(e)
    return checked

def flattenList(l):
    if isinstance(l, list):
        return sum(map(flattenList, l))
    else:
        return l

def md5(text):
    return hashlib.md5(ss(text)).hexdigest()

def sha1(text):
    return hashlib.sha1(text).hexdigest()

def isLocalIP(ip):
    ip = ip.lstrip('htps:/')
    regex = '/(^127\.)|(^192\.168\.)|(^10\.)|(^172\.1[6-9]\.)|(^172\.2[0-9]\.)|(^172\.3[0-1]\.)|(^::1)$/'
    return re.search(regex, ip) is not None or 'localhost' in ip or ip[:4] == '127.'

def getExt(filename):
    return os.path.splitext(filename)[1][1:]

def cleanHost(host, protocol = True, ssl = False, username = None, password = None):

    if not '://' in host and protocol:
        host = 'https://' if ssl else 'http://' + host

    if not protocol:
        host = host.split('://', 1)[-1]

    if protocol and username and password:
        login = '%s:%s@' % (username, password)
        if not login in host:
            host.replace('://', '://' + login, 1) 

    host = host.rstrip('/ ')
    if protocol:
        host += '/'

    return host

def getImdb(txt, check_inside = False, multiple = False):

    if not check_inside:
        txt = simplifyString(txt)
    else:
        txt = ss(txt)

    if check_inside and os.path.isfile(txt):
        output = open(txt, 'r')
        txt = output.read()
        output.close()

    try:
        ids = re.findall('(tt\d{4,7})', txt)

        if multiple:
            return list(set(['tt%07d' % tryInt(x[2:]) for x in ids])) if len(ids) > 0 else []

        return 'tt%07d' % tryInt(ids[0][2:])
    except IndexError:
        pass

    return False

def tryInt(s, default = 0):
    try: return int(s)
    except: return default

def tryFloat(s):
    try:
        if isinstance(s, str):
            return float(s) if '.' in s else tryInt(s)
        else:
            return float(s)
    except: return 0

def natsortKey(s):
    return map(tryInt, re.findall(r'(\d+|\D+)', s))

def natcmp(a, b):
    return cmp(natsortKey(a), natsortKey(b))

def toIterable(value):
    if isinstance(value, collections.Iterable):
        return value
    return [value]

def getTitle(library_dict):
    try:
        try:
            return library_dict['titles'][0]['title']
        except:
            try:
                for title in library_dict.titles:
                    if title.default:
                        return title.title
            except:
                try:
                    return library_dict['info']['titles'][0]
                except:
                    log.error('Could not get title for %s', library_dict.identifier)
                    return None

        log.error('Could not get title for %s', library_dict['identifier'])
        return None
    except:
        log.error('Could not get title for library item: %s', library_dict)
        return None

def possibleTitles(raw_title):

    titles = [
        toSafeString(raw_title).lower(),
        raw_title.lower(),
        simplifyString(raw_title)
    ]

    # replace some chars
    new_title = raw_title.replace('&', 'and')
    titles.append(simplifyString(new_title))

    return list(set(titles))

def randomString(size = 8, chars = string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for x in range(size))

def splitString(str, split_on = ',', clean = True):
    list = [x.strip() for x in str.split(split_on)] if str else []
    return filter(None, list) if clean else list

def dictIsSubset(a, b):
    return all([k in b and b[k] == v for k, v in a.items()])

def isSubFolder(sub_folder, base_folder):
    # Returns True if sub_folder is the same as or inside base_folder
    return base_folder and sub_folder and os.path.normpath(base_folder).rstrip(os.path.sep) + os.path.sep in os.path.normpath(sub_folder).rstrip(os.path.sep) + os.path.sep
