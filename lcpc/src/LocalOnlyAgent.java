import java.lang.instrument.*;
import java.security.ProtectionDomain;
import java.io.ByteArrayInputStream;
import javassist.*;
import javassist.expr.*;

/** Limits the unmodified vendor binaries to loopback. Fails closed on transform errors. */
public class LocalOnlyAgent {
  public static void premain(String ignored, Instrumentation inst) {
    inst.addTransformer(new ClassFileTransformer() {
      public byte[] transform(ClassLoader loader, String name, Class<?> old, ProtectionDomain domain, byte[] bytes) {
        boolean testAccountPolicy=name.equals("edu/csus/ecs/pc2/core/model/Account");
        boolean testBalloons=name.equals("edu/csus/ecs/pc2/core/util/BalloonHandler");
        boolean denyExecution=Boolean.getBoolean("lcpc.denyExecution") && name.equals("edu/csus/ecs/pc2/core/execute/Executable");
        boolean standingsBranding=!System.getProperty("lcpc.branding","").isEmpty() && (name.equals("edu/csus/ecs/pc2/ui/StandingsPane") || name.equals("edu/csus/ecs/pc2/ui/StandingsHTMLPane"));
        if (!testAccountPolicy && !testBalloons && !denyExecution && !standingsBranding && !name.equals("edu/csus/ecs/pc2/core/transport/ConnectionHandler") &&
            !name.equals("org/eclipse/jetty/server/ServerConnector")) return null;
        try {
          ClassPool p = new ClassPool(true);
          p.appendClassPath(new LoaderClassPath(loader));
          CtClass c = p.makeClass(new ByteArrayInputStream(bytes));
          if (testAccountPolicy) {
            c.getDeclaredMethod("isAllowed").insertBefore("{ if ($1 == edu.csus.ecs.pc2.core.security.Permission.Type.DISPLAY_ON_SCOREBOARD && TestTeamPolicy.isTest(getClientId())) return false; }");
          } else if (testBalloons) {
            c.getDeclaredMethod("shouldSendBalloon").insertBefore("{ if (TestTeamPolicy.isTest($1.getSubmitter())) return false; }");
          } else if (standingsBranding) {
            c.getDeclaredMethod("initialize").insertAfter("{ StandingsBranding.install(this); }");
          } else if (denyExecution) {
            String refusal="{ MacExecutionPolicy.deny(); }";
            c.getDeclaredMethod("compileProgram").insertBefore(refusal);
            c.getDeclaredMethod("executeProgram").insertBefore(refusal);
          } else if (name.endsWith("ConnectionHandler")) {
            final int[] count = {0};
            c.instrument(new ExprEditor() {
              public void edit(NewExpr e) throws CannotCompileException {
                if (e.getClassName().equals("java.net.ServerSocket") && e.getSignature().equals("(I)V")) {
                  e.replace("{ $_ = new java.net.ServerSocket($1, 50, java.net.InetAddress.getByName(\"127.0.0.1\")); }");
                  count[0]++;
                }
              }
            });
            if (count[0] != 1) throw new IllegalStateException("Unexpected PC2 transport binary");
          } else {
            c.getDeclaredMethod("open", new CtClass[0]).insertBefore("{ setHost(\"127.0.0.1\"); }");
          }
          byte[] out = c.toBytecode(); c.detach();
          System.err.println("LCPC loopback protection applied: " + name);
          return out;
        } catch (Throwable t) {
          System.err.println("LCPC loopback protection failed; aborting.");
          Runtime.getRuntime().halt(70); return null;
        }
      }
    });
  }
}
