import test from 'node:test';import assert from 'node:assert/strict';import {createHmac} from 'node:crypto';
import {validateDevice,power,requireAdmin,verifyWebhook,capturedPayment,CAP,INITIAL,issuedAt,rewardAt} from '../domain.js';
const miner={id:'M1',name:'Nova',family:'Nova',kind:'miner',virtualSpeed:400,virtualWatts:1200,pricePaise:2499900,published:true};
test('client cannot grant itself administrator access',()=>{
  for(const a of [null,{uid:'x',token:{}},{uid:'x',token:{admin:'true'}}])assert.throws(()=>requireAdmin(a));
  assert.doesNotThrow(()=>requireAdmin({uid:'x',token:{admin:true}}));
});
test('reject forged catalog stats and invalid numbers',()=>{
  for(const delta of [{pricePaise:-1},{virtualWatts:0},{virtualSpeed:NaN},{pricePaise:1.1},{kind:'token'},{name:''}])
    assert.throws(()=>validateDevice({...miner,...delta}));assert.equal(validateDevice(miner).pricePaise,2499900);
});
test('power is proportional and stops with generator disabled',()=>{
 const gen={...miner,id:'G1',kind:'generator',virtualWatts:600};
 const fleet=[{catalogId:'M1',enabled:true},{catalogId:'G1',enabled:true}];
 assert.equal(power([miner,gen],fleet).speed,200);fleet[1].enabled=false;
 assert.equal(power([miner,gen],fleet).speed,0);fleet[0].enabled=false;
 assert.equal(power([miner,gen],fleet).demand,0);
});
test('webhooks bind raw bytes and reject altered signatures',()=>{
 const raw=Buffer.from('{"event":"payment.captured"}'),secret='test-webhook-key';
 const sig=createHmac('sha256',secret).update(raw).digest('hex');
 assert.equal(verifyWebhook(raw,sig,secret),true);
 assert.equal(verifyWebhook(Buffer.from('tamper'),sig,secret),false);
 assert.equal(verifyWebhook(raw,'bad',secret),false);
});
test('payment validation checks frozen amount, currency, order and duplicate',()=>{
 const order={providerOrderId:'order_test',amountPaise:200,status:'pending'};
 const payment={id:'pay_test',order_id:'order_test',amount:200,status:'captured',currency:'INR'};
 const event=p=>({event:'payment.captured',payload:{payment:{entity:p}}});
 assert.equal(capturedPayment(event(payment),order).duplicate,false);
 for(const delta of [{amount:1},{currency:'USD'},{order_id:'wrong'},{status:'authorized'}])assert.throws(()=>capturedPayment(event({...payment,...delta}),order));
 assert.equal(capturedPayment(event(payment),{...order,status:'fulfilled'}).duplicate,true);
});
test('emission starts at 2400, decreases, conserves and never exceeds 2B',()=>{
 assert.equal(rewardAt(1),INITIAL);let sum=0n,previous=INITIAL;
 for(let n=1;n<=10000;n++){const r=rewardAt(n);assert.ok(r<=previous);sum+=r;previous=r;}
 assert.equal(sum,issuedAt(10000));assert.ok(issuedAt(10n**18n)<CAP);assert.throws(()=>rewardAt(0));
});
