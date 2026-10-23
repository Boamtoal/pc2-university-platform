"""Discover tools without embedding the developer's installed Java location."""
from pathlib import Path
import os,shutil

def executable(name,environment,preferred=()):
 override=os.environ.get(environment)
 if override:
  path=Path(override).expanduser()
  if not path.is_file() or not os.access(path,os.X_OK):raise RuntimeError(environment+' must point to an executable file')
  return str(path)
 for value in preferred:
  if Path(value).is_file():return value
 found=shutil.which(name)
 if not found:raise RuntimeError('Missing '+name+'. Install it or set '+environment+'.')
 return found

def java_executable():
 home=os.environ.get('LCPC_JAVA_HOME') or os.environ.get('JAVA_HOME')
 if home:
  path=Path(home).expanduser()/'bin/java'
  if not path.is_file():raise RuntimeError('The configured Java home has no bin/java')
  return str(path)
 return executable('java','LCPC_JAVA_BIN',('/Library/Java/JavaVirtualMachines/jdk-25.jdk/Contents/Home/bin/java',))
