import {api, badge, empty, h, mount, notice, waitJob} from '/base.js';

import {meterPage} from './meter-page.js';
import {calendarPage} from './calendar-page.js';
import {followupPage} from './notice-followup.js';

const pages = { districts:'账期与片区', ledger:'逐日勾稽', benchmark:'口径并表', notice:'公示签审', meters:'累计表底', calendar:'采暖日情景', followup:'送达与异议' };
const channelLabels = {weather:'日均气温 (°C)',heat:'日供热量 (MWh)'};
const calculationPhases = {queued:'后台计算中',ready:'快照已就绪'};
const active = {period:null, missing:null, chosen:null};
const periodsPath = '/api/heat-periods';
const format = value => Number(value).toLocaleString('zh-CN', {maximumFractionDigits:4});

function intro(title, desc, choices, period) {
  return `<header class="heat-title"><div><h1>${h(title)}</h1><p>${h(desc)}</p></div>
    ${period ? `<label class="period-tab">供热账期<select id="period">${choices.map(row =>
      `<option value="${row.id}" ${row.id === period.id ? 'selected' : ''}>${h(row.code)} · ${h(row.starts_on)} 至 ${h(row.ends_on)}</option>`).join('')}
    </select></label>` : ''}</header>`;
}

function bind(outlet, selector, submit, redraw) {
  const form = outlet.querySelector(selector);
  if (!form) return;
  form.onsubmit = async event => {
    event.preventDefault();
    const button = form.querySelector('[type=submit]');
    button.disabled = true;
    try {
      await submit(new FormData(form));
      await redraw();
    } catch (error) {
      notice(outlet.querySelector('[data-feedback]'), error.message, true);
      button.disabled = false;
    }
  };
}

async function districtView(outlet, base, all, period, role, redraw) {
  const sheet = period ? await api(base + '/worksheet') : {zones:[],days:[],missing:[]};
  outlet.innerHTML = intro('账期与片区','登记核算边界。供热面积在归一计算时参与气象权重。',all,period)
    + `<section class="coverage-ruler"><h2>核算覆盖</h2>
    ${period ? `<p>${h(period.starts_on)} 至 ${h(period.ends_on)} · ${sheet.days.length} 个自然日 · ${sheet.zones.length} 个片区</p>` : ''}
    ${sheet.zones.length ? `<ul>${sheet.zones.map(zone => `<li><strong>${h(zone.zone_name)}</strong><span class="heat-mono">${h(zone.zone_code)} / ${format(zone.area_m2)} m²</span></li>`).join('')}</ul>`
      : empty('录入账期和片区后，可逐日对接气象与热量来源。')}
    ${period && sheet.missing.length ? `<p><a href="#ledger">核查 ${sheet.missing.length} 项待补日账</a></p>` : ''}
    ${sheet.notice ? '<p>签审已完成，账期与核算面积已冻结。</p>' : ''}</section>
    ${role === 'operator' ? `<div class="heat-panels"><section class="register-sheet"><h2>登记账期</h2>
    <form id="start-period"><label>账期编码<input name="code" pattern="[A-Z0-9-]{3,24}" required placeholder="H-1126"></label>
    <div class="field-pair"><label>起始日<input name="starts_on" type="date" required></label><label>结束日<input name="ends_on" type="date" required></label></div>
    <button type="submit">建立账期</button></form></section>
    ${period && !sheet.notice ? `<section class="register-sheet"><h2>登记核算片区</h2>
    <form id="zone"><div class="field-pair"><label>片区编码<input name="zone_code" pattern="[A-Z0-9-]{2,24}" required></label>
    <label>片区名<input name="zone_name" required></label></div>
    <label>供热面积（m²）<input name="area_m2" type="number" min="100" max="1000000" required></label>
    <button type="submit">加入核算范围</button></form></section>` : ''}</div>` : ''}
    <p role="status" data-feedback></p>`;
  bind(outlet,'#start-period',async form => {
    const row = await api(periodsPath,'POST',Object.fromEntries(form));
    active.period = row.id;
  },redraw);
  bind(outlet,'#zone',form => api(base+'/zones','POST',{...Object.fromEntries(form),area_m2:Number(form.get('area_m2'))}),redraw);
}

