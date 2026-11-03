import { initializeApp } from 'firebase-admin/app';
import { getFirestore, FieldValue } from 'firebase-admin/firestore';
import { onCall, HttpsError } from 'firebase-functions/v2/https';
import { validateDevice, requireAdmin } from './domain.js';

initializeApp();const db=getFirestore();const options={region:'asia-south1',enforceAppCheck:true};
const deny=(code,message)=>{throw new HttpsError(code,message);};

export const saveCatalogDevice=onCall(options,async request=>{
  try{requireAdmin(request.auth);}catch{deny('permission-denied','Administrator access required.');}
  let d;try{d=validateDevice(request.data);}catch(e){deny('invalid-argument',e.message);}
  const ref=db.doc(`catalog/${d.id}`),log=db.collection('audit').doc();
  await db.runTransaction(async tx=>{
    const old=await tx.get(ref);
    tx.set(ref,{...d,updatedAt:FieldValue.serverTimestamp()});
    tx.set(log,{action:`Saved ${d.name}`,actor:request.auth.uid,before:old.data()??null,after:d,
      createdAt:FieldValue.serverTimestamp()});
  });return {saved:true};
});

export const toggleEquipment=onCall(options,async request=>{
  if(!request.auth)deny('unauthenticated','Sign in first.');
  const {equipmentId,enabled}=request.data??{};
  if(typeof equipmentId!=='string'||!/^[a-zA-Z0-9_-]{1,100}$/.test(equipmentId)||typeof enabled!=='boolean')
    deny('invalid-argument','Invalid equipment switch.');
  const ref=db.doc(`users/${request.auth.uid}/equipment/${equipmentId}`);
  await db.runTransaction(async tx=>{
    const owned=await tx.get(ref);
    if(!owned.exists)deny('not-found','Equipment not owned by this account.');
    tx.update(ref,{enabled,updatedAt:FieldValue.serverTimestamp()});
  });return {enabled};
});

export const createOrder=onCall(options,async request=>{
  if(!request.auth)deny('unauthenticated','Sign in first.');
  // Razorpay currently prohibits this crypto-related business model. Do not
  // enable a gateway with a client flag or collect credentials in this release.
  deny('failed-precondition','Payments are unavailable for this crypto-related model. No money has been charged.');
});

export const savePublicProfile=onCall(options,async request=>{
  if(!request.auth)deny('unauthenticated','Sign in first.');
  const {handle}=request.data??{};
  if(typeof handle!=='string'||!/^[a-z0-9_]{3,24}$/.test(handle))deny('invalid-argument','Use 3–24 lowercase letters, digits or underscore.');
  const profile=db.doc(`users/${request.auth.uid}`),reserved=db.doc(`handles/${handle}`);
  await db.runTransaction(async tx=>{
    const [entry,current]=await Promise.all([tx.get(reserved),tx.get(profile)]);
    if(entry.exists&&entry.data().uid!==request.auth.uid)deny('already-exists','Handle taken.');
    const previous=current.data()?.handle;
    if(previous&&previous!==handle)tx.delete(db.doc(`handles/${previous}`));
    tx.set(reserved,{uid:request.auth.uid});tx.set(profile,{handle,updatedAt:FieldValue.serverTimestamp()},{merge:true});
  });return {handle};
});
