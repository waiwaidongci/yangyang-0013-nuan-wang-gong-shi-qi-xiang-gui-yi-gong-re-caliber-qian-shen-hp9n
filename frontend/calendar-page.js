import {api,h} from '/base.js';
import {scenariosTable,scheduleStrip} from './scenario-ruler.js';

export async function calendarPage(outlet,base,all,period,role,redraw,ui) {
  const [calendar,book]=await Promise.all([api(base+'/operations'),api(base+'/specs')]);
  const calculations=book.calculations.filter(row=>row.phase==='ready');
  outlet.innerHTML=ui.intro('采暖日情景','复用一份源账快照，观察开启日范围与基准温度变化对归一口径的影响。',all,period)
    +`<section class="heat-sheet"><h2>账期运行日历</h2>${scheduleStrip(calendar.days,calendar.marks)}
    <h3>不同运行条件的热耗</h3><div class="scenario-scroll">${calendar.scenarios.length?scenariosTable(calendar.scenarios):'<p>选择已计算快照后可模拟加权度日，签审指标保留原口径。</p>'}</div>
    ${role==='operator'?`<form id="calendar-day" class="calendar-form">
    <label>自然日<select name="day">${calendar.days.map(day=>`<option>${h(day)}</option>`).join('')}</select></label>
    <label>运行状态<select name="mode"><option value="heating">开启</option><option value="standby">待机</option></select></label>
    <label>排班说明<input name="evidence" minlength="4" required></label><button type="submit">记录运行日</button></form>`:
    role==='reviewer' && calculations.length?`<form id="scenario-run" class="calendar-form">
    <label>已有快照<select name="calculation_id">${calculations.map(row=>`<option value="${row.id}">${h(row.spec_code)} #${row.id}</option>`).join('')}</select></label>
    <label>情景基准°C<input type="number" name="candidate_base" min="0" max="35" step=".1" value="18" required></label>
    <button type="submit">试算开启日热耗</button></form>` : ''}
    <p role="status" data-feedback></p></section>`;
  ui.bind(outlet,'#calendar-day',form=>api(base+'/operations/mark','POST',Object.fromEntries(form)),redraw);
  ui.bind(outlet,'#scenario-run',form=>{
    const fields=Object.fromEntries(form);
    return api(base+'/operations/scenario','POST',{...fields,calculation_id:Number(fields.calculation_id)});
  },redraw);
}
