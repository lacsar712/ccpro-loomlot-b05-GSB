<script>
  import { onMount } from 'svelte';
  import { api } from '../lib/api.js';

  let rows = [];
  let error = '';
  let reusedOnly = false;
  // waterReused 用 '' 表示尚未选择（新建时必选），保存时转布尔
  let form = { name: '', waterHardnessMgL: 120, waterReused: '', waterNote: '', notes: '' };
  let editing = null;

  async function load() {
    error = '';
    try {
      const query = reusedOnly ? '?reusedOnly=true' : '';
      rows = await api(`/dye-houses${query}`);
    } catch (e) {
      error = e.message;
    }
  }

  onMount(load);

  function resetForm() {
    form = { name: '', waterHardnessMgL: 120, waterReused: '', waterNote: '', notes: '' };
    editing = null;
  }

  async function save() {
    error = '';
    const hardness = Number(form.waterHardnessMgL);
    if (!form.name.trim()) {
      error = '请填写染坊名称';
      return;
    }
    if (!Number.isFinite(hardness) || hardness < 0 || hardness > 500) {
      error = '水源硬度须在 0 到 500 mg/L 之间';
      return;
    }
    if (form.waterReused === '') {
      error = '请选择是否回用水';
      return;
    }
    try {
      const body = {
        name: form.name.trim(),
        waterHardnessMgL: hardness,
        waterReused: form.waterReused === 'true',
        waterNote: form.waterNote.trim() || null,
        notes: form.notes.trim() || null,
      };
      if (editing) {
        await api(`/dye-houses/${editing}`, { method: 'PUT', body: JSON.stringify(body) });
      } else {
        await api('/dye-houses', { method: 'POST', body: JSON.stringify(body) });
      }
      resetForm();
      await load();
    } catch (e) {
      error = e.message;
    }
  }

  function startEdit(row) {
    editing = row.id;
    form = {
      name: row.name,
      waterHardnessMgL: row.waterHardnessMgL,
      waterReused: String(row.waterReused),
      waterNote: row.waterNote || '',
      notes: row.notes || '',
    };
  }

  async function remove(id) {
    if (!confirm('确认删除该染坊？')) return;
    error = '';
    try {
      await api(`/dye-houses/${id}`, { method: 'DELETE' });
      await load();
    } catch (e) {
      error = e.message;
    }
  }
</script>

<h1 class="page-title">染坊</h1>
<p class="page-sub">
  维护坊名、水源硬度（mg/L，0–500）与是否回用水；原自由文本用水说明改为可选备注。
  硬度 &gt; 200mg/L 时该坊染程布重不得超过 30kg；回用水坊染缸纤维禁用含「棉」。
</p>

<div class="panel" style="margin-bottom:1rem;">
  <div class="form-grid">
    <label>名称 <input bind:value={form.name} /></label>
    <label
      >水源硬度 mg/L（0–500）
      <input type="number" min="0" max="500" step="1" bind:value={form.waterHardnessMgL} />
    </label>
    <label
      >是否回用水（必选）
      <select bind:value={form.waterReused}>
        <option value="" disabled>请选择</option>
        <option value="false">否</option>
        <option value="true">是</option>
      </select>
    </label>
    <label>用水说明（可选备注） <input bind:value={form.waterNote} /></label>
    <label>备注 <input bind:value={form.notes} /></label>
  </div>
  <div class="toolbar">
    <button class="btn" type="button" on:click={save}>{editing ? '保存修改' : '新建染坊'}</button>
    {#if editing}
      <button class="btn ghost" type="button" on:click={resetForm}>取消</button>
    {/if}
  </div>
  {#if error}<p class="err">{error}</p>{/if}
</div>

<div class="panel">
  <div class="toolbar" style="margin-bottom:0.75rem;">
    <label style="display:flex;align-items:center;gap:0.4rem;margin:0;">
      <input type="checkbox" bind:checked={reusedOnly} on:change={load} />
      仅看回用水坊
    </label>
  </div>
  <table>
    <thead>
      <tr>
        <th>ID</th>
        <th>名称</th>
        <th>硬度 mg/L</th>
        <th>回用水</th>
        <th>用水说明</th>
        <th>备注</th>
        <th></th>
      </tr>
    </thead>
    <tbody>
      {#each rows as row}
        <tr>
          <td>{row.id}</td>
          <td>{row.name}</td>
          <td>{row.waterHardnessMgL}{row.waterHardnessMgL > 200 ? ' ⚠' : ''}</td>
          <td>{row.waterReused ? '是' : '否'}</td>
          <td>{row.waterNote || '—'}</td>
          <td>{row.notes || '—'}</td>
          <td class="row-actions">
            <button class="btn ghost small" type="button" on:click={() => startEdit(row)}>编辑</button>
            <button class="btn danger small" type="button" on:click={() => remove(row.id)}>删除</button>
          </td>
        </tr>
      {/each}
    </tbody>
  </table>
</div>