async function ledgerView(outlet, base, all, period, role, redraw) {
  const {zones,days,entries,missing,notice:published} = await api(base + '/worksheet');
  const records = new Map(entries.map(row => [`${row.zone_id}:${row.day}:${row.channel}`,row]));
  const address = (zone,day,channel) => records.get(`${zone}:${day}:${channel}`);
  const picked = missing.find(row => `${row.zone_id}:${row.day}:${row.channel}` === active.missing) ?? missing[0];
  const editable = role === 'operator' && zones.length && !published;
  outlet.innerHTML = intro('逐日勾稽','逐区核对气温和热量两套来源。新版本保留原凭证，按最后一版计入新快照。',all,period)
    + `<div class="ledger-layout"><section class="heat-sheet"><h2>同日两源检查</h2>
      ${zones.length ? zones.map(zone => `<article class="zone-ledger"><h3>${h(zone.zone_name)} · ${h(zone.zone_code)}</h3>
      <table><thead><tr><th>日期</th><th>${channelLabels.weather}</th><th>${channelLabels.heat}</th></tr></thead>
      <tbody>${days.map(day => `<tr><th scope="row">${h(day)}</th>${Object.keys(channelLabels).map(channel => {
        const row = address(zone.id,day,channel);
        return row ? `<td><strong>${format(row.amount)}</strong><small>v${row.revision} · ${h(row.source_ref)}</small></td>`
          : `<td>${editable ? `<button class="gap-mark" data-gap="${zone.id}:${h(day)}:${channel}" type="button">补录缺项</button>`
            : badge('缺源','missing') }</td>`;
      }).join('')}</tr>`).join('')}</tbody></table></article>`).join('') : empty('账期内还没有核算片区。')}</section>
      <aside class="heat-sheet"><h2>来源凭证</h2><p>${missing.length ? '当前待补 ' + missing.length + ' 项' : '两种日账已齐'}。</p>
      ${editable ? `<form id="reading"><label>片区<select name="zone_id">${zones.map(zone =>
        `<option value="${zone.id}" ${zone.id === picked?.zone_id ? 'selected' : ''}>${h(zone.zone_name)}</option>`).join('')}</select></label>
      <label>统计日期<input name="day" type="date" min="${h(period.starts_on)}" max="${h(period.ends_on)}"
        value="${h(picked?.day ?? period.starts_on)}" required></label>
      <label>数值口径<select name="channel">${Object.entries(channelLabels).map(([key,label]) =>
        `<option value="${key}" ${key === picked?.channel ? 'selected' : ''}>${h(label)}</option>`).join('')}</select></label>
      <label>来源表中的数值<input name="amount" type="number" step="0.001" required></label>
      <label>来源文件/账页<input name="source_ref" minlength="4" required placeholder="meter-daily-1123.csv"></label>
      <button type="submit">登记来源版本</button></form>`
      : published ? '<p>账期已公示，源数据冻结。</p>' : '<p>缺项由录入员依据原文件补写。</p>'}
      <p role="status" data-feedback></p></aside></div>`;
  for (const mark of outlet.querySelectorAll('[data-gap]')) {
    mark.onclick = () => { active.missing = mark.dataset.gap; redraw(); };
  }
  bind(outlet,'#reading',form => api(base + '/entries','POST',{...Object.fromEntries(form),zone_id:Number(form.get('zone_id'))}),redraw);
}

function specCard(title,row) {
  return `<article class="version-output"><header><h3>${h(title)}</h3><p>${h(row.spec_code)} · 基准 ${format(row.base_celsius)}°C</p></header>
  <dl><div><dt>供热面积</dt><dd>${format(row.scope_area)} m²</dd></div>
      <div><dt>净供热量</dt><dd>${format(row.total_mwh)} MWh</dd></div>
      <div><dt>面积加权度日</dt><dd>${format(row.period_hdd)} °C·日</dd></div>
      <div><dt>单位面积热耗</dt><dd>${format(row.raw_kwh_m2)} kWh/m²</dd></div>
      <div><dt>气象归一热耗</dt><dd>${format(row.normalized)} kWh/(m²·°C·日)</dd></div></dl></article>`;
}

