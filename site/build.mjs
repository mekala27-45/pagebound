import fs from 'node:fs';import path from 'node:path';import {fileURLToPath} from 'node:url';
const here=path.dirname(fileURLToPath(import.meta.url));const root=path.dirname(here);const out=path.join(here,'dist');fs.mkdirSync(out,{recursive:true});
const read=p=>JSON.parse(fs.readFileSync(path.join(root,p),'utf8'));
const data={packets:read('artifacts/manifests/synthetic-packets.json'),renders:read('artifacts/public-small/render-manifest.json'),extraction:read('artifacts/public-small/extraction.json'),summary:read('artifacts/public-small/summary.json'),demo:read('config/api-demo-manifest.json'),api_url:process.env.PAGEBOUND_API_URL||null};
fs.mkdirSync(path.join(out,'pages'),{recursive:true});
for(const page of data.renders.pages){const file=path.basename(page.path);fs.copyFileSync(path.join(root,page.path),path.join(out,'pages',file));page.display_path='./pages/'+file;}
let html=fs.readFileSync(path.join(here,'index.html'),'utf8').replace('./src/style.css','./style.css').replace('./src/main.ts','./app.js');
html=html.replace('<script type="module"',`<script>window.PAGEBOUND_DATA=${JSON.stringify(data).replaceAll('<','\\u003c')};</script><script type="module"`);
fs.writeFileSync(path.join(out,'index.html'),html);fs.copyFileSync(path.join(here,'src/main.ts'),path.join(out,'app.js'));fs.copyFileSync(path.join(here,'src/style.css'),path.join(out,'style.css'));
const fontSpecs=[['balthazar','balthazar-latin-400-normal.woff2','Balthazar'],['anek-latin','anek-latin-latin-400-normal.woff2','Anek Latin'],['monaspace-argon','monaspace-argon-latin-400-normal.woff2','Monaspace Argon']];
let fontCss='';const fontStatus=[];
for(const [pkg,file,family] of fontSpecs){const p=path.join(here,'node_modules/@fontsource',pkg,'files',file);if(fs.existsSync(p)){fs.mkdirSync(path.join(out,'fonts'),{recursive:true});fs.copyFileSync(p,path.join(out,'fonts',file));fontCss+=`@font-face{font-family:'${family}';font-style:normal;font-weight:400;font-display:swap;src:url('./fonts/${file}') format('woff2')}\n`;fontStatus.push({family,status:'bundled'});}else fontStatus.push({family,status:'system fallback; package unavailable locally'});}
fs.appendFileSync(path.join(out,'style.css'),fontCss);fs.writeFileSync(path.join(out,'build.json'),JSON.stringify({fontStatus,render_manifest:data.renders.render_manifest_digest,model_study:'not_run'}));console.log(JSON.stringify({output:out,pages:data.renders.pages.length,fontStatus}));
if(process.argv.includes('--standalone')){
  for(const page of data.renders.pages)page.display_path='data:image/png;base64,'+fs.readFileSync(path.join(root,page.path)).toString('base64');
  let single=fs.readFileSync(path.join(here,'index.html'),'utf8');
  single=single.replace('<link rel="stylesheet" href="./src/style.css">','<style>'+fs.readFileSync(path.join(here,'src/style.css'),'utf8')+'</style>');
  single=single.replace('<script type="module" src="./src/main.ts"></script>','<script>window.PAGEBOUND_DATA='+JSON.stringify(data).replaceAll('<','\\u003c')+';</script><script type="module">'+fs.readFileSync(path.join(here,'src/main.ts'),'utf8')+'</script>');
  fs.mkdirSync(path.join(root,'outputs'),{recursive:true});fs.writeFileSync(path.join(root,'outputs/pagebound-preview.html'),single);
}
