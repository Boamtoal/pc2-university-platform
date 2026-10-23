import edu.csus.ecs.pc2.api.*;
import edu.csus.ecs.pc2.core.*;
import edu.csus.ecs.pc2.core.model.*;
import java.nio.file.*;
import java.util.*;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import edu.csus.ecs.pc2.core.scoring.DefaultScoringAlgorithm;

/** Uses bundled PC2 API for repeatable real server checks and administrative controls. */
public class LCPCAdmin extends ServerConnection {
  static void require(boolean ok,String msg) {if(!ok)throw new IllegalStateException(msg);}
  String accountFingerprint() throws Exception {
    List<String> rows=new ArrayList<>();
    for(Account a:internalContest.getAccounts())rows.add(a.getClientId().getName()+"\0"+a.getDisplayName()+"\0"+a.getPassword());
    Collections.sort(rows);
    return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(String.join("\n",rows).getBytes(StandardCharsets.UTF_8)));
  }
  void configurePython() throws Exception {
    Language l=Arrays.stream(internalContest.getLanguages()).filter(x->"Python 3.12 (Isolated Linux ARM64)".equals(x.getDisplayName())).findFirst().orElse(null);
    boolean fresh=l==null;if(fresh)l=new Language("Python 3.12 (Isolated Linux ARM64)");
    l.setCompileCommandLine("/opt/lcpc/bin/compilepython {:mainfile} {:basename}.lcpcpy");
    l.setExecutableIdentifierMask("{:basename}.lcpcpy");
    l.setProgramExecuteCommandLine("/opt/lcpc/bin/runpython {:basename}.lcpcpy");
    // Syntax checking produces the staged source artifact before isolated execution.
    l.setInterpreted(false);l.setUsingJudgeProgramExecuteCommandLine(false);l.setActive(true);
    if(fresh)controller.addNewLanguage(l);else controller.updateLanguage(l);
    Thread.sleep(800);
  }
  void eventSummary() throws Exception {
    ContestInformation i=internalContest.getContestInformation();ContestTime t=internalContest.getContestTime();
    System.out.println("EVENT title="+i.getContestTitle()+" short="+i.getContestShortName());
    System.out.println("SCHEDULE start="+(i.getScheduledStartDate()==null?"unset":i.getScheduledStartDate().toInstant())+" autoStart="+i.isAutoStartContest()+" autoStop="+i.isAutoStopContest());
    System.out.println("TIMING lengthSeconds="+t.getContestLengthSecs()+" freezeRemaining="+i.getFreezeTime()+" running="+t.isContestRunning()+" elapsedSeconds="+t.getElapsedSecs());
    System.out.println("ACCOUNT_FINGERPRINT "+accountFingerprint());
    System.out.println("COUNTS teams="+Arrays.stream(internalContest.getAccounts()).filter(a->a.getClientId().getName().matches("team[0-9]+")).count()+" problems="+getContest().getProblems().length+" runs="+getContest().getRuns().length);
    for(Language l:internalContest.getLanguages())System.out.println("LANGUAGE_PROFILE "+l.getDisplayName()+" active="+l.isActive()+" compile="+l.getCompileCommandLine()+" run="+l.getProgramExecuteCommandLine());
    System.out.println("SCORING "+i.getScoringProperties());
  }
  void dump() throws Exception {
    IContest c=getContest();
    System.out.println("CONTEST "+internalContest.getContestInformation().getContestTitle());
    System.out.println("SCORING "+internalContest.getContestInformation().getScoringProperties());
    for(IProblem p:c.getProblems())System.out.println("PROBLEM "+p.getShortName()+" "+p.getName());
    for(ILanguage l:c.getLanguages())System.out.println("LANGUAGE "+l.getName());
    for(IRun r:c.getRuns())System.out.println("RUN "+r.getNumber()+" "+r.getTeam().getLoginName()+" "+r.getProblem().getShortName()+" "+r.getJudgementName()+" final="+r.isFinalJudged()+" solved="+r.isSolved());
    for(IStanding s:c.getStandings())System.out.println("STANDING "+s.getClient().getLoginName()+" rank="+s.getRank()+" solved="+s.getNumProblemsSolved()+" penalty="+s.getPenaltyPoints());
    for(ClientType.Type type:ClientType.Type.values()) for(ClientId id:internalContest.getLocalLoggedInClients(type)) System.out.println("LOGIN "+id.getName());
    System.out.println("CLOCK running="+internalContest.getContestTime().isContestRunning()+" elapsed="+internalContest.getContestTime().getElapsedTimeStr());
  }
  public static void main(String[] args) {
    LCPCAdmin s=new LCPCAdmin();int exit=0;
    try {
      Properties p=LCPCLaunch.secrets();String op=args[0];
      String user=op.equals("submit")?args[1]:op.equals("status")?"scoreboard1":"administrator1";
      s.login(user,op.equals("secure-bootstrap")?"administrator1":p.getProperty(user));
      System.out.println("AUTHENTICATED "+user+" Java="+System.getProperty("java.version"));
      switch(op) {
        case "reschedule-event": {
          require(System.getProperty("lcpc.cdp").contains("/lcpc-omu-preparation/"),"Organizer preparation instance required");
          ContestTime t=s.internalContest.getContestTime();
          require(!t.isContestRunning() && t.getElapsedSecs()==0 && s.getContest().getRuns().length==0,"Event must remain unstarted");
          java.time.OffsetDateTime start=java.time.OffsetDateTime.parse(args[1]),end=java.time.OffsetDateTime.parse(args[2]);
          long duration=java.time.Duration.between(start,end).getSeconds();require(duration>2700,"Duration must exceed freeze length");
          ContestInformation info=s.internalContest.getContestInformation();
          GregorianCalendar cal=GregorianCalendar.from(start.toZonedDateTime());info.setScheduledStartDate(Date.from(start.toInstant()));info.setScheduledStartTime(cal);info.setAutoStartContest(false);info.setAutoStopContest(true);info.setFreezeTime("00:45:00");
          s.controller.updateContestInformation(info);t.setContestLengthSecs(duration);t.setHaltContestAtTimeZero(true);s.controller.updateContestTime(t);Thread.sleep(1000);s.eventSummary();break;
        }
        case "event-summary":s.eventSummary();break;
        case "enable-python-test":
          require(s.internalContest.getContestInformation().getContestTitle().contains("ISOLATED INFRASTRUCTURE TEST"),"Technical test contest required");
          s.configurePython();s.eventSummary();break;
        case "prepare-event": {
          require(System.getProperty("lcpc.cdp").contains("/lcpc-omu-preparation/"),"Organizer preparation instance required");
          ContestTime t=s.internalContest.getContestTime();
          require(!t.isContestRunning() && t.getElapsedSecs()==0,"Event clock must remain unstarted");
          require(s.getContest().getRuns().length==0 && s.getContest().getProblems().length==0,"Expected event awaiting problem files");
          String before=s.accountFingerprint();System.out.println("ACCOUNTS_BEFORE "+before);
          ContestInformation i=s.internalContest.getContestInformation();
          i.setContestTitle("LCPC OMU Practice Contest");i.setContestShortName("LCPC OMU");
          GregorianCalendar date=new GregorianCalendar(TimeZone.getTimeZone("Africa/Tripoli"));
          date.clear();date.set(2026,Calendar.OCTOBER,19,10,30,0);
          i.setScheduledStartTime(date);i.setScheduledStartDate(date.getTime());
          i.setAutoStartContest(false);i.setAutoStopContest(true);i.setFreezeTime("00:45:00");i.setThawed(false);
          Properties scoring=DefaultScoringAlgorithm.getDefaultProperties();
          scoring.putAll(i.getScoringProperties());
          scoring.setProperty(DefaultScoringAlgorithm.POINTS_PER_NO,"20");
          scoring.setProperty(DefaultScoringAlgorithm.POINTS_PER_YES_MINUTE,"1");
          scoring.setProperty(DefaultScoringAlgorithm.BASE_POINTS_PER_YES,"0");
          scoring.setProperty(DefaultScoringAlgorithm.POINTS_PER_NO_COMPILATION_ERROR,"0");
          i.setScoringProperties(scoring);s.controller.updateContestInformation(i);
          t.setContestLengthSecs(7200);t.setHaltContestAtTimeZero(true);s.controller.updateContestTime(t);
          s.configurePython();Thread.sleep(1000);
          require(before.equals(s.accountFingerprint()),"Account preservation failed");
          s.eventSummary();break;
        }
        case "secure-bootstrap":
          for(Account a:s.internalContest.getAccounts()) {
            String u=a.getClientId().getName();
            if(p.getProperty(u)!=null) {a.setPassword(p.getProperty(u));s.controller.updateAccount(a);}
          }
          Thread.sleep(1500);System.out.println("Bootstrap credentials rotated through PC2 controller");break;
        case "audit":
          for(Account a:s.internalContest.getAccounts()) {
            String u=a.getClientId().getName();
            require(p.getProperty(u)!=null && p.getProperty(u).equals(a.getPassword()),"Unexpected credential for "+u);
            require(!a.getPassword().equals(u),"Default credential: "+u);
            System.out.println("CREDENTIAL_NONDEFAULT "+u);
          }
          require(p.getProperty("site1").equals(s.internalContest.getSite(1).getPassword()),"Site credential mismatch");
          s.dump();break;
        case "infra-judgements":
          require(s.internalContest.getContestInformation().getContestTitle().contains("ISOLATED INFRASTRUCTURE TEST"),"Technical test contest required");
          if(Arrays.stream(s.internalContest.getJudgements()).noneMatch(j->"MLE".equals(j.getAcronym())))s.controller.addNewJudgement(new Judgement("No - Memory Limit Exceeded","MLE"));
          Thread.sleep(700);System.out.println("MLE judgement configured");break;
        case "start-clock":s.startContestClock();Thread.sleep(800);s.dump();break;
        case "stop-clock":s.stopContestClock();Thread.sleep(800);s.dump();break;
        case "quiesce":
          s.stopContestClock();Thread.sleep(700);
          long end=System.currentTimeMillis()+30000;
          while(Arrays.stream(s.getContest().getRuns()).anyMatch(r->!r.isFinalJudged()&&!r.isDeleted()) && System.currentTimeMillis()<end)Thread.sleep(500);
          require(Arrays.stream(s.getContest().getRuns()).allMatch(r->r.isFinalJudged()||r.isDeleted()),"Pending submissions remain");
          System.out.println("QUIESCENT all submissions final");break;
        case "shutdown":s.shutdownServer();Thread.sleep(1500);break;
        case "status":s.dump();break;
        case "roster":
          for(Account a:s.internalContest.getAccounts()) {
            String u=a.getClientId().getName();
            if(u.matches("team[0-9]+"))System.out.println("TEAM "+u+" displayName="+a.getDisplayName());
          }
          break;
        case "submit":
          IProblem problem=Arrays.stream(s.getContest().getProblems()).filter(x->x.getShortName().equals(args[2])).findFirst().orElseThrow();
          ILanguage lang=args.length>5?Arrays.stream(s.getContest().getLanguages()).filter(l->l.getName().equals(args[5])).findFirst().orElseThrow():s.getContest().getLanguages()[0];
          int before=s.getContest().getRuns().length;
          s.submitJudgeRun(problem,lang,Path.of(args[3]).toAbsolutePath().toString());
          long deadline=System.currentTimeMillis()+90000;IRun found=null;
          while(System.currentTimeMillis()<deadline) {
            Thread.sleep(500);
            IRun[] runs=s.getContest().getRuns();
            if(runs.length>before) {
              found=Arrays.stream(runs).max(Comparator.comparingInt(IRun::getNumber)).orElseThrow();
              if(found.isFinalJudged())break;
            }
          }
          require(found!=null && found.isFinalJudged(),"Submission did not receive final judgement");
          System.out.println("RESULT run="+found.getNumber()+" team="+user+" problem="+problem.getShortName()+" judgement="+found.getJudgementName()+" solved="+found.isSolved());
          if(args.length>4)require(found.getJudgementName().toLowerCase().contains(args[4].toLowerCase()),"Unexpected judgement");
          break;
        default:throw new IllegalArgumentException("Unknown operation");
      }
    }catch(Exception e){e.printStackTrace();exit=1;}
    finally{try{if(s.isLoggedIn())s.logoff();}catch(Exception ignored){} }
    System.exit(exit);
  }
}
