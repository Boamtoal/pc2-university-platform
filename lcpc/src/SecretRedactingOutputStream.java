import java.io.*;
import java.nio.charset.StandardCharsets;
import java.util.Properties;
/** Removes credentials from vendor console messages before they reach log files. */
public class SecretRedactingOutputStream extends OutputStream {
  private final OutputStream out;
  private final Properties secrets;
  private final ByteArrayOutputStream line = new ByteArrayOutputStream();
  public SecretRedactingOutputStream(OutputStream out,Properties secrets){this.out=out;this.secrets=secrets;}
  public synchronized void write(int b)throws IOException {
    line.write(b);
    if(b=='\n')emit();
  }
  private void emit()throws IOException {
    String text=line.toString(StandardCharsets.UTF_8);
    for(Object value:secrets.values())text=text.replace(value.toString(),"[REDACTED]");
    out.write(text.getBytes(StandardCharsets.UTF_8));line.reset();out.flush();
  }
  public synchronized void close()throws IOException{if(line.size()>0)emit();out.flush();}
}
