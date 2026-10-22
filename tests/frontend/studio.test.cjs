const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const path=require('node:path');
const definitions=new Map();
const context={HTMLElement:class{},customElements:{get:n=>definitions.get(n),define:(n,v)=>definitions.set(n,v)},window:{},Intl,Date,Set,Map,Number,Error};
vm.createContext(context);
vm.runInContext(fs.readFileSync(path.join(__dirname,'../../custom_components/rocon_g1_local/frontend/rocon-studio-card.js'),'utf8'),context);
test('schedule handles midnight and rejects overlaps and non-quarter-hour input',()=>{
  assert.equal(context.studioParseProgram('06:00-08:00;19:00-24:00;00:00-00:00')[1][1],'24:00');
  for(const value of ['06:01-08:00;00:00-00:00;00:00-00:00','06:00-09:00;08:00-10:00;00:00-00:00','24:00-24:00;00:00-00:00;00:00-00:00'])assert.throws(()=>context.studioParseProgram(value));
});
test('power conversions require actual power units and preserve valid zero',()=>{
  const entity=(state,unit)=>({state,attributes:{unit_of_measurement:unit}});
  assert.equal(context.studioWatts(entity('1.5','kW')),1500);
  assert.equal(context.studioWatts(entity('0','W')),0);
  assert.equal(context.studioWatts(entity('unavailable','W')),null);
  assert.equal(context.studioWatts(entity('30','°C')),null);
  assert.equal(context.studioWatts(entity('-40','W')),null);
});
test('energy requires matching hourly coverage and never double counts meters',()=>{
  const start=Date.parse('2026-10-20T10:00:00Z'),row={start,end:start+3600000,mean:1000};
  const series={external:[row,{...row,start:row.end,end:row.end+3600000}],internal:[{...row,mean:500}]};
  const days=context.studioEnergyDays(series,['external','internal'],'Europe/Rome');
  assert.equal(days.length,1);assert.ok(Math.abs(days[0].kwh-1.5)<1e-9);assert.ok(Math.abs(days[0].hours-1)<1e-9);
  assert.throws(()=>context.studioEnergyDays(series,['external','external'],'Europe/Rome'));
});
test('hourly estimates split correctly at local midnight in half-hour time zones',()=>{
  const start=Date.parse('2026-01-01T18:00:00Z');
  const days=context.studioEnergyDays({meter:[{start,end:start+3600000,mean:1000}]},['meter'],'Asia/Kolkata');
  assert.equal(days.length,2);assert.ok(Math.abs(days[0].kwh-.5)<1e-9);assert.ok(Math.abs(days[1].kwh-.5)<1e-9);
});
