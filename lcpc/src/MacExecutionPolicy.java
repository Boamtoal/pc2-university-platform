/** Fail closed before any participant compiler or executable runs on Mac. */
public class MacExecutionPolicy {
 public static void deny(){throw new SecurityException("LCPC: participant compile/run is disabled on macOS in isolated mode");}
}
