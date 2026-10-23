import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.IInternalController;
import org.json.*;
import java.io.*;
import java.nio.file.*;
import java.lang.reflect.*;
import java.util.*;

/** Typed configuration preview. Stages a complete batch before sending any native packet. */
public final class AdministratorConfig {
 static final Set<String> WRITES=Set.of("addNewAccount","addNewLanguage","addNewGroup","addNewCategory","addNewJudgement","addNewSite","addNewBalloonSettings","updateAccount","updateLanguage","updateGroup","updateCategory","updateJudgement","updateSite","updateProblem","updateContestInformation","updateContestTime","updateFinalizeData","updateBalloonSettings","updateProfile");
 static class Invocation implements Serializable {String name;Class<?>[] types;Object[] args;Invocation(Method method,Object[] values){name=method.getName();types=method.getParameterTypes();args=values;}}
 static class Plan implements Serializable {String fingerprint;long created;List<Invocation> calls=new ArrayList<>();List<Map<String,Object>> credentials=new ArrayList<>();}
 static class StagedModel extends InternalContest {Run[] sourceRuns;public Run[] getRuns(){return sourceRuns==null?new Run[0]:sourceRuns;}}
 static class Staged extends DashboardBridge {
  StagedModel data=new StagedModel();IInternalController recorder;Plan plan;
  Staged(DashboardBridge source,Plan p)throws Exception{
   plan=p;privateBase=source.privateBase;data.setSiteNumber(source.model().getSiteNumber());data.setClientId(source.model().getClientId());data.sourceRuns=source.model().getRuns();
   for(Site value:source.model().getSites())data.addSite(AdministratorFeatures.copy(value));for(Account value:source.model().getAccounts())data.addAccount(AdministratorFeatures.copy(value));for(Language value:source.model().getLanguages())data.addLanguage(AdministratorFeatures.copy(value));for(Group value:source.model().getGroups())data.addGroup(AdministratorFeatures.copy(value));for(Category value:source.model().getCategories())data.addCategory(AdministratorFeatures.copy(value));for(Judgement value:source.model().getJudgements())data.addJudgement(AdministratorFeatures.copy(value));for(Problem value:source.model().getProblems())data.addProblem(AdministratorFeatures.copy(value),AdministratorFeatures.copy(source.model().getProblemDataFile(value)));for(ContestTime value:source.model().getContestTimes())data.addContestTime(AdministratorFeatures.copy(value));for(BalloonSettings value:source.model().getBalloonSettings())data.addBalloonSettings(AdministratorFeatures.copy(value));for(Profile value:source.model().getProfiles())data.addProfile(AdministratorFeatures.copy(value));data.addContestInformation(AdministratorFeatures.copy(source.model().getContestInformation()));if(source.model().getFinalizeData()!=null)data.setFinalizeData(AdministratorFeatures.copy(source.model().getFinalizeData()));
   recorder=(IInternalController)Proxy.newProxyInstance(getClass().getClassLoader(),new Class[]{IInternalController.class},(proxy,method,args)->{
    if(method.getName().equals("getLog"))return source.control().getLog();AdministratorFeatures.need(WRITES.contains(method.getName()),"Unsupported configuration import operation");Invocation call=new Invocation(method,args);String target=switch(method.getName()){case "addNewAccount"->"addAccount";case "addNewLanguage"->"addLanguage";case "addNewGroup"->"addGroup";case "addNewCategory"->"addCategory";case "addNewJudgement"->"addJudgement";case "addNewSite"->"addSite";case "addNewBalloonSettings"->"addBalloonSettings";case "updateFinalizeData"->"setFinalizeData";default->method.getName();};
    StagedModel.class.getMethod(target,method.getParameterTypes()).invoke(data,args);plan.calls.add(call);if(method.getName().equals("addNewAccount")){Account a=(Account)args[0];plan.credentials.add(Map.of("site",a.getSiteNumber(),"login",a.getClientId().getName(),"name",a.getDisplayName(),"password",a.getPassword()));}return null;
   });internalContest=data;controller=recorder;
  }
  IInternalContest model(){return data;}IInternalController control(){return recorder;}
 }
 static String fingerprint(DashboardBridge s)throws Exception{
  JSONObject state=new JSONObject();for(String domain:AdministratorFeatures.TYPES.keySet())state.put(domain,AdministratorFeatures.rows(s,domain).getJSONArray("rows"));JSONArray secrets=new JSONArray();for(Account a:s.model().getAccounts())secrets.put(a.getPassword());for(Site site:s.model().getSites())secrets.put(site.getPassword());state.put("credentialFingerprint",HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(secrets.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8))));state.put("scoring",AdministratorFeatures.scoring(s));ByteArrayOutputStream infoBytes=new ByteArrayOutputStream();try(ObjectOutputStream out=new ObjectOutputStream(infoBytes)){out.writeObject(s.model().getContestInformation());}state.put("informationFingerprint",HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(infoBytes.toByteArray())));state.put("runs",s.model().getRuns().length);return HexFormat.of().formatHex(java.security.MessageDigest.getInstance("SHA-256").digest(state.toString().getBytes(java.nio.charset.StandardCharsets.UTF_8)));
 }
 static JSONObject preview(DashboardBridge s,JSONObject a)throws Exception{
  AdministratorFeatures.paused(s);JSONObject bundle=a.getJSONObject("bundle");AdministratorFeatures.need(bundle.optString("format").equals("PC2-DASHBOARD-CONFIG-1"),"Unsupported configuration JSON format");String domain=bundle.getString("domain");AdministratorFeatures.need((AdministratorFeatures.TYPES.containsKey(domain)||domain.equals("scoring"))&&!domain.equals("profiles"),"This section cannot import configuration");JSONArray rows=domain.equals("scoring")?new JSONArray().put(new JSONObject().put("properties",bundle.getJSONObject("properties"))):bundle.getJSONArray("records");AdministratorFeatures.need(rows.length()>0&&rows.length()<=100,"Import 1–100 records per configuration batch");Plan plan=new Plan();plan.created=System.currentTimeMillis();plan.fingerprint=fingerprint(s);Staged staged=new Staged(s,plan);JSONArray changes=new JSONArray();
  AdministratorFeatures.validating.set(true);
  try{for(int i=0;i<rows.length();i++){
   JSONObject row=rows.getJSONObject(i);if(domain.equals("scoring")){AdministratorFeatures.operations(staged,new JSONObject().put("command","scoring.save").put("properties",row.getJSONObject("properties")));changes.put(new JSONObject().put("action","update").put("record","Scoring rules"));continue;}JSONObject fields=row.getJSONObject("fields");Object matched=null;
   for(Object value:AdministratorFeatures.values(staged,domain)){
    JSONObject existing=AdministratorFeatures.bean(domain,value);boolean same=existing.getString("id").equals(row.optString("id"));
    if(value instanceof Account account)same|=account.getClientId().getName().equals(row.optString("login"))&&account.getSiteNumber()==row.optInt("site",staged.model().getSiteNumber());
    else if(value instanceof Site site)same|=site.getSiteNumber()==row.optInt("number",row.optInt("site",-1));
    else if(value instanceof BalloonSettings balloon)same|=balloon.getSiteNumber()==row.optInt("site",-1);
    else if(value instanceof ContestTime time)same|=time.getSiteNumber()==row.optInt("site",-1);
    else if(domain.equals("contest")||domain.equals("finalization"))same=true;
    else if(value instanceof Problem p)same|=Objects.equals(p.getLetter(),fields.optString("Letter"));
    else if(value instanceof Judgement judgement)same|=judgement.getAcronym().equals(fields.optString("Acronym"));
    else if(existing.getJSONObject("fields").has("DisplayName"))same|=existing.getJSONObject("fields").getString("DisplayName").equals(fields.optString("DisplayName"));
    if(same){matched=value;break;}
   }
   boolean create=matched==null;JSONObject args=new JSONObject().put("command","save").put("domain",domain).put("fields",fields).put("create",create);if(!create)args.put("id",AdministratorFeatures.bean(domain,matched).getString("id"));
   for(String key:List.of("permissions","members","validator","colors","host","port","password","proxySites","myProxy","primaryGroup"))if(row.has(key))args.put(key,row.get(key));
   if(row.has("groupNames")){JSONArray ids=new JSONArray(),names=row.getJSONArray("groupNames");for(int n=0;n<names.length();n++){String name=names.getString(n);Group group=Arrays.stream(staged.model().getGroups()).filter(g->g.getDisplayName().equals(name)).findFirst().orElseThrow(()->new IllegalArgumentException("Import the missing group first: "+name));ids.put(group.getElementId().toString());}args.put("groups",ids);}
   if(row.has("primaryGroupName")&&!row.optString("primaryGroupName").isBlank()){String name=row.getString("primaryGroupName");Group group=Arrays.stream(staged.model().getGroups()).filter(g->g.getDisplayName().equals(name)).findFirst().orElseThrow(()->new IllegalArgumentException("Import the primary group first: "+name));args.put("primaryGroup",group.getElementId().toString());}
   if(create){args.put("site",domain.equals("sites")?row.optInt("number",row.optInt("site",staged.model().getSiteNumber())):row.optInt("site",staged.model().getSiteNumber()));if(domain.equals("accounts")){args.put("type",row.optString("type","TEAM"));if(!args.has("password"))args.put("password",UUID.randomUUID().toString()+UUID.randomUUID().toString().substring(0,8));}}
   if(domain.equals("sites")&&matched instanceof Site site&&site.getSiteNumber()==staged.model().getSiteNumber()){args.remove("host");args.remove("port");args.remove("password");}
   AdministratorFeatures.save(staged,args);changes.put(new JSONObject().put("action",create?"create":"update").put("record",fields.optString("DisplayName",row.optString("login",domain))));
  }}finally{AdministratorFeatures.validating.remove();}
  Path dir=s.privateBase.resolve("configuration-plans");Files.createDirectories(dir);String token=UUID.randomUUID().toString().replace("-","");try(ObjectOutputStream out=new ObjectOutputStream(Files.newOutputStream(dir.resolve(token+".bin"),StandardOpenOption.CREATE_NEW))){out.writeObject(plan);}return new JSONObject().put("ok",true).put("token",token).put("changes",changes).put("count",plan.calls.size());
 }
 static JSONObject commit(DashboardBridge s,JSONObject a)throws Exception{
  AdministratorFeatures.paused(s);String token=a.getString("token");AdministratorFeatures.need(token.matches("[a-f0-9]{32}"),"Invalid configuration preview token");Path file=s.privateBase.resolve("configuration-plans").resolve(token+".bin"),used=file.resolveSibling(token+".used");AdministratorFeatures.need(Files.isRegularFile(file)&&!Files.exists(used),"Configuration preview expired or was already applied");Plan plan;try(ObjectInputStream in=new ObjectInputStream(Files.newInputStream(file))){in.setObjectInputFilter(ObjectInputFilter.Config.createFilter("maxdepth=100;maxrefs=1000000;maxbytes=67108864;*"));plan=(Plan)in.readObject();}
  AdministratorFeatures.need(System.currentTimeMillis()-plan.created<=300000&&plan.fingerprint.equals(fingerprint(s)),"Native configuration changed or preview expired. Preview the import again.");Files.move(file,used,StandardCopyOption.ATOMIC_MOVE);int sent=0;for(Invocation call:plan.calls){AdministratorFeatures.need(WRITES.contains(call.name),"Unsupported saved operation");IInternalController.class.getMethod(call.name,call.types).invoke(s.control(),call.args);sent++;}return new JSONObject().put("ok",true).put("count",sent).put("credentials",new JSONArray(plan.credentials));
 }
}
