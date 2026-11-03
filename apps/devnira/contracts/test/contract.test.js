import test from 'node:test';import assert from 'node:assert/strict';
import solc from 'solc';import ganache from 'ganache';import {readFileSync,mkdirSync,writeFileSync} from 'node:fs';
import {BrowserProvider,ContractFactory,keccak256,toUtf8Bytes} from 'ethers';
const source=readFileSync(new URL('../DevniraRewards.sol',import.meta.url),'utf8');
const output=JSON.parse(solc.compile(JSON.stringify({language:'Solidity',sources:{'DevniraRewards.sol':{content:source}},
 settings:{optimizer:{enabled:true,runs:200},evmVersion:'shanghai',outputSelection:{'*':{'*':['abi','evm.bytecode.object']}}}}),{
 import:path=>{try{return{contents:readFileSync(new URL('../node_modules/'+path,import.meta.url),'utf8')}}catch{return{error:'Import not found'}}}}));
assert.deepEqual((output.errors??[]).filter(x=>x.severity==='error'),[]);
const compiled=output.contracts['DevniraRewards.sol'].DevniraRewards;
mkdirSync(new URL('../build/',import.meta.url),{recursive:true});
writeFileSync(new URL('../build/DevniraRewards.json',import.meta.url),JSON.stringify(compiled,null,2));
test('deployed EVM contract enforces authority, timing, replay, supply and pause',async()=>{
 const engine=ganache.provider({logging:{quiet:true},chain:{hardfork:'shanghai'}});
 try {
 const provider=new BrowserProvider(engine);provider.pollingInterval=10;
 const owner=await provider.getSigner(0),operator=await provider.getSigner(1),user=await provider.getSigner(2);
 const contract=await new ContractFactory(compiled.abi,compiled.evm.bytecode.object,owner).deploy(await owner.getAddress());
 await contract.waitForDeployment();assert.equal(await contract.decimals(),8n);assert.equal(await contract.totalSupply(),0n);
 await assert.rejects(contract.connect(user).setOperator(await user.getAddress()));
 await(await contract.setOperator(await operator.getAddress())).wait();
 const hash=keccak256(toUtf8Bytes('chirag')),digest=keccak256(toUtf8Bytes('allocation-1'));
 await assert.rejects(contract.connect(operator).settleRound(1,await user.getAddress(),hash,digest));
 await(await contract.setRewardsPaused(false)).wait();
 await assert.rejects(contract.connect(operator).settleRound(1,await user.getAddress(),hash,digest));
 await provider.send('evm_increaseTime',[121]);await provider.send('evm_mine',[]);
 await assert.rejects(contract.connect(user).settleRound(1,await user.getAddress(),hash,digest));
 await(await contract.connect(operator).settleRound(1,await user.getAddress(),hash,digest,{gasLimit:300000})).wait();
 assert.equal(await contract.balanceOf(await user.getAddress()),2400n*100_000_000n);
 assert.equal(await contract.round(),1n);
 await assert.rejects(contract.connect(operator).settleRound(1,await user.getAddress(),hash,digest));
 assert.ok(await contract.rewardAt(2)<await contract.rewardAt(1));
 assert.ok(await contract.issuedAt(2n**64n-1n)<=await contract.MAX_SUPPLY());
 await assert.rejects(contract.issuedAt(2n**64n));
 await(await contract.setRewardsPaused(true)).wait();
 await provider.send('evm_increaseTime',[121]);await provider.send('evm_mine',[]);
 await assert.rejects(contract.connect(operator).settleRound(2,await user.getAddress(),hash,digest));
 }finally{await engine.disconnect();}
});
