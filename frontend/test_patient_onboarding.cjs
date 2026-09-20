const fs=require('fs'),vm=require('vm'),assert=require('assert');const src=fs.readFileSync('app.js','utf8');let selection=null,prescription=null;const nodes=new Map();
const c={exercises:['seated','supine','squat','stand'].map(id=>({id})),currentUser:{id:11,username:'new@example.test',role:'patient'},localStorage:{getItem:()=>null},renderExercises(){},$:s=>{if(!nodes.has(s))nodes.set(s,{});return nodes.get(s)},api:async p=>JSON.parse(JSON.stringify(p.includes('visual-prescription')?{prescription}:{selection}))};
vm.createContext(c);vm.runInContext(src.slice(src.indexOf('let patientTrainingSource='),src.indexOf('const $ = selector'))+src.slice(src.indexOf('function resetPatientExercises()'),src.indexOf('function openTrainingSelection()')),c);
(async()=>{
 await c.syncVisualPlan();assert.equal(c.availableExercises().length,0);
 selection={condition:'knee_osteoarthritis',exercise_ids:['seated']};await c.syncVisualPlan();assert.equal(c.availableExercises().length,1);assert.equal(c.availableExercises()[0].id,'seated');
 c.exercises[0].reps=7;await c.syncVisualPlan();assert.equal(c.exercises[0].reps,7);
 c.currentUser={id:12,username:'other@example.test',role:'patient'};selection=null;await c.syncVisualPlan();assert.equal(c.availableExercises().length,0);assert.equal(c.exercises[0].reps,10);
 c.currentUser={id:1,username:'p.zhang',role:'patient'};await c.syncVisualPlan();assert.equal(c.availableExercises().length,4);
 selection={condition:null,exercise_ids:[]};await c.syncVisualPlan();assert.equal(c.availableExercises().length,0);
 prescription={id:4,title:'方案',side:'right',phase:'测试',days_per_week:5,items:[{exercise_id:'supine',sets:3,reps:9,target_deg:30,hold_s:5,return_s:2,rest_s:30}]};await c.syncVisualPlan();assert.equal(c.availableExercises()[0].id,'supine');assert.equal(c.availableExercises()[0].reps,9);
 console.log('PASS empty new user, explicit selection, unchanged dose, account isolation, demo-only defaults, clearing and prescription precedence');
})().catch(e=>{console.error(e);process.exit(1)});
