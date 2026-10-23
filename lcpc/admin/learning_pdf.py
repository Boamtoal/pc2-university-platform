"""Printable team feedback from facts and organizer material; no source execution."""
from pathlib import Path
import json,sys,textwrap,subprocess,shutil
from xml.sax.saxutils import escape
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,LongTable,TableStyle,PageBreak,CondPageBreak,XPreformatted
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.pagesizes import A4
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from pypdf import PdfReader,PdfWriter

def render(source,target):
 root=source.parent;data=json.loads(source.read_text());font=Path('/System/Library/Fonts/Supplemental/Arial Unicode.ttf');face='Helvetica'
 if font.is_file():pdfmetrics.registerFont(TTFont('LearningUnicode',str(font)));face='LearningUnicode'
 mono='Courier'
 mono_file=Path('/System/Library/Fonts/Supplemental/Courier New.ttf')
 if mono_file.is_file():pdfmetrics.registerFont(TTFont('LearningMono',str(mono_file)));mono='LearningMono'
 styles=getSampleStyleSheet()
 for key in ('Normal','Title','Heading1','Heading2','Heading3'):styles[key].fontName=face
 styles['Normal'].fontSize=9;styles['Normal'].leading=14
 styles.add(ParagraphStyle('LearningSmall',parent=styles['Normal'],fontSize=8,leading=11,textColor=colors.HexColor('#52677d'),wordWrap='CJK'))
 styles.add(ParagraphStyle('LearningCode',fontName=mono,fontSize=8,leading=11,spaceAfter=10,backColor=colors.HexColor('#f1f5f9'),borderPadding=7))
 styles.add(ParagraphStyle('LearningCell',parent=styles['Normal'],fontSize=7.5,leading=10,wordWrap='CJK'))
 styles.add(ParagraphStyle('LearningHeader',parent=styles['LearningCell'],textColor=colors.white))
 navy=colors.HexColor('#102b47');width=A4[0]-80;story=[];statements=[]
 def p(text,style='Normal'):return Paragraph(escape(str(text)).replace('\n','<br/>'),styles[style])
 def text(value,style='Normal'):story.extend([p(value,style),Spacer(1,5)])
 def heading(title,level='Heading2'):story.extend([CondPageBreak(90),p(title,level)])
 def code(value,label,numbered=False):
  heading(label,'Heading3')
  if not value:text('No retained content is available.','LearningSmall');return
  content=value.get('text','') if isinstance(value,dict) else value
  lines=[]
  for number,line in enumerate(content.expandtabs(4).splitlines(),1):
   chunks=[];chunk='';used=0;available=width-22-pdfmetrics.stringWidth('00000  ',mono,8)
   for char in line:
    size=pdfmetrics.stringWidth(char,mono,8)
    if chunk and used+size>available:chunks.append(chunk);chunk='';used=0
    chunk+=char;used+=size
   chunks.append(chunk)
   lines.append((f'{number:4}  ' if numbered else '')+chunks[0]);lines.extend(('      ' if numbered else '')+chunk for chunk in chunks[1:])
  story.append(XPreformatted(escape('\n'.join(lines) or '(empty file)'),styles['LearningCode']))
  if isinstance(value,dict) and value.get('truncated'):text('Preview truncated. Complete file: '+value.get('path','included in this team folder'),'LearningSmall')
 def table(columns,rows,widths=None):
  if not rows:text('No records.','LearningSmall');return
  grid=[[p(c,'LearningHeader') for c in columns]]+[[p(v,'LearningCell') for v in row] for row in rows]
  t=LongTable(grid,colWidths=[width*x for x in widths] if widths else [width/len(columns)]*len(columns),repeatRows=1,splitInRow=1,hAlign='LEFT')
  t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),navy),('ROWBACKGROUNDS',(0,1),(-1,-1),[colors.white,colors.HexColor('#f2f6fa')]),('GRID',(0,0),(-1,-1),.3,colors.HexColor('#dce4ed')),('VALIGN',(0,0),(-1,-1),'TOP'),('LEFTPADDING',(0,0),(-1,-1),6),('RIGHTPADDING',(0,0),(-1,-1),6),('TOPPADDING',(0,0),(-1,-1),6),('BOTTOMPADDING',(0,0),(-1,-1),6)]))
  story.extend([t,Spacer(1,12)])
 text('TEAM LEARNING REPORT','LearningSmall');story.append(p(data['contest']['title'],'Title'));text(data['team']['name']+' | '+data['team']['login']);text('Exported '+data['exportedAt']+' | Contest time is shown in elapsed minutes.','LearningSmall')
 table(['Attempts','Accepted attempts','Distinct problems solved'],[[data['attempts'],data['acceptedAttempts'],data['solvedProblems']]])
 heading('How to use this report')
 text('Read the reference reasoning, trace your own approach and review the retained test outcomes. Original source, current reference tests, textual diffs and saved output files accompany this PDF. Post-contest analysis executes team code only in the isolated Linux sandbox and never changes official judgements.')
 text('Evidence limits: current test data is not proven to be the historic revision used for a submission. Historic stdout/stderr is not linked to a particular test by this PC2 version. Per-test outputs below are newly captured isolated replay evidence. A textual code difference is not proof of a logical error. Missing evidence is marked unavailable, never inferred.','LearningSmall')
 heading('Recommended next steps')
 for note in data['advice']:text('- '+note)
 if data.get('activity'):
  heading('Retained interactive activity');table(['Observed action','Count'],list(data['activity'].get('events',{}).items()));text('First retained interaction: '+data['activity'].get('first','Unknown')+' | Last: '+data['activity'].get('last','Unknown'),'LearningSmall')
 if data.get('clarifications'):
  heading('Your questions');table(['Problem','Question','Answer'],[[c.get('problem','General'),c.get('question',''),c.get('answer') or 'Not answered'] for c in data['clarifications']], [.2,.4,.4])
 for problem in data['problems']:
  story.append(PageBreak());heading(problem['letter']+' - '+problem['name'],'Heading1');rating=problem.get('difficulty');text('Difficulty: '+(str(rating)+(' (estimated)' if problem.get('difficultyEstimated') else '') if rating is not None else 'Not assigned')+' | Time limit: '+str(problem.get('timeLimit','Unknown'))+' s | Memory: '+str(problem.get('memoryLimit','Unknown'))+' MiB')
  text('Attempts: '+str(len(problem['attempts']))+' | Current reference tests: '+str(len(problem['tests']))+' | Validator: '+problem['validator'],'LearningSmall')
  heading('Problem statement and supporting files')
  table(['File','Language','Type'],[[r['filename'],r['language'],r['kind']] for r in problem['resources']],[.6,.2,.2])
  for resource in problem['resources']:
   if resource['mime']=='application/pdf' and resource['kind'] in ('statement','booklet'):statements.append(resource['path'])
  text('Full supplied problem PDFs are appended after the feedback section and included as original files.','LearningSmall')
  reference=problem['reference'];editorial=reference.get('editorial')
  if editorial:
   heading('Solution explanation and complexity');text(editorial['preview']);text(editorial['provenance'],'LearningSmall')
  else:heading('Reference reasoning');text('No organizer explanation has been supplied. No algorithmic explanation was invented.','LearningSmall')
  solution=reference.get('solution')
  if solution:
   formatted=solution['preview'];formatter=shutil.which('clang-format')
   if not formatter and shutil.which('xcrun'):
    probe=subprocess.run(['xcrun','--find','clang-format'],capture_output=True,text=True,timeout=5);formatter=probe.stdout.strip() if probe.returncode==0 else None
   if formatter and Path(solution['filename']).suffix.lower() in ('.cpp','.cc','.c'):
    result=subprocess.run([formatter,'-style={BasedOnStyle: LLVM, IndentWidth: 4, ColumnLimit: 78}','--assume-filename=reference.cpp'],input=formatted,capture_output=True,text=True,timeout=10)
    if result.returncode==0:
     formatted=result.stdout;original=root/solution['path'];(original.parent/'formatted-reference.cpp').write_text(formatted)
   code({'text':formatted,'truncated':solution['truncated']},'Organizer reference solution - C++' if Path(solution['filename']).suffix.lower() in ('.cpp','.cc','.c') else 'Organizer reference solution',numbered=True)
   text('Presentation formatting only. The original source is included separately. '+solution['provenance'],'LearningSmall')
  else:text('Reference solution unavailable. An owner can upload it from Team Learning Reports.','LearningSmall')
  table(['Run','Minute','Auto result','Final / current result'],[[str(a['site'])+'-'+str(a['number']),f"{a.get('elapsedMinutes',0):.2f}",a.get('automaticVerdict') or 'Not retained',a.get('verdict','Pending')+('' if a.get('final') else ' (not final)')] for a in problem['attempts']],[.12,.12,.35,.41])
  for attempt in problem['attempts']:
   story.append(PageBreak());heading('Attempt '+str(attempt['site'])+'-'+str(attempt['number'])+' | '+problem['letter'],'Heading1')
   text('Language: '+attempt.get('language','Unknown')+' | Elapsed minute: '+f"{attempt.get('elapsedMinutes',0):.2f}")
   verdict=attempt.get('verdict','Pending');tone='#126349' if attempt.get('accepted') and attempt.get('final') else '#a52e3b' if attempt.get('final') else '#826218'
   story.append(Paragraph('<font color="'+tone+'">'+escape(verdict+('' if attempt.get('final') else ' - not final'))+'</font>',styles['Heading2']))
   text('Automatic result: '+(attempt.get('automaticVerdict') or 'Not retained')+' | Workflow: '+attempt.get('workflowState','Unknown'),'LearningSmall')
   if attempt['history']:table(['Decision','Actor','Time (UTC)','Type'],[[h['verdict'],h['actor'],h['at'],'Automatic' if h['computer'] else 'Human'] for h in attempt['history']],[.25,.16,.4,.19])
   if attempt.get('organizerDecisions'):table(['Organizer action','Actor / time (UTC)','Reason'],[[d['action'],d['actor']+' / '+d['at'],d['reason'] or 'No reason retained'] for d in attempt['organizerDecisions']],[.2,.35,.45])
   if not attempt['sources']:text('Team source was not retained.','LearningSmall')
   for source_file in attempt['sources']:code(source_file.get('preview'),'Your source: '+source_file.get('name','Source'),numbered=True)
   if attempt['comparisonAvailable']:
    text('A raw line-by-line diff is available separately in the attempt folder. It is not mixed with the reference code in this PDF.','LearningSmall')
   heading('Test cases: input, team output and correct output')
   text('The following team outputs come from an isolated analysis replay on the current test data. They are separate from the original contest decision. All tests are shown, including tests after the original first failure. Large values have clearly marked previews; the complete files are included in the team folder.','LearningSmall')
   replay=attempt.get('replay',{})
   if replay.get('compilation',{}).get('exit'):
    code(replay.get('compilerStderr',''),'Analysis replay - compilation error')
   recorded={c['number']:c for c in attempt.get('cases',{}).get('tests',[])}
   if not attempt.get('replayTests'):text('Per-test replay is unavailable for this language/source. No team output is invented.','LearningSmall')
   for case in attempt.get('replayTests',[]):
    heading('Test case '+str(case['number']),'Heading3')
    old=recorded.get(case['number'],{}).get('status','Not recorded')
    status=case.get('executionStatus') or ('Completed' if case.get('exit')==0 else 'Time Limit Exceeded' if case.get('exit') in (244,245) else 'Runtime Error' if case.get('executed') else 'Compilation Error - not executed')
    tone='#126349' if status=='Completed' else '#a52e3b'
    story.append(Paragraph('<font color="'+tone+'">'+escape('Analysis replay: '+status)+'</font>',styles['Normal']))
    text('Original saved status: '+old+' | Output comparison: '+case['comparison'],'LearningSmall')
    code(case.get('input'),'Input')
    if not case.get('executed'):text('Team output: Not executed because compilation failed.','LearningSmall')
    else:code(case.get('output'),'Team output - actual replay stdout')
    code(case.get('expected'),'Correct output - expected answer')
    if (case.get('stderr') or {}).get('text'):code(case['stderr'],'Runtime diagnostics')
   heading('Saved compiler / execution / validator evidence')
   if not attempt['reports']:text('No saved output report was retained.','LearningSmall')
   for i,saved in enumerate(attempt['reports'],1):
    heading('Saved report '+str(i)+' - '+saved.get('verdict','Unknown'),'Heading3');table(['Stage','Exit code','Time (ms)'],[['Compiler',saved.get('compileExitCode','Unknown'),saved.get('compileTimeMS','Unknown')],['Execution',saved.get('executeExitCode','Unknown'),saved.get('executeTimeMS','Unknown')],['Validator',saved.get('validationExitCode','Unknown'),saved.get('validateTimeMS','Unknown')]])
    text('Saved report verdict can differ from the final human decision. Output-to-test association is unavailable; no output is presented as a particular test result.','LearningSmall')
    for key,item in saved['outputs'].items():
     if key=='executionStdout':label='Actual saved program output (test association unavailable)'
     else:label={'compilerStderr':'Compiler errors / stderr','compilerStdout':'Compiler stdout','executionStderr':'Execution errors / stderr','validatorStderr':'Validator stderr','validatorStdout':'Validator stdout'}.get(key,key)
     code(item.get('preview'),label)
    if saved.get('validatorMessage'):text('Validator message: '+saved['validatorMessage'],'LearningSmall')
 heading('Evidence file index');text('report.json contains full structured metadata, all case statuses and the paths/checksums of retained files. Each problem folder contains complete current input/answer files. Each attempt folder contains only this team\'s source and saved judge streams. Missing output, missing reference material and missing historic associations remain explicitly unavailable.','LearningSmall')
 interim=target.with_suffix('.feedback.pdf')
 def footer(canvas,doc):
  canvas.setFont(face,8);canvas.setFillColor(navy);canvas.drawString(40,24,data['team']['login']+' | Team learning report');canvas.drawRightString(A4[0]-40,24,'Feedback page '+str(doc.page))
 SimpleDocTemplate(str(interim),pagesize=A4,leftMargin=40,rightMargin=40,topMargin=42,bottomMargin=42,title=data['team']['name']+' - Team learning report',author='Contest organizer').build(story,onFirstPage=footer,onLaterPages=footer)
 writer=PdfWriter();writer.append(PdfReader(str(interim)),import_outline=False)
 seen=set()
 for relative in statements:
  file=root/relative
  import hashlib
  digest=hashlib.sha256(file.read_bytes()).hexdigest()
  if digest in seen:continue
  seen.add(digest);reader=PdfReader(str(file));
  if len(reader.pages)>250:raise ValueError('A problem document exceeds 250 pages')
  writer.append(reader,import_outline=False)
 writer.add_metadata({'/Title':data['team']['name']+' - Team learning report','/Author':'Contest organizer'})
 with target.open('wb') as stream:writer.write(stream)
 interim.unlink()

if __name__=='__main__':render(Path(sys.argv[1]),Path(sys.argv[2]))
