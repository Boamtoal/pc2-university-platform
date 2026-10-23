import java.util.*;
import java.nio.file.*;
import java.io.*;
/** Reads local secrets inside the JVM, keeping passwords out of process arguments. */
public class LCPCLaunch {
  public static Properties secrets() throws Exception {
    Properties p=new Properties();
    try(InputStream s=Files.newInputStream(Path.of(System.getProperty("lcpc.secrets")))) { p.load(s); }
    return p;
  }
  public static void main(String[] args) throws Exception {
    Properties p=secrets(); String mode=args[0];
    System.setOut(new java.io.PrintStream(new SecretRedactingOutputStream(System.out,p),true));
    System.setErr(new java.io.PrintStream(new SecretRedactingOutputStream(System.err,p),true));
    if(mode.equals("wti")) {
      Class.forName("config.JettyConfig").getMethod("main", String[].class).invoke(null,(Object)new String[0]); return;
    }
    List<String> a=new ArrayList<>();
    if(mode.equals("server")) {
      Collections.addAll(a,"--server","--nogui","--login","site1","--password",p.getProperty("site1"),"--contestpassword",p.getProperty("contest"));
      if(args.length>1 && args[1].equals("bootstrap")) Collections.addAll(a,"--load",System.getProperty("lcpc.cdp"));
    } else {
      String user=mode.equals("admin")?"administrator1":mode.equals("judge")?"judge1":mode.equals("board")?"scoreboard1":mode;
      Collections.addAll(a,"--login",user,"--password",p.getProperty(user));
      if(mode.equals("judge")) a.add("--nogui");
    }
    edu.csus.ecs.pc2.Starter.main(a.toArray(new String[0]));
  }
}
