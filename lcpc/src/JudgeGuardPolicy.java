import edu.csus.ecs.pc2.core.model.*;
/** Fixed compile/run profiles; participant execution stays inside Linux. */
public class JudgeGuardPolicy {
  public static void verify(Problem problem,Language language) {
    boolean safe=problem!=null && language!=null && problem.getSandboxType()==Problem.SandboxType.PC2_INTERNAL_SANDBOX
      && !problem.isInteractive() && problem.getTimeOutInSeconds()>=1 && problem.getTimeOutInSeconds()<=10
      && problem.getMemoryLimitMB()>=32 && problem.getMemoryLimitMB()<=1024
      && "pc2sandbox.sh".equals(problem.getSandboxProgramName())
      && "./{:sandboxprogramname} {:memlimit} {:timelimit}".equals(problem.getSandboxCmdLine());
    if(safe){
      String compile=language.getCompileCommandLine();
      boolean cpp=("/opt/lcpc/bin/compile17 {:mainfile} {:basename}".equals(compile) || "/opt/lcpc/bin/compile20 {:mainfile} {:basename}".equals(compile))
        && "./{:basename}".equals(language.getProgramExecuteCommandLine())
        && "{:basename}".equals(language.getExecutableIdentifierMask())
        && !language.isInterpreted() && !language.isUsingJudgeProgramExecuteCommandLine();
      boolean python="/opt/lcpc/bin/compilepython {:mainfile} {:basename}.lcpcpy".equals(compile)
        && "/opt/lcpc/bin/runpython {:basename}.lcpcpy".equals(language.getProgramExecuteCommandLine())
        && "{:basename}.lcpcpy".equals(language.getExecutableIdentifierMask())
        && !language.isInterpreted() && !language.isUsingJudgeProgramExecuteCommandLine();
      safe=cpp || python;
    }
    if(!safe)throw new SecurityException("LCPC refused judging: sandbox or compiler configuration is outside tested policy");
  }
}
