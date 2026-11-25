const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('app.js','utf8');const nodes=new Map();let response;
const c={exercises:[{id:'seated'},{id:'supine'},{id:'squat'},{id:'stand'}],currentUser:{id:3,role:'patient'},patientSide:'left',api:async()=>JSON.parse(JSON.stringify(response)),renderExercises(){},localStorage:{getItem:()=>null},$:s=>{if(!nodes.has(s))nodes.set(s,{});return nodes.get(s)}};
vm.createContext(c);vm.runInContext(source.slice(source.indexOf('let patientTrainingSource='),source.indexOf('const $ = selector'))+source.slice(source.indexOf('function resetPatientExercises()'),source.indexOf('function openTrainingSelection()')),c);
vm.runInContext(source.slice(source.indexOf('function defaultTargets('),source.indexOf('function targetDescription(')),c);
assert.equal(c.defaultTargets('seated').hold_s,1);
assert.equal(c.defaultTargets('supine').hold_s,5);
(async()=>{
 response={prescription:{id:1,title:'方案',side:'right',phase:'测试',days_per_week:4,notes:'慢慢放下',items:[{exercise_id:'seated',sets:4,reps:12,target_deg:175,hold_s:4,return_s:2,rest_s:40}]}};
 assert(await c.syncVisualPlan());assert.equal(c.availableExercises().length,1);assert.equal(c.exercises[0].targets.hold_s,4);assert.equal(c.patientSide,'right');assert.equal(c.exercises[0].groups,4);
 c.exercises[0].reps=7;await c.syncVisualPlan();assert.equal(c.exercises[0].reps,7,'same version preserves patient dose');
 response.prescription.id=2;await c.syncVisualPlan();assert.equal(c.exercises[0].reps,12,'new published version applies');
 response={prescription:null};await c.syncVisualPlan();assert.equal(c.availableExercises().length,0);assert.equal(c.exercises[0].targets,undefined);
 assert(source.includes('result.training_session.prescription_snapshot=activePrescriptionSnapshot'));
 assert(source.includes('targets:activeExercise.targets||defaultTargets(activeExercise.id)'));
 console.log('PASS plan selection, thresholds, version refresh, independent dose, unlink reset and frozen report wiring');
})().catch(e=>{console.error(e);process.exit(1)});

