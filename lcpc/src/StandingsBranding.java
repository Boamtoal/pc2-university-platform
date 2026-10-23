import java.awt.*;
import java.awt.image.BufferedImage;
import java.nio.file.*;
import javax.imageio.ImageIO;
import javax.swing.*;
/** Adds the supplied organizer logos above the original PC2 standings widget. */
public class StandingsBranding {
 public static void install(JPanel pane) {
  String path=System.getProperty("lcpc.branding","");
  if(path.isEmpty() || Boolean.TRUE.equals(pane.getClientProperty("lcpc.branding.installed")))return;
  try {
   JPanel logos=new JPanel(new FlowLayout(FlowLayout.CENTER,30,10));
   logos.setName("LCPC OMU standings logos");logos.setBackground(Color.WHITE);
   logos.setBorder(BorderFactory.createMatteBorder(0,0,2,0,new Color(25,63,109)));
   logos.add(logo(Path.of(path,"lcpc-logo.png"),"LCPC OMU Programming Contest",150,150));
   logos.add(logo(Path.of(path,"omu-logo.png"),"Omar Al-Mukhtar University",230,172));
   if(!(pane.getLayout() instanceof BorderLayout))throw new IllegalStateException("Unexpected standings layout");
   BorderLayout layout=(BorderLayout)pane.getLayout();Component previous=layout.getLayoutComponent(BorderLayout.NORTH);
   JPanel top=new JPanel(new BorderLayout());top.setBackground(Color.WHITE);top.add(logos,BorderLayout.NORTH);
   if(previous!=null){pane.remove(previous);top.add(previous,BorderLayout.SOUTH);}
   pane.add(top,BorderLayout.NORTH);pane.putClientProperty("lcpc.branding.installed",Boolean.TRUE);
   pane.revalidate();pane.repaint();
  }catch(Exception e){System.err.println("LCPC standings logos unavailable: "+e.getClass().getSimpleName());}
 }
 private static JLabel logo(Path path,String name,int maxWidth,int maxHeight)throws Exception {
  BufferedImage original=ImageIO.read(path.toFile());
  if(original==null)throw new IllegalArgumentException("Invalid logo image");
  double scale=Math.min((double)maxWidth/original.getWidth(),(double)maxHeight/original.getHeight());
  int w=(int)Math.round(original.getWidth()*scale),h=(int)Math.round(original.getHeight()*scale);
  BufferedImage image=new BufferedImage(w,h,BufferedImage.TYPE_INT_ARGB);Graphics2D g=image.createGraphics();
  g.setRenderingHint(RenderingHints.KEY_INTERPOLATION,RenderingHints.VALUE_INTERPOLATION_BICUBIC);
  g.drawImage(original,0,0,w,h,null);g.dispose();
  JLabel label=new JLabel(new ImageIcon(image));label.setToolTipText(name);label.getAccessibleContext().setAccessibleName(name);return label;
 }
}
