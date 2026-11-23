import {spawnSync} from 'node:child_process';
import {fileURLToPath} from 'node:url';
const root=fileURLToPath(new URL('../',import.meta.url)),mode=process.argv[2]||'all';
function run(command,args){if(command==='npm'&&process.platform==='win32'){if(!process.env.npm_execpath)throw Error('Launch verification using npm run so npm_execpath is available.');args=[process.env.npm_execpath,...args];command=process.execPath;}const p=spawnSync(command,args,{cwd:root,stdio:'inherit'});if(p.status!==0)process.exit(p.status??1);}
const npm='npm';
if(['check','all'].includes(mode)){
 run(process.execPath,['scripts/check.mjs']);
 for(const app of ['hr-portal','expenses','insurance','daily-updates'])run(npm,['--prefix','apps/'+app,'run','check']);
}
if(['test','all'].includes(mode)){
 for(const app of ['hr-portal','expenses','insurance','daily-updates'])run(npm,['--prefix','apps/'+app,'test']);
 run(process.execPath,['--test','tests/suite.test.mjs','tests/review-regressions.test.mjs']);
}
if(mode==='all'){if(process.env.BEVY_DAILY_SQL_DIR)run(npm,['--prefix','apps/daily-updates','run','test:database']);else console.log('SKIP: optional Daily Updates SQL check (private fixtures unavailable). Set BEVY_DAILY_SQL_DIR and run npm run test:database.');}
if(['build','all'].includes(mode)){run(process.execPath,['scripts/check.mjs']);run(npm,['--prefix','apps/hr-portal','run','build']);}
if(!['check','test','build','all'].includes(mode))throw Error('Unknown verification mode: '+mode);
