const $ = id => document.getElementById(id);
const ruleNames = {device_offline:'Stopped checking in', telemetry_anomaly:'Temperature or vibration is too high', connection_failures:'Several failed connections were reported', unusual_control_write:'Write request did not match the rules'};
const eventNames = {heartbeat:'Heartbeat: I am here', telemetry:'Sensor reading', connection_failure:'Failed connection report', control_write:'Write request report'};
const scenarioNames = {normal:'everything is normal', offline:'cooling is quiet', telemetry:'the press is running hot', failures:'failed connections were reported', control:'an unapproved write was reported'};
const statusNames = {online:'Sending updates', offline:'No recent check-in', waiting:'Waiting for first check-in'};
const activeLabels = {device_offline:'Needs attention', telemetry_anomaly:'Needs attention', connection_failures:'Saved for review', unusual_control_write:'Saved for review'};
let selected = null;
let busy = false;
async function api(path, method = 'GET') {
  const response = await fetch(path, {method, headers: method === 'POST' ? {'X-EdgeSentinel-Demo':'1'} : {}});
  const data = await response.json();
  if (!response.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail));
  return data;
}
function node(tag, text, className) {
  const element = document.createElement(tag);
  if (text !== undefined) element.textContent = text;
  if (className) element.className = className;
  return element;
}
function badge(text, label = text) { return node('span', label, `badge ${text}`); }
function timestamp(value) { return value ? new Date(value * 1000).toLocaleTimeString() : 'Not yet'; }
function jsonDetails(parent, title, value) {
  const details = node('details'); details.append(node('summary', title), node('pre', JSON.stringify(value, null, 2))); parent.append(details);
}
async function refresh() {
  const [devices, alerts, events, demo] = await Promise.all(['/api/devices','/api/alerts','/api/events?limit=30','/api/demo'].map(path => api(path)));
  $('devices').replaceChildren(...devices.map(device => {
    const card = node('div', undefined, 'device');
    card.append(node('h3', device.device_id), badge(device.status, statusNames[device.status]), node('p', `Last check-in: ${timestamp(device.last_heartbeat_received_at)}`)); return card;
  }));
  const focusedAlert = document.activeElement?.dataset.alertId;
  $('alerts').replaceChildren(...alerts.map(alert => {
    const button = node('button', undefined, `alert ${selected === alert.id ? 'selected' : ''}`);
    button.dataset.alertId = alert.id;
    const title = node('div', undefined, 'alert-title'); title.append(node('strong', `#${alert.id} · ${alert.device_id}`), badge(alert.severity));
    const state = alert.active ? activeLabels[alert.rule] : 'Back to normal';
    button.append(title, node('div', ruleNames[alert.rule]), node('div', `${state} · Last noticed ${timestamp(alert.latest_observed)}`, 'muted'));
    button.onclick = () => showAlert(alert.id).catch(showError); return button;
  }));
  if (!alerts.length) $('alerts').append(node('p','No problems found yet. Try making the press run hot above.'));
  if (focusedAlert) document.querySelector(`[data-alert-id="${focusedAlert}"]`)?.focus({preventScroll:true});
  $('events').replaceChildren(...events.map(event => {
    const row = node('tr'); row.id = `event-${event.id}`;
    [event.id,event.device_id,eventNames[event.event_type],`${event.temperature} °C`,`${event.vibration} mm/s`,timestamp(event.received_at)].forEach(value => row.append(node('td',value))); return row;
  }));
  $('sim-status').textContent = demo.error || (demo.running ? `Running: ${scenarioNames[demo.scenario]}` : 'Machines are stopped. Click Start to begin.');
}
function showError(error) { $('feedback').textContent = `Error: ${error.message}`; }
async function showAlert(id) {
  const data = await api(`/api/alerts/${id}`); selected = id;
  $('detail-empty').hidden = true; $('detail').replaceChildren(); $('investigation').replaceChildren();
  $('detail').append(node('h3', `Alert #${id}: ${ruleNames[data.alert.rule]}`), node('p',data.alert.explanation), node('p',`What to check: ${data.alert.next_step}`));
  jsonDetails($('detail'),'See the original alert and messages (technical details)',data);
  $('investigate').hidden = false;
}
function renderClaim(parent, claim) {
  const block = node('div', undefined, 'claim'); block.append(node('p',claim.text), node('span',claim.citations.join(' · '),'muted')); parent.append(block);
}
$('investigate').onclick = async () => {
  const id = selected; $('investigate').disabled = true;
  try {
    const result = await api(`/api/alerts/${id}/investigation`);
    if (selected !== id) return;
    const panel = $('investigation'); panel.replaceChildren(node('h3','Here is what we know'), node('p','Source labels let you check the answer: event means a saved message, alert means this warning, and runbooks means a local troubleshooting guide. Open the source data below to see them.'));
    renderClaim(panel,result.summary); result.evidence_claims.forEach(claim => renderClaim(panel,claim));
    panel.append(node('h3','What to check next')); result.next_steps.forEach(claim => renderClaim(panel,claim));
    panel.append(node('p',result.limitations)); jsonDetails(panel,'See all source data and guides (technical details)',result.retrieved);
  } catch (error) { showError(error); } finally { $('investigate').disabled = false; }
};
async function control(path) {
  if (busy) return; busy = true;
  document.querySelectorAll('.controls button').forEach(button => button.disabled = true);
  try {
    const result = await api(path,'POST'); $('feedback').textContent = result.message;
    if (path === '/api/reset') { selected = null; $('detail').replaceChildren(); $('investigation').replaceChildren(); $('investigate').hidden = true; $('detail-empty').hidden = false; }
    await refresh();
  } catch (error) { showError(error); } finally { busy = false; document.querySelectorAll('.controls button').forEach(button => button.disabled = false); }
}
document.querySelectorAll('[data-scenario]').forEach(button => button.onclick = () => control(`/api/demo/${button.dataset.scenario}`));
$('reset').onclick = () => { if (confirm('Delete stored demo events and alerts, and stop simulation?')) control('/api/reset'); };
async function poll() { try { await refresh(); } catch (error) { showError(error); } finally { setTimeout(poll,1500); } }
poll();
