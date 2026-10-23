"""Contest-scoped presentation colors; verdict and balloon colors are never theme inputs."""
import re
from core import require
from dashboard_branding import foreground
DEFAULT={'headerColor':'#102b47','primaryColor':'#173f68','accentColor':'#eab746','activeColor':'#244664','hoverColor':'#244664','rowHoverColor':'#edf3f9','backgroundColor':'#f3f6fa','surfaceColor':'#ffffff','textColor':'#172d48','focusColor':'#eab746'}
VARIABLES={'headerColor':'team-navy','primaryColor':'team-primary','accentColor':'team-accent','activeColor':'team-active','hoverColor':'team-menu-hover','rowHoverColor':'team-hover','backgroundColor':'team-background','surfaceColor':'team-surface','textColor':'team-text','focusColor':'team-focus'}
def luminance(color):
 values=[int(color[i:i+2],16)/255 for i in (1,3,5)]
 return sum(w*(v/12.92 if v<=.04045 else ((v+.055)/1.055)**2.4) for w,v in zip((.2126,.7152,.0722),values))
def contrast(a,b):
 x,y=sorted((luminance(a),luminance(b)));return (y+.05)/(x+.05)
def validate(value):
 require(isinstance(value,dict) and set(value)==set(DEFAULT),'Configure all participant theme colors')
 require(all(isinstance(v,str) and re.fullmatch('#[0-9a-fA-F]{6}',v) for v in value.values()),'Use #RRGGBB theme colors')
 result={k:v.lower() for k,v in value.items()}
 require(all(contrast(result['textColor'],result[k])>=4.5 for k in ('surfaceColor','backgroundColor')),'Text must have a contrast ratio of at least 4.5:1 against the page and card backgrounds')
 return result

def variables(value):
 colors=validate(value);out={VARIABLES[k]:v for k,v in colors.items()}
 for name,key in [('header','headerColor'),('primary','primaryColor'),('active','activeColor'),('menu-hover','hoverColor'),('hover','rowHoverColor')]:out['team-on-'+name]=foreground(colors[key])
 # Keep secondary text readable for dark as well as light themes.
 out['team-muted']=colors['textColor'];return out

def css(value):return ':root{'+''.join('--'+k+':'+v+';' for k,v in variables(value).items())+'}\n'
