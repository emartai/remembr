'use strict';
const $ = id => document.getElementById(id);
let credential = '', owner = false, generation = 0, selection = 0, searchVersion = 0;
let offset = 0, nextOffset = null, pages = [], currentSpaces = [], pendingSave = null;
const requests = new Set(), busy = new WeakSet();
class Cancelled extends Error {}
const message = text => { $('notice').textContent = text; };
function clearEditor() {
  $('save-form').reset(); pendingSave = null; $('editor').open = false;
}
function clearResults() {
  searchVersion++; offset = 0; nextOffset = null; pages = [];
  $('results').replaceChildren(); $('results').setAttribute('aria-busy', 'false'); $('search-info').textContent = '';
  $('more').hidden = true; $('previous').hidden = true;
}
function resetSession(value = '') {
  generation++; selection++;
  for (const controller of requests) controller.abort();
  requests.clear(); credential = value; owner = false; currentSpaces = [];
  clearResults(); clearEditor();
  for (const id of ['connect-form', 'login-form', 'new-project', 'new-space', 'new-agent', 'grant', 'search-form']) $(id).reset();
  $('project').replaceChildren(); $('space').replaceChildren();
  $('new-credential').textContent = ''; $('new-credential').hidden = true;
  $('permission-info').textContent = ''; $('management').open = false;
  $('management').hidden = true; $('workspace').hidden = true;
  $('connection').hidden = false; $('disconnect').hidden = true;
}
async function api(path, method = 'GET', body, authenticated = true) {
  const session = generation, controller = new AbortController();
  requests.add(controller);
  const timer = setTimeout(() => controller.abort(), 30000);
  try {
    const headers = {'Content-Type': 'application/json'};
    if (authenticated && credential) Object.assign(headers, credential.startsWith('rmsp_') ? {'X-API-Key': credential} : {Authorization: `Bearer ${credential}`});
    const response = await fetch('/api/v1' + path, {method, headers, signal: controller.signal, body: body === undefined ? undefined : JSON.stringify(body), cache: 'no-store'});
    const envelope = await response.json().catch(() => ({}));
    if (session !== generation) throw new Cancelled();
    if (!response.ok) {
      if (response.status === 401 && !$('workspace').hidden) {
        resetSession(); message('Connection expired or credential revoked. Connect again.'); throw new Cancelled();
      }
      const request = envelope.request_id || envelope.error?.request_id;
      throw new Error(`${response.status}: ${envelope.error?.message || 'Request failed'}${request ? ' · Request ' + request : ''}`);
    }
    return envelope;
  } catch (error) {
    if (session !== generation || error instanceof Cancelled) throw new Cancelled();
    if (error.name === 'AbortError') throw new Error('Request timed out. Check the connection and try again.');
    throw error;
  } finally { clearTimeout(timer); requests.delete(controller); }
}
function bind(id, event, action) {
  $(id).addEventListener(event, async e => {
    e.preventDefault();
    // Selection changes must supersede an in-flight selection, not be dropped.
    if (event !== 'change' && busy.has(e.currentTarget)) return;
    const target = e.currentTarget, buttons = target.tagName === 'BUTTON' ? [target] : [...target.querySelectorAll('button[type=submit], button:not([type])')];
    busy.add(target); buttons.forEach(button => { button.disabled = true; }); message('');
    try { await action(e); } catch (error) { if (!(error instanceof Cancelled)) message(error.message); }
    finally { busy.delete(target); buttons.forEach(button => { button.disabled = false; }); }
  });
}
function options(id, rows, preferred) {
  $(id).replaceChildren(...rows.map(row => {
    const option = document.createElement('option'); option.value = row.id; option.textContent = row.name; return option;
  }));
  if (rows.some(row => row.id === preferred)) $(id).value = preferred;
}
function permissions() {
  return currentSpaces.find(space => space.id === $('space').value)?.permissions || {can_read: false, can_write: false, can_delete: false};
}
function spacePath(id = $('space').value) {
  if (!id) throw new Error('Select a space first.');
  return `/projects/spaces/${id}`;
}
async function spaces(preferred) {
  const project = $('project').value, version = ++selection;
  clearResults(); clearEditor(); currentSpaces = []; options('space', []);
  if (project) {
    const {data} = await api(`/projects/${project}/spaces`);
    if (version !== selection) return;
    currentSpaces = data; options('space', data, preferred);
  }
  await chooseSpace();
}
async function projects(preferred, preferredSpace) {
  const {data} = await api('/projects');
  options('project', data, preferred); await spaces(preferredSpace);
}
async function connect() {
  const session = generation;
  owner = !credential.startsWith('rmsp_'); await projects();
  if (session !== generation) return;
  $('connection').hidden = true; $('workspace').hidden = false;
  $('management').hidden = !owner; $('disconnect').hidden = false;
}
async function chooseSpace() {
  selection++; clearResults(); clearEditor(); $('search-form').reset();
  const access = permissions();
  $('editor').hidden = !access.can_write; $('search-form').hidden = !access.can_read;
  $('permission-info').textContent = !$('space').value ? '' : owner ? 'Project owner · read, write and delete' : `This connection: ${['read', 'write', 'delete'].filter(name => access['can_' + name]).join(', ')}`;
  await search();
}
async function search() {
  const access = permissions(), version = ++searchVersion, space = $('space').value;
  $('results').replaceChildren(); $('more').hidden = true; $('previous').hidden = true;
  if (!space) {
    $('search-info').textContent = owner ? 'Create a project and memory space to begin.' : 'No accessible memory spaces. Ask the project owner to grant access.';
    return;
  }
  if (!access.can_read) { $('search-info').textContent = 'This connection cannot read memories. It can only perform its granted actions.'; return; }
  if ($('history').checked && $('query').value.trim()) { $('search-info').textContent = ''; throw new Error('Clear the search query to browse expired and superseded history.'); }
  $('search-info').textContent = 'Loading memories…'; $('results').setAttribute('aria-busy', 'true');
  try {
    const {data, request_id} = await api(spacePath(space) + '/search', 'POST', {
      query: $('query').value, mode: $('mode').value, offset, limit: 20,
      context_chars: Number($('budget').value), include_inactive: $('history').checked
    });
    if (version !== searchVersion || space !== $('space').value) return;
    nextOffset = data.next_offset ?? (data.has_more ? offset + data.results.length : null);
    $('search-info').textContent = `${data.results.length} memories · ${data.mode} · ${data.context_chars_used} characters${data.truncated ? ' · truncated; inspect full content or narrow your search' : ''} · Request ${request_id}. ${data.score_explanation}`;
    $('more').hidden = nextOffset === null; $('previous').hidden = pages.length === 0;
    if (!data.results.length) {
      const empty = document.createElement('p');
      empty.textContent = $('history').checked ? 'No memories in this space.' : 'No matching active memories. Try keyword search while embeddings are pending, or browse history.';
      $('results').append(empty);
    }
    for (const row of data.results) $('results').append(cardFor(row, space, access));
  } catch (error) {
    if (version === searchVersion) $('search-info').textContent = 'Could not load memories. Try again.';
    throw error;
  } finally { if (version === searchVersion) $('results').setAttribute('aria-busy', 'false'); }
}
function metadata(row) {
  return `Memory ${row.id} · Author ${row.author_kind}:${row.author_id} · ${new Date(row.created_at).toLocaleString()}\nSource: ${row.source_ref || 'Not supplied'} · Run: ${row.run_id || 'Not supplied'}${row.retrieval_reason ? ' · ' + row.retrieval_reason + ', score ' + row.score.toFixed(4) : ''}${row.supersedes_id ? ' · Corrects ' + row.supersedes_id : ''}${row.expires_at ? ' · Expires ' + row.expires_at : ''}${row.content_truncated ? ' · Content truncated' : ''}`;
}
function cardFor(row, space, access) {
  const scope = selection;
  async function scopedApi(path, method = 'GET') {
    const result = await api(path, method);
    if (scope !== selection || space !== $('space').value) throw new Cancelled();
    return result;
  }
  const card = document.createElement('article'); card.className = 'card'; card.dataset.memoryId = row.id;
  const state = document.createElement('span'); state.className = 'badge';
  const content = document.createElement('pre'), meta = document.createElement('div'); meta.className = 'meta';
  function render(full) {
    state.textContent = `${full.state} · embedding ${full.embedding_status}${full.embedding_error ? ' · ' + full.embedding_error : ''}`;
    content.textContent = full.content; meta.textContent = metadata(full);
  }
  render(row);
  const actions = document.createElement('div'); actions.className = 'actions';
  function button(label, action, className) {
    const element = document.createElement('button'); element.textContent = label;
    if (className) element.className = className;
    element.onclick = async () => {
      element.disabled = true; message('');
      try { await action(); } catch (error) { if (!(error instanceof Cancelled)) message(error.message); }
      finally { if (element.isConnected) element.disabled = false; }
    };
    actions.append(element); return element;
  }
  button('Inspect / refresh', async () => { const {data} = await scopedApi(spacePath(space) + '/memories/' + row.id); render(data); });
  if (row.supersedes_id) button('View previous version', async () => {
    const {data} = await scopedApi(spacePath(space) + '/memories/' + row.supersedes_id);
    card.querySelector('.revision')?.remove();
    const previous = document.createElement('div'); previous.className = 'revision';
    const heading = document.createElement('strong'); heading.textContent = 'Previous version';
    const text = document.createElement('pre'); text.textContent = data.content;
    const info = document.createElement('div'); info.className = 'meta'; info.textContent = metadata(data);
    previous.append(heading, text, info); card.append(previous);
  });
  if (access.can_write && row.state === 'active') button('Correct', async () => {
    const {data} = await scopedApi(spacePath(space) + '/memories/' + row.id);
    if (data.state !== 'active') throw new Error('This memory is no longer active. Refresh before correcting it.');
    clearEditor(); $('supersedes').value = data.id; $('source').value = data.source_ref || '';
    $('content').value = data.content; $('editor').open = true; $('content').focus();
  });
  if (access.can_delete) button('Delete', async () => {
    if (!confirm('Delete this memory content and embedding? Its revision tombstone remains.')) return;
    await scopedApi(spacePath(space) + '/memories/' + row.id, 'DELETE'); offset = 0; pages = []; await search();
  }, 'danger');
  card.append(state, content, meta, actions); return card;
}
bind('connect-form', 'submit', async () => { const value = $('credential').value.trim(); resetSession(value); await connect(); });
bind('login-form', 'submit', async () => {
  const email = $('email').value, password = $('password').value; resetSession();
  const result = await api('/auth/login', 'POST', {email, password}, false);
  credential = result.data.access_token; await connect();
});
bind('disconnect', 'click', () => { resetSession(); message('Disconnected. Credentials and draft content cleared.'); });
bind('refresh', 'click', () => projects($('project').value, $('space').value));
bind('project', 'change', () => spaces());
bind('space', 'change', chooseSpace);
bind('search-form', 'submit', async () => { offset = 0; pages = []; await search(); });
bind('more', 'click', async () => { if (nextOffset !== null) { pages.push(offset); offset = nextOffset; await search(); } });
bind('previous', 'click', async () => { if (pages.length) { offset = pages.pop(); await search(); } });
bind('new-project', 'submit', async () => { const {data} = await api('/projects', 'POST', {name: $('project-name').value}); $('new-project').reset(); await projects(data.id); });
bind('new-space', 'submit', async () => { if (!$('project').value) throw new Error('Create a project first.'); const {data} = await api(`/projects/${$('project').value}/spaces`, 'POST', {name: $('space-name').value}); $('new-space').reset(); await spaces(data.id); });
bind('new-agent', 'submit', async () => {
  const {data} = await api('/projects/principals', 'POST', {name: $('agent-name').value});
  $('grant').reset(); $('principal-id').value = data.id; $('new-agent').reset();
  $('new-credential').textContent = `${data.name} · ${data.id}\n${data.api_key}`; $('new-credential').hidden = false;
});
bind('grant', 'submit', async () => {
  await api(spacePath() + '/grants/' + $('principal-id').value, 'PUT', {can_read: $('grant-read').checked, can_write: $('grant-write').checked, can_delete: $('grant-delete').checked});
  message('Permissions saved. Unchecked permissions are removed immediately.');
});
bind('revoke', 'click', async () => {
  if (!confirm('Revoke this agent credential?')) return;
  await api('/projects/principals/' + $('principal-id').value, 'DELETE');
  $('new-credential').textContent = ''; $('new-credential').hidden = true; $('grant').reset(); message('Credential revoked.');
});
bind('save-form', 'submit', async () => {
  const scope = selection;
  const body = {content: $('content').value, source_ref: $('source').value || null, supersedes_id: $('supersedes').value || null, expires_at: $('expires').value ? new Date($('expires').value).toISOString() : null};
  const fingerprint = JSON.stringify([spacePath(), body]);
  if (!pendingSave || pendingSave.fingerprint !== fingerprint) pendingSave = {fingerprint, key: crypto.randomUUID()};
  const {data} = await api(spacePath() + '/memories', 'POST', {...body, idempotency_key: pendingSave.key});
  if (scope !== selection) throw new Cancelled();
  clearEditor(); offset = 0; pages = [];
  try { await search(); message(`Saved ${data.id} · embedding ${data.embedding_status}`); }
  catch (error) { if (!(error instanceof Cancelled)) message(`Saved ${data.id}. Refresh failed: ${error.message}`); }
});
