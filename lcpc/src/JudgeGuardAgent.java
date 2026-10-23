import java.lang.instrument.*;
import java.security.ProtectionDomain;
import java.io.ByteArrayInputStream;
import javassist.*;
/** Linux-only runtime guard: configuration mistakes must never bypass isolation. */
public class JudgeGuardAgent {
  public static void premain(String ignored, Instrumentation inst) {
    if(!System.getProperty("os.name").equals("Linux"))throw new IllegalStateException("Linux judge required");
    inst.addTransformer(new ClassFileTransformer() {
      public byte[] transform(ClassLoader loader,String name,Class<?> old,ProtectionDomain domain,byte[] bytes) {
        if(!name.equals("edu/csus/ecs/pc2/core/execute/Executable"))return null;
        try {
          ClassPool p=new ClassPool(true);p.appendClassPath(new LoaderClassPath(loader));
          CtClass c=p.makeClass(new ByteArrayInputStream(bytes));
          String guard="{ JudgeGuardPolicy.verify(this.problem,this.language); }";
          c.getDeclaredMethod("compileProgram").insertBefore(guard);
          c.getDeclaredMethod("executeProgram").insertBefore(guard);
          byte[] out=c.toBytecode();c.detach();
          System.err.println("LCPC Linux isolation guard applied");return out;
        }catch(Throwable t){System.err.println("LCPC isolation guard failed; aborting");Runtime.getRuntime().halt(70);return null;}
      }
    });
  }
}
