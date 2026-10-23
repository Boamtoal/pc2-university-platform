"""PDF renderer, run with the bundled document runtime."""
import json,sys
from pathlib import Path
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,PageBreak,KeepTogether,CondPageBreak
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.pagesizes import A4,landscape

def render(data,path):
 font=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
 if font.exists():pdfmetrics.registerFont(TTFont('ReportUnicode',str(font)));face='ReportUnicode'
 else:face='Helvetica'
 styles=getSampleStyleSheet();styles.add(ParagraphStyle(name='Cell',fontName=face,fontSize=8,leading=11,wordWrap='CJK'));styles.add(ParagraphStyle(name='SmallReport',fontName=face,fontSize=9,leading=14,textColor=colors.HexColor('#53677c')))
 styles['Title'].fontName=face;styles['Heading2'].fontName=face
 navy=colors.HexColor('#102b47');teal=colors.HexColor('#126f73');story=[];s=data['snapshot'];page=landscape(A4);width=page[0]-72
 header=ParagraphStyle('Header',parent=styles['Cell'],textColor=colors.white)
 labels={'login':'Account','name':'Name','enabled':'Login enabled','visible':'Visible','letter':'Letter','timeLimit':'Time limit (s)','memoryLimit':'Memory (MiB)','tests':'Tests','active':'Active','site':'Site','number':'Run / ID','teamName':'Team','problem':'Problem','language':'Language','elapsedMinutes':'Contest min','verdict':'Verdict','final':'Final','team':'Team','question':'Question','answer':'Answer','filename':'File','kind':'Type','published':'Published','deleted':'Removed','created':'Time','actor':'Actor','event':'Event','outcome':'Outcome'}
 def para(v,head=False):return Paragraph(escape(str(v if v is not None else '')).replace('\n','<br/>'),header if head else styles['Cell'])
 def section(title,cols,rows):
  gap=Spacer(1,6);gap.keepWithNext=True;story.extend([CondPageBreak(110),Paragraph(escape(title),styles['Heading2']),gap])
  if not rows:story.extend([Paragraph('No records.',styles['SmallReport']),Spacer(1,12)]);return
  table=LongTable([[para(labels.get(c,c),True) for c in cols]]+[[para(r.get(c,'')) for c in cols] for r in rows],colWidths=[width/len(cols)]*len(cols),repeatRows=1,splitInRow=1,hAlign='LEFT')
  table.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('TEXTCOLOR',(0,0),(-1,0),colors.white),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f1f5f8')]),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#dce4ed')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),7),('RIGHTPADDING',(0,0),(-1,-1),7),('TOPPADDING',(0,0),(-1,-1),7),('BOTTOMPADDING',(0,0),(-1,-1),7)]))
  story.extend([table,Spacer(1,18)])
 story.extend([Paragraph('UNIVERSITY CONTEST REPORT',styles['SmallReport']),Spacer(1,14),Paragraph(escape(s['contest']['title']),styles['Title']),Paragraph(escape(data['contestId']+' | '+data['status']+' | Exported '+data['exportedAt']),styles['SmallReport']),Spacer(1,20)])
 section('Contest configuration',['Setting','Value'],[{'Setting':{'title':'Contest title','shortName':'Short name','running':'Clock running','elapsedSeconds':'Elapsed (seconds)','remainingSeconds':'Remaining (seconds)','lengthSeconds':'Duration (seconds)','freezeRemaining':'Freeze remaining time','thawed':'Frozen results released','scheduledStart':'Scheduled start (UTC)'}.get(k,k),'Value':v} for k,v in s['contest'].items()])
 raw=s.get('standings',{}).get('contestStandings',{}).get('teamStanding',[]);raw=[raw] if isinstance(raw,dict) else raw
 section('Administrator standings (public freeze ignored)',['Rank','Team','Solved','Penalty'],[{'Rank':r.get('overallRank',r.get('rank','')),'Team':r.get('teamName',''),'Solved':r.get('solved',''),'Penalty':r.get('points','')} for r in raw])
 section('Teams',['login','name','enabled','visible'],s.get('teams',[]));section('Problems',['letter','name','timeLimit','memoryLimit','tests','active'],s.get('problems',[]))
 section('Submissions',['site','number','teamName','problem','language','elapsedMinutes','verdict','final'],s.get('runs',[]))
 section('Clarifications',['number','team','problem','question','answer'],s.get('clarifications',[]));section('Resources',['filename','problem','kind','language','published','deleted'],data['resources'])
 section('Audit trail',['created','actor','event','outcome'],data['audit'])
 story.append(Paragraph('Report scope',styles['Heading2']))
 for note in data['notes']:story.append(Paragraph(escape(note),styles['SmallReport']))
 def footer(canvas,doc):
  canvas.setStrokeColor(teal);canvas.line(36,30,page[0]-36,30);canvas.setFont(face,8);canvas.setFillColor(navy);canvas.drawString(36,18,'LCPC OMU | Private organizer report');canvas.drawRightString(page[0]-36,18,'Page '+str(doc.page))
 SimpleDocTemplate(str(path),pagesize=page,rightMargin=36,leftMargin=36,topMargin=36,bottomMargin=42,title=s['contest']['title'],author='University Contest Administration').build(story,onFirstPage=footer,onLaterPages=footer)
if __name__=='__main__':render(json.loads(Path(sys.argv[1]).read_text()),sys.argv[2])
