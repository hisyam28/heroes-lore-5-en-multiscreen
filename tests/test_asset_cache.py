"""JVM models using the actual cache predicate and async startup guard."""
from pathlib import Path
import subprocess
import tempfile
import unittest
from test_android_startup import ACTIVITY,JDKS,extract_method

ROOT=Path(__file__).resolve().parents[1]


@unittest.skipUnless(ACTIVITY.exists() and JDKS,'Requires local staged Activity and JDK')
class AssetCacheModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary=tempfile.TemporaryDirectory(prefix='asset-cache-',dir=ROOT/'work')
        cls.addClassCleanup(cls.temporary.cleanup)
        cls.directory=Path(cls.temporary.name)
        main=ACTIVITY.parent
        cache=extract_method((main/'TargetAssets.java').read_text(encoding='utf-8'),'static boolean cacheMatches(')
        activity=(main/'MainActivity.java').read_text(encoding='utf-8')
        guard=extract_method(activity,'private void startGameView(')
        guard=guard[:guard.index('android.media.AudioAttributes')]+'''glSurfaceView=new Object(); starts++;
    }'''
        jsondir=cls.directory/'org/json';jsondir.mkdir(parents=True)
        (jsondir/'JSONObject.java').write_text('''package org.json;
public class JSONObject {
    java.util.HashMap<String,Object> values=new java.util.HashMap<>();
    public JSONObject put(String key,Object value){values.put(key,value);return this;}
    public String optString(String key){Object value=values.get(key);return value instanceof String?(String)value:"";}
    public long optLong(String key,long fallback){Object value=values.get(key);return value instanceof Number?((Number)value).longValue():fallback;}
}''',encoding='utf-8')
        harness='''import java.io.*;import org.json.JSONObject;
public class CacheHarness {
    private boolean filesPrepared=false,activityResumed=false,finishing=false,destroyed=false;
    private Object glSurfaceView=null;private int starts=0;
    private boolean isFinishing(){return finishing;}
    private boolean isDestroyed(){return destroyed;}
    CACHE
    GUARD
    public static void main(String[] args)throws Exception{
        CacheHarness harness=new CacheHarness();String scenario=args[0];
        if(scenario.startsWith("startup_")){
            if(scenario.equals("startup_files_first"))harness.filesPrepared=true;
            if(scenario.equals("startup_resume_first"))harness.activityResumed=true;
            harness.startGameView();if(harness.starts!=0)throw new AssertionError("Premature renderer");
            harness.filesPrepared=true;harness.activityResumed=true;
            harness.finishing=scenario.equals("startup_finishing");harness.destroyed=scenario.equals("startup_destroyed");
            harness.startGameView();harness.startGameView();
            int expected=harness.finishing||harness.destroyed?0:1;
            if(harness.starts!=expected)throw new AssertionError("Startup ordering/re-entry");return;
        }
        File file=new File(args[1]);try(FileOutputStream output=new FileOutputStream(file)){output.write(new byte[]{1,2,3});}
        JSONObject stamp=new JSONObject().put("sha256","abc").put("length",file.length()).put("modified",file.lastModified());
        if(!cacheMatches(file,stamp,"abc"))throw new AssertionError("Verified cache rejected");
        if(scenario.equals("changed_hash")){if(cacheMatches(file,stamp,"def"))throw new AssertionError("New fingerprint skipped");}
        if(scenario.equals("changed_file")){
            try(FileOutputStream output=new FileOutputStream(file)){output.write(1);}
            if(cacheMatches(file,stamp,"abc"))throw new AssertionError("Changed file skipped");
        }
        if(scenario.equals("changed_time")){
            if(!file.setLastModified(file.lastModified()-10000))throw new AssertionError("Timestamp setup failed");
            if(cacheMatches(file,stamp,"abc"))throw new AssertionError("Changed timestamp skipped");
        }
        if(scenario.equals("missing")){
            if(cacheMatches(file,null,"abc"))throw new AssertionError("Missing stamp accepted");
            if(!file.delete())throw new AssertionError();
            if(cacheMatches(file,stamp,"abc"))throw new AssertionError("Missing file accepted");
        }
    }
}'''.replace('CACHE',cache).replace('GUARD',guard)
        (cls.directory/'CacheHarness.java').write_text(harness,encoding='utf-8')
        result=subprocess.run([str(JDKS[0]),'-encoding','UTF-8','-d',str(cls.directory),
            *map(str,cls.directory.rglob('*.java'))],capture_output=True,text=True)
        if result.returncode:raise RuntimeError(result.stderr)

    def scenario(self,name):
        result=subprocess.run([str(JDKS[0].with_name('java.exe')),'-cp',str(self.directory),
            'CacheHarness',name,str(self.directory/'asset.bin')],capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)

    def test_unchanged_private_asset_uses_verified_metadata(self):self.scenario('unchanged')
    def test_changed_hash_file_or_timestamp_requires_verification(self):
        for name in ('changed_hash','changed_file','changed_time','missing'):
            with self.subTest(name=name):self.scenario(name)
    def test_async_asset_and_resume_order_start_renderer_once(self):
        for name in ('startup_files_first','startup_resume_first','startup_finishing','startup_destroyed'):
            with self.subTest(name=name):self.scenario(name)


if __name__=='__main__':unittest.main()
