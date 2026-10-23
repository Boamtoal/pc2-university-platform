import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.PermissionGroup;
import edu.csus.ecs.pc2.core.security.*;
import java.util.*;

/** Reserved participant identity: normal isolated judging, never an official competitor. */
public class TestTeamPolicy {
 public static final int NUMBER=99999;
 public static boolean isTest(ClientId id){return id!=null&&id.getClientType()==ClientType.Type.TEAM&&id.getClientNumber()==NUMBER;}
 public static int nextNumber(IInternalContest model){
  int n=Arrays.stream(model.getAccounts()).filter(a->a.isTeam()&&!isTest(a.getClientId())).mapToInt(a->a.getClientId().getClientNumber()).max().orElse(0)+1;
  if(n>=NUMBER)throw new IllegalArgumentException("Team capacity reached");return n;
 }
 public static Account account(int site,int number,String name,String password,boolean enabled,boolean visible){
  Account a=new Account(new ClientId(site,ClientType.Type.TEAM,number),password,site);a.setDisplayName(name);
  a.clearListAndLoadPermissions(new PermissionGroup().getPermissionList(ClientType.Type.TEAM));
  if(!enabled)a.removePermission(Permission.Type.LOGIN);
  if(!visible||isTest(a.getClientId()))a.removePermission(Permission.Type.DISPLAY_ON_SCOREBOARD);
  return a;
 }
}
