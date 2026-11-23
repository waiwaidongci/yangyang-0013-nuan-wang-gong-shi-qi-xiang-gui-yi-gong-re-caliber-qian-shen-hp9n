import {h} from '/base.js';

export function plantMeters(rows) {
  return `<ul class="meter-register">${rows.map(row=>`<li><strong>${h(row.serial)}</strong><span>${h(row.zone_name)}</span>
    <span>表盘上界 ${row.dial_limit} · 倍率 ${row.multiplier}</span></li>`).join('')}</ul>`;
}

export function chainedReads(rows) {
  return `<table class="meter-flow"><thead><tr><th>日结</th><th>表底衔接</th><th>折算热量</th><th>依据</th></tr></thead>
  <tbody>${rows.map(row=>`<tr><th>${h(row.day)}</th><td>${row.before_reading} → ${row.after_reading}${row.rollover?'（清零）':''}</td>
    <td>${row.amount} MWh</td><td>${h(row.source_ref)} · 日账 v${row.revision}</td></tr>`).join('')}</tbody></table>`;
}
