import { createHmac, timingSafeEqual } from 'node:crypto';

export function validateDevice(input) {
  if (!input || typeof input !== 'object') throw new Error('Invalid equipment');
  const { id, name, family, kind, virtualSpeed, virtualWatts, pricePaise, published, tier=1, modelVariant=1 } = input;
  if (typeof id!=='string'||!/^[a-zA-Z0-9_-]{1,80}$/.test(id)||
    typeof name!=='string'||name.trim().length<1||name.length>80||
    typeof family!=='string'||family.trim().length<1||family.length>40||
    !['miner','generator'].includes(kind)||typeof published!=='boolean') throw new Error('Invalid equipment identity');
  for(const v of [virtualSpeed,virtualWatts,pricePaise,tier,modelVariant])
    if(!Number.isSafeInteger(v)||v<0||v>1_000_000_000) throw new Error('Invalid numeric value');
  if(virtualWatts===0||pricePaise===0||tier===0||modelVariant===0||kind==='miner'&&virtualSpeed===0)
    throw new Error('Positive values required');
  return {id,name:name.trim(),family:family.trim(),kind,virtualSpeed:kind==='generator'?0:virtualSpeed,
    virtualWatts,pricePaise,published,tier,modelVariant};
}
export function requireAdmin(auth) {
  if(!auth?.uid||auth.token?.admin!==true) throw new Error('Administrator access required');
}
export function power(catalog,fleet) {
  const byId=new Map(catalog.map(d=>[d.id,d]));let supply=0,demand=0,speed=0;
  for(const o of fleet) {if(o.enabled!==true)continue;const d=byId.get(o.catalogId);if(!d)continue;
    if(d.kind==='generator')supply+=d.virtualWatts;else {demand+=d.virtualWatts;speed+=d.virtualSpeed;}}
  return {supply,demand,speed:demand===0?0:Math.floor(speed*Math.min(1,supply/demand))};
}
export function verifyWebhook(raw,signature,secret) {
  if(typeof signature!=='string'||!/^[a-f0-9]{64}$/i.test(signature)||!secret) return false;
  const expected=createHmac('sha256',secret).update(raw).digest();
  return timingSafeEqual(expected,Buffer.from(signature,'hex'));
}
export function capturedPayment(event,order) {
  const p=event?.payload?.payment?.entity;
  if(event?.event!=='payment.captured'||!p||p.status!=='captured'||p.currency!=='INR'||
    p.order_id!==order.providerOrderId||p.amount!==order.amountPaise||!p.id)
    throw new Error('Payment does not match frozen order');
  if(order.status==='fulfilled') return {duplicate:true,paymentId:p.id};
  if(order.status!=='pending') throw new Error('Order is not payable');
  return {duplicate:false,paymentId:p.id};
}
export const CAP=2_000_000_000n*100_000_000n, INITIAL=2_400n*100_000_000n;
export function issuedAt(n) {n=BigInt(n);if(n<0n)throw new Error('Invalid round');
  return CAP*n*INITIAL/(CAP-INITIAL+n*INITIAL);}
export function rewardAt(n) {n=BigInt(n);if(n<1n)throw new Error('Invalid round');return issuedAt(n)-issuedAt(n-1n);}
