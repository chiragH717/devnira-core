// Run only against the explicitly selected Firebase project using ADC.
import {initializeApp,applicationDefault} from 'firebase-admin/app';
import {getFirestore} from 'firebase-admin/firestore';
import {readFile} from 'node:fs/promises';
if(!process.env.GOOGLE_CLOUD_PROJECT)throw new Error('Set GOOGLE_CLOUD_PROJECT explicitly');
initializeApp({credential:applicationDefault(),projectId:process.env.GOOGLE_CLOUD_PROJECT});
const db=getFirestore();const catalog=JSON.parse(await readFile(new URL('../assets/catalog.json',import.meta.url)));
const batch=db.batch();
for(const item of catalog.items)batch.set(db.doc(`catalog/${item.id}`),{...item,published:false});
batch.set(db.doc('public/network'),{status:'Configuration pending',maxSupply:'2,000,000,000',
  reward:'2,400',roundSeconds:120,tokenAddress:null,chainName:null});
await batch.commit();console.log('Seeded draft catalog. No user equipment or balances created.');