async function benchmark(outlet,base,all,period,role,redraw) {
  const {definitions,calculations,notice:published} = await api(base+'/specs');
  const ready = calculations.filter(row => row.phase === 'ready');
  const first = ready.find(row => row.id === active.first) ?? ready.at(-1);
  const second = ready.find(row => row.id === active.second) ?? ready.find(row => row.spec_id !== first?.spec_id);
  let parallel = null;
  let warning = '';
  if (first && second) {
    try {
      parallel = await api(base + `/compare?first=${first.id}&second=${second.id}`);
    } catch (error) {
      if (error.status !== 409) throw error;
      warning = error.message;
    }
  }
  const both = first && second;
  const reviewer = role === 'reviewer' && !published;
  const options = selected => ready.map(row => `<option value="${row.id}" ${row.id === selected?.id ? 'selected' : ''}>
    ${h(row.spec_code)} · 快照 ${row.id}</option>`).join('');
  outlet.innerHTML = intro('口径并表','比较不同基准温度的影响。两版快照须使用同一份日账。',all,period)
    + `<section class="version-deck heat-sheet"><header><h2>版次对照</h2>
      ${both ? `<div class="field-pair"><label>左侧版次<select id="first">${options(first)}</select></label>
       <label>右侧版次<select id="second">${options(second)}</select></label></div>` : ''}</header>
      ${parallel ? `<div class="metric-folio">${specCard('左列',parallel.base)}${specCard('右列',parallel.candidate)}</div>
       <p class="heat-mono">右列 − 左列 · 归一热耗差 ${format(parallel.normalized_delta)} · 度日差 ${format(parallel.degree_days_delta)}</p>`
       : warning ? `<p class="flag-line">${h(warning)}</p>` : first ? specCard('当前快照',first)
         : empty('登记口径并计算后，可以检视气象归一热耗。')}
      <details><summary>快照与片区明细</summary>
      <ul class="version-trail">${calculations.map(row => `<li>${h(row.spec_code)} · 快照 ${row.id} · ${row.entry_ids.length} 条日账 · ${calculationPhases[row.phase]}
        ${row.zones.map(zone => `<small>${h(zone.zone_name)} ${format(zone.hdd)} °C·日 / 归一热耗 ${format(zone.normalized)}</small>`).join('')}</li>`).join('')}</ul></details></section>
      ${reviewer ? `<div class="heat-panels">
      <section class="register-sheet"><h2>登记比较口径</h2><form id="definition">
        <div class="field-pair"><label>版次<input name="spec_code" pattern="[A-Z0-9-]{2,24}" required></label>
        <label>基准温度（°C）<input name="base_celsius" type="number" min="0" max="35" step="0.1" required></label></div>
        <label>口径说明<input name="description" minlength="4" required></label>
        <button type="submit">保存口径</button></form></section>
      <section class="register-sheet"><h2>冻结日账并计算</h2>${definitions.length ? `<form id="evaluate">
        <label>归一口径<select name="spec_id">${definitions.map(row => `<option value="${row.id}">${h(row.spec_code)} · ${format(row.base_celsius)}°C</option>`).join('')}</select></label>
        <button type="submit">送交后台计算</button></form>` : '<p>先登记一个口径。</p>'}</section></div>` : ''}
      <p role="status" data-feedback></p>`;
  for (const key of ['first','second']) {
    outlet.querySelector('#'+key)?.addEventListener('change',event => {
      active.first = Number(outlet.querySelector('#first').value);
      active.second = Number(outlet.querySelector('#second').value);
      redraw();
    });
  }
  bind(outlet,'#definition',form => api(base+'/specs','POST',Object.fromEntries(form)),redraw);
  bind(outlet,'#evaluate',async form => {
    const row = await api(base+'/specs/'+form.get('spec_id')+'/evaluate','POST');
    active.chosen = row.calculation.id;
    notice(outlet.querySelector('[data-feedback]'),'源日账已冻结，后台归一计算中。');
    await waitJob(row.job_id);
  },redraw);
}

async function noticeView(outlet,base,all,period,role,redraw) {
  const {calculations,notice:published} = await api(base+'/specs');
  const ready = calculations.filter(row => row.phase === 'ready');
  const chosen = ready.find(row => row.id === (published?.calculation_id ?? active.chosen)) ?? ready[0];
  outlet.innerHTML = intro('公示签审','公示绑定一个版次及其完整来源快照，同一账期只签出一份。',all,period)
    + `<article class="notice-sheet"><header><h2>供热气象归一公示单</h2><span class="seal-chip">${published ? '已签审' : '待签审'}</span></header>
      ${published ? `<dl class="notice-stamp"><dt>公示编号</dt><dd class="heat-mono">${h(published.notice_code)}</dd>
        <dt>签审凭证</dt><dd>${h(published.note)}</dd><dt>签审人</dt><dd>${h(published.signed_by)}</dd></dl>`
      : chosen ? `<label>公示备选快照<select id="chosen">${ready.map(row =>
        `<option value="${row.id}" ${row.id === chosen.id ? 'selected' : ''}>${h(row.spec_code)} · 快照 ${row.id}</option>`).join('')}</select></label>`
      : empty('尚未生成归一快照。请先在口径并表完成计算。')}
      ${chosen ? specCard('账期口径',chosen) : ''}
      ${!published && chosen && role === 'reviewer' ? `<form id="publish"><label>签审依据<input name="note" minlength="4" required placeholder="两源、面积与账期复核完成"></label>
        <button type="submit">盖章并冻结账期</button></form>` : ''}
      <p role="status" data-feedback></p></article>`;
  outlet.querySelector('#chosen')?.addEventListener('change',event => { active.chosen = Number(event.target.value); redraw(); });
  bind(outlet,'#publish',form => api(base+'/notice','POST',{calculation_id:chosen.id,note:form.get('note')}),redraw);
}

async function render(slug,outlet,user) {
  const all = await api(periodsPath);
  const redraw = () => render(slug,outlet,user);
  const selected = all.find(row => row.id === active.period)
    ?? all.find(row => Boolean(row.notice_code) === ['benchmark','notice','calendar','followup'].includes(slug)) ?? all[0];
  if (!selected && slug !== 'districts') {
    outlet.innerHTML = empty('请先在账期与片区登记一个供热账期。');
    return;
  }
  const screen = {districts:districtView,ledger:ledgerView,benchmark,notice:noticeView,
    meters:meterPage,calendar:calendarPage,followup:followupPage}[slug];
  await screen(outlet,periodsPath+'/'+selected?.id,all,selected,user.role,redraw,{intro,bind});
  outlet.querySelector('#period')?.addEventListener('change',event => {
    active.period = Number(event.target.value);
    active.first = active.second = active.chosen = active.missing = null;
    redraw();
  });
}

mount({title:'暖网公示',kicker:'青桥热网核算组',pages,render});
