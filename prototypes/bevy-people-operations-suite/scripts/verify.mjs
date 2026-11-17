import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),mode=process.argv[2]||'all';
function run(command,args){const p=spawnSync(command,args,{cwd:root,stdio:'inherit'});if(p.status!==0)process.exit(p.status??1);}
const npm=process.platform==='win32'?'npm.cmd':'npm';
if(['check','all'].includes(mode)){
 run(process.execPath,['scripts/check.mjs']);
 for(const app of ['hr-portal','expenses','insurance','daily-updates'])run(npm,['--prefix','apps/'+app,'run','check']);
}
if(['test','all'].includes(mode)){
 for(const app of ['hr-portal','expenses','insurance','daily-updates'])run(npm,['--prefix','apps/'+app,'test']);
 run(process.execPath,['--test','tests/suite.test.mjs']);
}
if(mode==='all')run(npm,['--prefix','apps/daily-updates','run','test:database']);
if(['build','all'].includes(mode)){run(process.execPath,['scripts/check.mjs']);run(npm,['--prefix','apps/hr-portal','run','build']);}
if(!['check','test','build','all'].includes(mode))throw Error('Unknown verification mode: '+mode);
