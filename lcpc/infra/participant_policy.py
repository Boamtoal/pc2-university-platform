"""Strict single-source C++ and Python uploads, before vendor deserialization."""
import base64,re
PYTHON='Python 3.12 (Isolated Linux ARM64)'
LANGUAGES={'GNU C++17 (Isolated Linux ARM64)','GNU C++20 (Isolated Linux ARM64)',PYTHON}
def submission(data):
 if not isinstance(data,dict) or data.get('isTest',False) is not False:raise ValueError('Only judged submissions are enabled')
 if data.get('language') not in LANGUAGES:raise ValueError('Unsupported language')
 if not isinstance(data.get('probName'),str) or not 1<=len(data['probName'])<=200:raise ValueError('Invalid problem name')
 if data.get('extraFiles') not in [None,[]] or data.get('additionalTestFiles') not in [None,[]]:raise ValueError('This profile accepts one source file')
 f=data.get('mainFile')
 if not isinstance(f,dict) or not isinstance(f.get('fileName'),str):raise ValueError('Invalid source filename')
 name=f['fileName']
 if not 1<=len(name)<=255 or name in ('.','..') or any(c in name for c in ('/','\\')) or any(ord(c)<32 or ord(c)==127 for c in name):raise ValueError('Use a filename without folders or control characters')
 # Browser filenames never become paths or compiler arguments.
 canonical_name='submission.py' if data['language']==PYTHON else 'submission.cpp'
 if not isinstance(f.get('byteData'),str):raise ValueError('Invalid source')
 source=base64.b64decode(f['byteData'],validate=True)
 if not 1<=len(source)<=512*1024:raise ValueError('Source must be 1..512 KiB')
 osname=data.get('osName','')
 if not isinstance(osname,str) or len(osname)>1024 or any(ord(c)<32 for c in osname):raise ValueError('Invalid client platform')
 # The bundled UI sends navigator.userAgent; PC2 expects a short OS name.
 if 'Windows' in osname:osname='Windows'
 elif 'Macintosh' in osname or 'Mac OS X' in osname:osname='Mac OS X'
 elif 'Linux' in osname or 'X11' in osname:osname='Linux'
 return {'probName':data['probName'],'language':data['language'],'mainFile':{'fileName':canonical_name,'byteData':base64.b64encode(source).decode()},'extraFiles':[],'isTest':False,'osName':osname}
