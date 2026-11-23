import {api,h} from '/base.js';
import {caseTypes,channelNames,deliveryDocket,objectionThread} from './notice-docket.js';

const options=(rows,key)=>rows.map(row=>`<option value="${row.id}">${h(row[key])}</option>`).join('');

export async function followupPage(outlet,base,all,period,role,redraw,ui) {
  const endpoint=base+'/followup';
  const archive=await api(endpoint);
  const pending=archive.copies.filter(row=>!row.delivery_ref);
  const delivered=archive.copies.filter(row=>row.delivery_ref);
  const unresolved=archive.objections.filter(row=>!row.resolution);
  outlet.innerHTML=ui.intro('送达与异议','追踪签审公示的副本和异议。文字说明补正保留原公示编号及计算档案。',all,period)
    +`<div class="followup-board"><section class="heat-sheet"><h2>公示副本与答复</h2>
    <p>${archive.notice?h(archive.notice.notice_code):'该账期尚未签发公示。'}</p>
    ${archive.copies.length?deliveryDocket(archive.copies):'<p>未登记分发对象。</p>'}
    ${archive.objections.length?objectionThread(archive.objections):'<p>尚未收到片区异议。</p>'}</section>
    <aside class="register-sheet"><h2>送达与复核</h2>
    ${archive.notice&&role==='reviewer'?`<form id="notice-copy"><label>接收片区或单位<input name="recipient" required></label>
    <label>公示渠道<select name="channel">${Object.entries(channelNames).map(([key,value])=>`<option value="${key}">${value}</option>`).join('')}</select></label>
    <button type="submit">登记分发副本</button></form>`:''}
    ${role==='operator'&&pending.length?`<form id="notice-receipt"><label>待送达副本<select name="item">${options(pending,'recipient')}</select></label>
    <label>据以送达的登记号<input name="delivery_ref" minlength="4" required></label><button type="submit">记录送达</button></form>`:''}
    ${role==='operator'&&delivered.length?`<form id="notice-objection"><label>已送达副本<select name="item">${options(delivered,'recipient')}</select></label>
    <label>异议类别<select name="category">${Object.entries(caseTypes).map(([key,value])=>`<option value="${key}">${value}</option>`).join('')}</select></label>
    <label>异议原文<input name="question" minlength="6" required></label><button type="submit">记入待答</button></form>`:''}
    ${role==='reviewer'&&unresolved.length?`<form id="notice-answer"><label>异议<select name="item">${options(unresolved,'question')}</select></label>
    <label>复核处置<select name="resolution"><option value="clarified">解释现有内容</option><option value="addendum">签发措辞补正</option>
      <option value="recheck_next_period">标记下期复查</option></select></label>
    <label>答复说明<input name="answer" minlength="6" required></label><label>替代文字（仅措辞补正）<input name="replacement_text"></label>
    <button type="submit">核签答复</button></form>`:''}
    <p role="status" data-feedback></p></aside></div>`;
  ui.bind(outlet,'#notice-copy',form=>api(endpoint+'/copies','POST',Object.fromEntries(form)),redraw);
  ui.bind(outlet,'#notice-receipt',form=>api(endpoint+'/copies/'+form.get('item')+'/receipt','POST',{delivery_ref:form.get('delivery_ref')}),redraw);
  ui.bind(outlet,'#notice-objection',form=>{
    const {item,...body}=Object.fromEntries(form);
    return api(endpoint+'/copies/'+item+'/object','POST',body);
  },redraw);
  ui.bind(outlet,'#notice-answer',form=>{
    const {item,...body}=Object.fromEntries(form);
    body.replacement_text ||= null;
    return api(endpoint+'/objections/'+item+'/answer','POST',body);
  },redraw);
}
