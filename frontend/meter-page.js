import {api,h} from '/base.js';
import {chainedReads,plantMeters} from './meter-register.js';

export async function meterPage(outlet,base,all,period,role,redraw,ui) {
  const [meter,book]=await Promise.all([api(base+'/meters'),api(base+'/worksheet')]);
  const canWrite=role==='operator' && !book.notice;
  const existing=new Set(meter.meters.map(row=>row.zone_id));
  const candidates=book.zones.filter(row=>!existing.has(row.id));
  outlet.innerHTML=ui.intro('累计表底','核对相邻日首尾表底，识别回零并折算为日供热量。源账保留表号和录入凭证。',all,period)
    +`<div class="meter-desk"><section class="heat-sheet"><h2>账期计量表</h2>
    ${meter.meters.length?plantMeters(meter.meters):'<p>演示日账可继续手工查阅。登记累计表后，由表底差换算新的热量版本。</p>'}
    <h3>表底换算流水</h3><div class="meter-scroll">${meter.reads.length?chainedReads(meter.reads):'<p>尚无累计读数。</p>'}</div></section>
    <aside class="register-sheet"><h2>计量登记</h2>${canWrite && candidates.length?`<form id="meter-create">
    <label>片区<select name="zone_id">${candidates.map(row=>`<option value="${row.id}">${h(row.zone_name)}</option>`).join('')}</select></label>
    <label>计量表序列号<input name="serial" minlength="3" required></label>
    <div class="field-pair"><label>表盘上界<input name="dial_limit" type="number" min="1" step="0.001" required></label>
    <label>倍率<input name="multiplier" type="number" value="1" min=".001" step=".001" required></label></div>
    <button type="submit">注册累计计量表</button></form>`:''}
    ${canWrite && meter.meters.length?`<form id="meter-read">
    <label>计量表<select name="meter">${meter.meters.map(row=>`<option value="${row.id}">${h(row.serial)} · ${h(row.zone_name)}</option>`).join('')}</select></label>
    <label>日结日<input name="day" type="date" min="${h(period.starts_on)}" max="${h(period.ends_on)}" required></label>
    <div class="field-pair"><label>首数<input name="before_reading" type="number" min="0" step=".001" required></label>
    <label>尾数<input name="after_reading" type="number" min="0" step=".001" required></label></div>
    <label>表盘是否回零<select name="rollover"><option value="no">未回零</option><option value="yes">已核实回零</option></select></label>
    <label>日结原始凭证<input name="source_ref" minlength="4" required></label><button type="submit">审查衔接并生成日账</button></form>`:''}
    ${!canWrite?'<p>现有累计表底及其折算日账均可追溯。已签审账期冻结。</p>':''}
    <p role="status" data-feedback></p></aside></div>`;
  ui.bind(outlet,'#meter-create',form=>{
    const data=Object.fromEntries(form);
    return api(base+'/meters','POST',{...data,zone_id:Number(data.zone_id)});
  },redraw);
  ui.bind(outlet,'#meter-read',form=>{
    const {meter,...data}=Object.fromEntries(form);
    return api(base+'/meters/'+meter+'/read','POST',{...data,rollover:data.rollover==='yes'});
  },redraw);
}
