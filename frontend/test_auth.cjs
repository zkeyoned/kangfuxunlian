const fs=require('fs'),vm=require('vm'),assert=require('assert');
const src=fs.readFileSync('app.js','utf8');
const nodes=new Map(),handlers={},store=new Map();
function $(id){if(!nodes.has(id))nodes.set(id,{value:'',textContent:'',disabled:false,reset(){},querySelector(){return $('button'+id)},addEventListener(k,fn){handlers[id]=fn}});return nodes.get(id)}
const c={passwordCompliant:v=>v.length>=5&&v.length<=15&&/[A-Za-z]/.test(v)&&/[0-9]/.test(v),openPasswordReset:a=>{c.resetAccount=a},$,fetch:async()=>({ok:false,status:401,json:async()=>({error:'用户名或密码错误'})}),sessionStorage:{setItem(k,v){store.set(k,v)},removeItem(k){store.delete(k)}},TypeError,showToast(){},enterApp(u){c.entered=u},apiUser:u=>u,syncBackendData:async()=>{},setRole(){},showAuthScreen(){}};
vm.createContext(c);
vm.runInContext(src.match(/function passwordCompliant\(value\)\{[^\n]+/)[0],c);
assert(c.passwordCompliant('abc12'));assert(c.passwordCompliant('abc123456789012'));assert(!c.passwordCompliant('abc1'));assert(!c.passwordCompliant('abc1234567890123'));
const apiStart=src.indexOf('async function api('),apiEnd=src.indexOf('function apiUser(',apiStart);
const formStart=src.indexOf('$("#login-form").addEventListener'),formEnd=src.indexOf('$("#message-form").addEventListener',formStart);
vm.runInContext('let apiToken="",selectedLoginRole="patient",selectedRegisterRole="patient";const API_BASE="test";'+src.slice(apiStart,apiEnd)+src.slice(formStart,formEnd),c);
async function submit(id){await handlers[id]({preventDefault(){},currentTarget:$(id)})}
(async()=>{
  $('#login-account').value='test@example.test';$('#login-password').value='test-only-1234';await submit('#login-form');
  assert($('#login-error').textContent.includes('账号或密码'));assert(!$('#login-error').textContent.includes('启动'));assert(!$('#login-form').querySelector().disabled);
  c.fetch=async()=>({ok:true,json:async()=>({token:'test-token',user:{role:'patient'}})});c.syncBackendData=async()=>{throw new Error('plan unavailable')};
  await submit('#login-form');assert(c.entered);assert.equal(store.get('kangshifu_api_token'),'test-token');
  $('#register-name').value='测试';$('#register-account').value='new@example.test';$('#register-password').value='test-only-1234';$('#register-confirm').value='different';
  await submit('#register-form');assert($('#register-error').textContent.includes('不一致'));
  $('#register-confirm').value='test-only-1234';let body;
  c.fetch=async(url,options)=>{assert(url.endsWith('/auth/register'));body=JSON.parse(options.body);return {ok:true,json:async()=>({ok:true,username:body.username,role:'patient'})}};
  await submit('#register-form');assert.equal(body.display_name,'测试');assert.equal($('#login-account').value,'new@example.test');assert($('#login-error').textContent.includes('注册成功'));
  c.fetch=async()=>({ok:false,status:409,json:async()=>({error:'该手机号或邮箱已注册，请返回登录'})});await submit('#register-form');assert($('#register-error').textContent.includes('已注册'));
  c.fetch=async()=>({ok:false,status:403,json:async()=>({code:'PASSWORD_RESET_REQUIRED',error:'请重设密码'})});await submit('#login-form');assert.equal(c.resetAccount,$('#login-account').value);
  for(const weak of ['12345678','abcdefgh','abc1','abc1234567890123']){$('#register-password').value=weak;await submit('#register-form');assert($('#register-error').textContent.includes('5–15'));}
  console.log('PASS: login errors, valid token on data failure, password confirmation, real registration request, duplicate account');
})().catch(e=>{console.error(e);process.exit(1)});

