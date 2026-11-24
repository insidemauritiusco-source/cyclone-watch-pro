const a=require('node:assert/strict'),f=require('./official-forecast.js');
const now=Date.parse('2026-11-24T10:00:00Z'),issued='2026-11-24T00:00:00Z',checked='2026-11-24T09:50:00Z';
const b={system_number:3,bulletin_number:3,issued_at:issued,anchor:{lat:-9.5,lon:77.1},points:[{hours:12,valid_at:'2026-11-24T12:00:00Z',lat:-10.5,lon:76.4}]};
const feed={schema:1,issuer:'Meteo-France RSMC La Reunion',source:'https://wwmiws.wmo.int/index.php/metareas/bulletinset/8S/html',status:'ok',checked_at:checked,bulletins:[b]};
const v={mode:'official',connected:true,stale:false,data:{source_status:'ok',checked_at:checked},storm:{name:'Tropical Depression (B03)',lat:-9.7,lon:76.8}};
a.equal(f.select(feed,v,now),b);a.equal(f.select(feed,{...v,mode:'demo'},now),null);a.equal(f.select(feed,{...v,storm:{...v.storm,name:'B04'}},now),null);a.equal(f.select({...feed,status:'unavailable'},v,now),null);a.equal(f.select(feed,v,now+3600000),null);a.equal(f.select({...feed,bulletins:[{...b,points:[{...b.points[0],valid_at:'2026-11-24T13:00:00Z'}]}]},v,now),null);
a.deepEqual(f.mapPoint({lon:43,lat:-4}),[35,25]);console.log('PASS official forecast overlay selection and stale/mismatch guards');

a.deepEqual(f.intensity({max_wind_kt:30,classification:'TROPICAL DEPRESSION'}),{wind:'30 kt (10-min average)',classification:'TROPICAL DEPRESSION'});
a.deepEqual(f.intensity({max_wind_kt:999,classification:'invented'}),{wind:'Not reported',classification:'Not reported'});
a.equal(f.nextStep(0,2),1);a.equal(f.nextStep(1,2),null);
console.log('PASS forecast playback bounds and reported-only intensity');
