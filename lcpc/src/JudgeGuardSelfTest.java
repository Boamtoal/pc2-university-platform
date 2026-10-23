import java.lang.reflect.*;
import sun.misc.Unsafe;
import edu.csus.ecs.pc2.core.model.*;
import edu.csus.ecs.pc2.core.execute.Executable;
/** Trusted test: invalid configuration must throw before vendor execution begins. */
public class JudgeGuardSelfTest {
 public static void main(String[] args)throws Exception {
  Field u=Unsafe.class.getDeclaredField("theUnsafe");u.setAccessible(true);
  Executable target=(Executable)((Unsafe)u.get(null)).allocateInstance(Executable.class);
  Problem p=new Problem("guard probe");p.setTimeOutInSeconds(5);p.setMemoryLimitMB(128);
  Language l=new Language("guard probe");l.setCompileCommandLine("/opt/lcpc/bin/compile17 {:mainfile} {:basename}");l.setProgramExecuteCommandLine("./{:basename}");l.setExecutableIdentifierMask("{:basename}");
  for(String n:new String[]{"problem","language"}){Field f=Executable.class.getDeclaredField(n);f.setAccessible(true);f.set(target,n.equals("problem")?p:l);}
  refused(target,"compileProgram",new Class<?>[0],new Object[0]);
  p.setSandboxType(Problem.SandboxType.PC2_INTERNAL_SANDBOX);JudgeGuardPolicy.verify(p,l);
  if(args.length>0 && args[0].equals("deny-all")){
   refused(target,"compileProgram",new Class<?>[0],new Object[0]);
   refused(target,"executeProgram",new Class<?>[]{int.class},new Object[]{0});
   System.out.println("VERIFIED: macOS compile/run denied even for a valid isolated configuration");
  }
  l.setCompileCommandLine("/bin/true");refused(target,"compileProgram",new Class<?>[0],new Object[0]);
  refused(target,"executeProgram",new Class<?>[]{int.class},new Object[]{0});
  System.out.println("VERIFIED: missing sandbox and unsafe compiler refused before compile/run");
  l.setCompileCommandLine("/opt/lcpc/bin/compilepython {:mainfile} {:basename}.lcpcpy");
  l.setProgramExecuteCommandLine("/opt/lcpc/bin/runpython {:basename}.lcpcpy");l.setExecutableIdentifierMask("{:basename}.lcpcpy");
  JudgeGuardPolicy.verify(p,l);
  if(args.length>0 && args[0].equals("deny-all")){
   refused(target,"compileProgram",new Class<?>[0],new Object[0]);
   refused(target,"executeProgram",new Class<?>[]{int.class},new Object[]{0});
  }
  l.setProgramExecuteCommandLine("/usr/bin/python3 {:mainfile}");refused(target,"executeProgram",new Class<?>[]{int.class},new Object[]{0});
  System.out.println("VERIFIED: Python requires the approved isolated runner");
 }
 static void refused(Object target,String name,Class<?>[] types,Object[] args)throws Exception {
  Method m=Executable.class.getDeclaredMethod(name,types);m.setAccessible(true);
  try{m.invoke(target,args);throw new AssertionError("Guard did not reject unsafe settings");}
  catch(InvocationTargetException e){if(!(e.getCause() instanceof SecurityException))throw e;}
 }
}
