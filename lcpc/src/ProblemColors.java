import edu.csus.ecs.pc2.core.model.*;
import org.json.JSONObject;

/** Problem color is canonical; explicit edits also update native balloon delivery maps. */
final class ProblemColors {
 static void validate(String name,String rgb){
  DashboardBridge.require(name!=null&&!name.isBlank()&&name.length()<=80&&!name.contains("\0"),"Use a balloon color name of 1–80 characters");
  DashboardBridge.require(rgb!=null&&rgb.matches("#[0-9A-Fa-f]{6}"),"Use a balloon color in #RRGGBB format");
 }
 static boolean apply(Problem p,JSONObject args)throws Exception{
  boolean requested=args.has("colorName")||args.has("colorRGB");
  if(requested){String name=args.getString("colorName"),rgb=args.getString("colorRGB");validate(name,rgb);p.setColorName(name.trim());p.setColorRGB(rgb);}
  return requested;
 }
 static void sync(DashboardBridge s,Problem p)throws Exception{
  for(BalloonSettings old:s.model().getBalloonSettings()){
   BalloonSettings settings=AdministratorFeatures.copy(old);settings.addColor(p,p.getColorName(),p.getColorRGB());s.control().updateBalloonSettings(settings);
  }
 }
}
