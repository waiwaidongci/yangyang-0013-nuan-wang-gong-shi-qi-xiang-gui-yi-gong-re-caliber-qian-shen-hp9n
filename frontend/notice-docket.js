import {h} from '/base.js';

export const channelNames={wall:'公告栏',desk:'服务窗口',intranet:'内网'};
export const caseTypes={wording:'措辞',source:'日账来源',metric:'归一口径'};
const resolved={clarified:'已说明',addendum:'已补正措辞',recheck_next_period:'下期复查'};

export function deliveryDocket(rows) {
  return `<ol class="notice-deliveries">${rows.map(row=>`<li><strong>${h(row.recipient)}</strong>
    <span>${channelNames[row.channel]}</span><small>${row.delivery_ref ? '送达：'+h(row.delivery_ref) : '待登记回执'}</small></li>`).join('')}</ol>`;
}
export function objectionThread(cases) {
  return `<ul class="objection-thread">${cases.map(row=>`<li><strong>${h(row.recipient)} / ${caseTypes[row.category]}</strong><p>${h(row.question)}</p>
    ${row.resolution ? `<p>${resolved[row.resolution]} · ${h(row.answer)}</p>`:'<p>尚未签审答复</p>'}
    ${row.update_code ? `<blockquote>${h(row.update_code)}<br>${h(row.replacement_text)}</blockquote>`:''}</li>`).join('')}</ul>`;
}
