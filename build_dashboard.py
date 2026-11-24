"""Build one consistent HTML shell. Weather JSON and imagery stay independent and dated."""
from pathlib import Path
import re, subprocess, tempfile, sys
root=Path(sys.argv[1] if len(sys.argv)>1 else '_site')
p=root/'index.html'
h=p.read_text()
css_names=['v6.css','v7.css','v8.css','v9.css','v15.css']
js_names=['v6.js','v7.js','v8.js','v9.js','video-player.js','v15.js','v17.js','v18.js','v19.js','v20.js','v21.js','v22.js','v23.js','v24.js','official-forecast.js']
def replace_one(s,old,new):
    if s.count(old)!=1:raise ValueError('Expected one '+old)
    return s.replace(old,new,1)
for name in css_names:
    css=(root/name).read_text()
    if re.search(r'</style',css,re.I):raise ValueError('Unsafe style end: '+name)
    h=replace_one(h,'<link rel="stylesheet" href="'+name+'">','<style data-cyclone-asset="'+name+'">\n'+css+'\n</style>')
h=h.replace('</head>','''<style>
#startupHealth[hidden]{display:none!important}
.v151safety a{overflow-wrap:anywhere}
@media(max-width:600px){
header{gap:8px}
.v15hero,.panel{min-width:0}
.v18tools,.v16layers,.maptools{gap:6px;flex-wrap:wrap}
.v18tools button,.v16layers button,.maptools button{max-width:100%;white-space:normal}
}
</style></head>''',1)
# Preserve order: the base inline controller runs first, followed by local feature modules.
# Separate script tags prevent an error in one optional feature from blocking later modules.
scripts=[]
for name in js_names:
    js=(root/name).read_text()
    if re.search(r'</script',js,re.I):raise ValueError('Unsafe script end: '+name)
    subprocess.run(['node','--check',str(root/name)],check=True)
    h=replace_one(h,'<script src="'+name+'" defer></script>','')
    scripts.append('<script data-cyclone-asset="'+name+'">\nwindow.cycloneStartup.current='+repr(name)+';\ntry {\n'+js+'\nwindow.cycloneStartup.loaded.push('+repr(name)+');\n} catch(e) {window.cycloneStartup.errors.push('+repr(name)+');console.error("Dashboard module failed",'+repr(name)+',e);}\n</script>')
startup='''<script>window.cycloneStartup={loaded:[],errors:[],current:null};</script>'''
finish='''<script>
(function(){
const s=window.cycloneStartup,el=document.getElementById('startupHealth');
if(s.errors.length||s.loaded.length!==15){
el.textContent='Some dashboard controls could not start: '+(s.errors.join(', ')||'incomplete startup')+'. Reload or consult official MMS sources.';
}else{el.hidden=true;}
window.cycloneStartup.current=null;
document.documentElement.dataset.dashboardStartup=s.errors.length?'partial':'ready';
})();
</script>'''
h=replace_one(h,'</body></html>',startup+'\n'+'\n'.join(scripts)+'\n'+finish+'</body></html>')
assert all('data-cyclone-asset="'+name+'"' in h for name in css_names+js_names)
assert h.index("const snapshot=")<h.index('data-cyclone-asset="v6.js"')
p.write_text(h)
print('PASS V24.1 bundled shell: 5 local stylesheets, 15 independent dashboard modules; weather data not embedded')
