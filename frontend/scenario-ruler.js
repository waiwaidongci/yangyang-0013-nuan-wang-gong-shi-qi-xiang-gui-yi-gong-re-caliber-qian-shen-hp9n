import {h} from '/base.js';

export function scheduleStrip(days,marks) {
  const detail=new Map(marks.map(mark=>[mark.day,mark]));
  return `<ol class="schedule-strip">${days.map(day=>`<li class="${detail.get(day)?.mode ?? 'heating'}"><time>${h(day)}</time>
    <strong>${detail.get(day)?.mode==='standby'?'待机':'开启'}</strong>
    <small>${h(detail.get(day)?.evidence ?? '默认沿用账期')}</small></li>`).join('')}</ol>`;
}

export function scenariosTable(scenarios) {
  const value=x=>Number(x).toLocaleString('zh-CN',{maximumFractionDigits:5});
  return `<table class="scenario-grid"><thead><tr><th>来源快照 / 基准</th><th>开启日</th><th>加权度日</th><th>归一热耗</th><th>对原值差</th></tr></thead>
  <tbody>${scenarios.map(row=>`<tr><th>${h(row.spec_code)} #${row.calculation_id} · ${value(row.candidate_base)}°C</th>
    <td>${row.active_days.length}</td><td>${value(row.weighted_hdd)}</td><td>${value(row.normalized)}</td><td>${value(row.difference)}</td></tr>`).join('')}</tbody></table>`;
}
