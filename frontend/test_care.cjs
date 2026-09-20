const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8'),html=fs.readFileSync('index.html','utf8');
const nodes=new Map(),handlers={};
function $(id){assert(html.includes(`id="${id.slice(1)}"`));if(!nodes.has(id))nodes.set(id,{value:'',addEventListener(event,fn){handlers[id]=fn},querySelector(){return {disabled:false}}});return nodes.get(id)}
let response={connections:[],requests:[]};const calls=[];
const c={$,currentUser:{id:5,role:'patient',name:'患者',username:'patient@example.test'},api:async(path,opt)=>{calls.push([path,opt]);return response},showToast(){},syncBackendData:async()=>{},window:{confirm:()=>true}};vm.createContext(c);
const escape=src.split(/\r?\n/).find(s=>s.startsWith('function escapeHtml('));
vm.runInContext(escape+'\n'+src.slice(src.indexOf('async function loadCareConnections('),src.indexOf('renderExercises(); renderFeedback(); renderTherapist();')),c);
(async()=>{
 await c.loadCareConnections();assert($('#care-linked').innerHTML.includes('暂无关联'));assert($('#care-my-account').textContent.includes('patient@example.test'));
 response={connections:[{patient_id:9,therapist_name:'<script>bad</script>',patient_name:'患者'}],requests:[{id:1,recipient_id:5,sender_id:8,sender_name:'医生',created_at:'test'}]};await c.loadCareConnections();assert($('#care-linked').innerHTML.includes('&lt;script&gt;'));assert($('#care-requests').innerHTML.includes('接受关联'));
 response={users:[{id:8,display_name:'医生',role:'therapist'}]};$('#care-search-account').value='doctor@example.test';await handlers['#care-search-form']({preventDefault(){},currentTarget:$('#care-search-form')});assert(calls.at(-1)[0]==='/care/search');assert($('#care-search-results').innerHTML.includes('申请关联'));
 response={connections:[],requests:[]};await handlers['#care-connections']({target:{closest:()=>({dataset:{careAction:'accept',careRequest:'1'}})}});assert(calls.some(([p,o])=>p.endsWith('/1/respond')&&o.body.action==='accept'));
 c.currentUser={id:8,role:'therapist',name:'医生',username:'doctor@example.test'};await c.loadCareConnections();assert.equal($('#care-title').textContent,'我的患者');
 console.log('PASS: both role views, search, incoming acceptance wiring and escaped names');
})().catch(e=>{console.error(e);process.exit(1)});
