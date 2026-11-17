/* Clone local do AFSESAB — menus idênticos ao portal real, dados FICTÍCIOS. */
(function () {
  'use strict';

  const MENU = [
    { id: 'dashboard', label: 'Dashboard', icon: '📊' },
    { id: 'cadastros', label: 'Cadastros', icon: '🗂', sub: [
      ['medicamento', 'Medicamento'], ['produto', 'Produto'],
      ['estabelecimento', 'Estabelecimento de Saúde'], ['paciente', 'Paciente'],
      ['programas', 'Programas de Saúde'], ['lista_medicamentos', 'Lista de Medicamentos'],
      ['profissional', 'Profissional'], ['carga_sigtap', 'Carga do SIGTAP'],
      ['fornecedor', 'Fornecedor/Fabricante'], ['almoxarifado', 'Almoxarifado'],
    ]},
    { id: 'administracao', label: 'Administração', icon: '⚙', sub: [
      ['usuarios', 'Usuários'], ['paciente_ext', 'Paciente Tratamento Ext'],
      ['paciente_insulina', 'Pacientes Tratamento Insulina'],
    ]},
    { id: 'planejamento', label: 'Planejamento Aquisição', icon: '📋', sub: [
      ['rel_planejamento', 'Relatório Planejamento de Aquisição'],
    ]},
    { id: 'ceaf', label: 'Componente Especializado', icon: '💊', sub: [
      ['lme', 'LME'], ['lme_transferencia', 'LME em Transferência'],
    ]},
    { id: 'farmacia', label: 'Farmácia', icon: '🏥', sub: [
      ['entrada', 'Entrada de Medicamentos'], ['pedido', 'Pedido'],
      ['ajuste_estoque', 'Ajuste de Estoque'], ['ajuste_vinculo', 'Ajuste de Vínculo'],
      ['transferencia', 'Transferência entre Unidades'], ['divergencia', 'Divergência de Entrega'],
    ]},
    { id: 'relatorios', label: 'Relatórios', icon: '📈', sub: [
      ['rel_autorizada_faturada', 'Quantidade Autorizada x Faturada'],
      ['rel_entrada', 'Entrada de Medicamentos'], ['rel_mapa', 'Mapa de Medicamentos'],
      ['rel_comprometimento', 'Relatório Comprometimento Estoque'], ['rel_indicadores', 'Indicadores'],
      ['rel_acompanhamento', 'Acompanhamento de Pedidos'], ['rel_distribuicao', 'Distribuição'],
      ['rel_ajuste_estoque', 'Ajuste de Estoque'], ['rel_posicao', 'Posição de Estoque'],
      ['rel_estoque_anterior', 'Estoque Dia Anterior'],
    ]},
    { id: 'rel-esp', label: 'Relatórios Especializado', icon: '📑', sub: [
      ['esp_lme', 'LME'], ['esp_glaucoma', 'Comparecimento de Pacientes Glaucoma'],
      ['esp_lme_glaucoma', 'LME Glaucoma'], ['esp_atendimentos', 'Consulta de Atendimentos'],
      ['esp_patologias', 'Patologias x Medicamentos'], ['esp_dispensacao', 'Dispensação'],
      ['esp_movimentos', 'Movimentos de Dispensa'], ['esp_paciente_status', 'Paciente LME por Status'],
      ['esp_pacientes_atendidos', 'Relatório de Pacientes Atendidos'],
      ['esp_deferidos', 'Pacientes Deferidos e Devolvidos'], ['esp_ativos', 'Relatório Pacientes Ativos'],
    ]},
    { id: 'rel-sigaf', label: 'Relatórios SIGAF', icon: '📊', sub: [
      ['sigaf_distribuicao', 'Distribuição SIGAF'], ['sigaf_ajuste_vinculo', 'Ajuste de Vínculo SIGAF'],
      ['sigaf_ajuste_estoque', 'Ajuste de Estoque SIGAF'], ['sigaf_exportar', 'Exportar Dados Estoque'],
    ]},
  ];

  const content = document.getElementById('content');
  const breadcrumb = document.getElementById('breadcrumb');
  const menuEl = document.getElementById('menu');
  const sidebar = document.querySelector('.sidebar');
  let currentViewKey = 'dashboard';
  let sessionUser = { nome: 'Usuário', perfil: 'Farmacêutico', username: 'usuario', unidade: '' };

  function renderMenu() {
    menuEl.innerHTML = '';
    for (const item of MENU) {
      const div = document.createElement('div');
      div.className = 'menu__item' + (item.id === 'dashboard' ? ' active' : '');
      div.innerHTML = `<span class="menu__icon">${item.icon}</span>
        <span class="menu__label">${item.label}</span>
        <span class="menu__chevron">${item.sub ? '›' : ''}</span>`;
      menuEl.appendChild(div);

      let subEl = null;
      if (item.sub) {
        subEl = document.createElement('div');
        subEl.className = 'submenu';
        for (const [key, label] of item.sub) {
          const s = document.createElement('div');
          s.className = 'submenu__item';
          s.textContent = label;
          s.addEventListener('click', () => openView(key, `${item.label} / ${label}`, s));
          subEl.appendChild(s);
        }
        menuEl.appendChild(subEl);
      }

      div.addEventListener('click', () => {
        if (subEl) {
          subEl.classList.toggle('open');
          div.classList.toggle('open');
        } else {
          openView(item.id, item.label, div);
        }
      });
    }
  }

  function setActive(el) {
    document.querySelectorAll('.menu__item.active, .submenu__item.active')
      .forEach(n => n.classList.remove('active'));
    if (el) el.classList.add('active');
  }

  function escapeHtml(value) {
    return String(value).replace(/[&<>"']/g, c => ({
      '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    })[c]);
  }

  function tableHtml(columns, rows, hasPdf, canAct) {
    const idIndex = columns.indexOf('ID');
    const statusIndex = columns.indexOf('Status');
    const head = columns.map(c => `<th>${escapeHtml(c)}</th>`).join('') + (canAct ? '<th>Ações</th>' : '');
    const currentStatus = (r) => statusIndex >= 0 ? String(r[statusIndex]).toLowerCase() : '';
    const actions = (r) => {
      const id = escapeHtml(r[idIndex]);
      const st = currentStatus(r);
      let html = `<button class="receipt-btn" data-id="${id}" title="Validar receita">📷</button>`;
      if (st === 'pendente' || st === '') {
        html += `<button class="status-btn" data-id="${id}" data-status="autorizada">Autorizar</button>`;
      }
      if (st === 'autorizada') {
        html += `<button class="status-btn" data-id="${id}" data-status="faturada">Faturar</button>`;
      }
      if (st === 'faturada') {
        html += `<button class="status-btn" data-id="${id}" data-status="dispensada">Dispensar</button>`;
      }
      if (st !== '' && st !== 'dispensada') {
        html += `<button class="status-btn status-btn--warn" data-id="${id}" data-status="pendente">Devolver</button>`;
      }
      return html;
    };

    const body = rows.map(r => `<tr>${r.map((v, i) => {
      if (hasPdf && columns[i] === 'ID') {
        return `<td><button class="pdf-btn" data-id="${escapeHtml(v)}" title="Abrir PDF da LME">📄 ${escapeHtml(v)}</button></td>`;
      }
      return `<td>${escapeHtml(v)}</td>`;
    }).join('')}${canAct ? `<td class="row-actions">${actions(r)}</td>` : ''}</tr>`).join('');
    return `<div class="panel"><table><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
  }

  async function openDashboard() {
    const s = await window.afPortal.getStats();
    const p = s.por_status || {};
    const total = s.total_lmes || 1;
    const cores = { faturada: '#f39c12', autorizada: '#2f9e8f', pendente: '#e74c3c', dispensada: '#4a90d9' };

    let acc = 0;
    const segments = Object.entries(p).map(([key, value]) => {
      const start = acc;
      acc += (value / total) * 100;
      return `${cores[key] || '#78909c'} ${start}% ${acc}%`;
    }).join(', ');
    const legend = Object.entries(p).map(([key, value]) =>
      `<span class="legend-item"><i style="background:${cores[key] || '#78909c'}"></i>${key} <b>${value}</b></span>`
    ).join('');

    const tops = Object.entries(s.top_medicamentos || {});
    const max = Math.max(1, ...tops.map(x => x[1]));
    const bars = tops.map(([name, qty]) =>
      `<div class="bar-row"><span class="bar-label">${escapeHtml(name)}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${(qty / max) * 100}%"></div></div>
        <span class="bar-value">${qty}</span></div>`
    ).join('');

    content.innerHTML = `<h2>Dashboard</h2>
      <div class="cards">
        <div class="card"><div class="card__title">Usuários atendidos</div><div class="card__value">${s.total_usuarios.toLocaleString('pt-BR')}</div></div>
        <div class="card"><div class="card__title">LMEs no sistema</div><div class="card__value">${s.total_lmes.toLocaleString('pt-BR')}</div></div>
        <div class="card card--amber"><div class="card__title">Faturadas</div><div class="card__value">${(p.faturada || 0).toLocaleString('pt-BR')}</div></div>
        <div class="card"><div class="card__title">Autorizadas</div><div class="card__value">${(p.autorizada || 0).toLocaleString('pt-BR')}</div></div>
        <div class="card card--red"><div class="card__title">Pendentes</div><div class="card__value">${(p.pendente || 0).toLocaleString('pt-BR')}</div></div>
        <div class="card"><div class="card__title">Dispensadas</div><div class="card__value">${(p.dispensada || 0).toLocaleString('pt-BR')}</div></div>
      </div>
      <div class="charts">
        <div class="chart-card">
          <h3>Distribuição por status</h3>
          <div class="chart-body">
            <div class="donut" style="background:conic-gradient(${segments})"><div class="donut-hole">${s.total_lmes.toLocaleString('pt-BR')}<small>LMEs</small></div></div>
            <div class="legend">${legend}</div>
          </div>
        </div>
        <div class="chart-card">
          <h3>Medicamentos mais solicitados</h3>
          <div class="bars">${bars}</div>
        </div>
      </div>`;

    try {
      const alerts = await window.afPortal.getAlerts();
      const items = (alerts.achados || []).slice(0, 6).map(a =>
        `<div class="alert-item alert-${escapeHtml(a.severidade)}"><b>${escapeHtml(a.titulo)}</b><br>${escapeHtml(a.detalhe)}</div>`
      ).join('');
      content.insertAdjacentHTML('beforeend',
        `<div class="chart-card" style="margin-top:14px"><h3>Alertas operacionais (IA)</h3>${items}</div>`);
    } catch (_) { /* alertas são opcionais */ }
  }

  async function openView(key, title, el) {
    setActive(el);
    breadcrumb.textContent = title;
    currentViewKey = key;
    content.innerHTML = '<div class="loading">Carregando registros…</div>';

    try {
      if (key === 'dashboard') return await openDashboard();
      const view = await window.afPortal.getView(key);
      const podeCadastrar = key === 'medicamento' || key === 'lista_medicamentos';
      const canAct = view.columns.includes('ID') && view.columns.includes('Status') && view.has_pdf;
      content.innerHTML = `<h2>${escapeHtml(view.title)}</h2>
        <div class="toolbar">
          <input id="filtro" placeholder="Filtrar nesta tela…" />
          ${view.columns.includes('Paciente') ? '<input id="filtro-paciente" placeholder="Filtrar por paciente…" />' : ''}
          ${podeCadastrar ? '<button class="btn-new" id="btn-new-med">+ Novo medicamento</button>' : ''}
          <button class="btn-export" data-formato="csv">↓ CSV</button>
          <button class="btn-export" data-formato="pdf">↓ PDF</button>
          <span class="toolbar-info">${view.rows.length} registros</span>
        </div>
        <div id="tabela">${tableHtml(view.columns, view.rows, view.has_pdf, canAct)}</div>
        <p class="nota">${escapeHtml(view.note)}</p>`;

      const input = document.getElementById('filtro');
      const patientInput = document.getElementById('filtro-paciente');
      const applyFilters = () => {
        const q = input.value.trim().toLowerCase();
        const pq = patientInput ? patientInput.value.trim().toLowerCase() : '';
        const patientIndex = view.columns.indexOf('Paciente');
        const filtered = view.rows.filter(r => {
          const okGeral = !q || r.some(v => String(v).toLowerCase().includes(q));
          const okPaciente = !pq || (patientIndex >= 0 && String(r[patientIndex]).toLowerCase().includes(pq));
          return okGeral && okPaciente;
        });
        document.getElementById('tabela').innerHTML = tableHtml(view.columns, filtered, view.has_pdf, canAct);
        const info = document.querySelector('.toolbar-info');
        if (info) info.textContent = `${filtered.length} registros`;
      };
      input.addEventListener('input', applyFilters);
      if (patientInput) patientInput.addEventListener('input', applyFilters);
    } catch (err) {
      content.innerHTML = `<div class="loading">Erro ao carregar: ${escapeHtml(err.message || err)}</div>`;
    }
  }

  const modal = document.getElementById('modal-med');
  document.addEventListener('click', (event) => {
    if (event.target.id === 'btn-new-med') modal.classList.add('open');
    if (event.target.id === 'med-cancel') modal.classList.remove('open');
  });
  document.getElementById('form-med').addEventListener('submit', async (event) => {
    event.preventDefault();
    const btn = event.target.querySelector('button[type=submit]');
    btn.disabled = true;
    try {
      await window.afPortal.createMedication(
        document.getElementById('med-nome').value,
        document.getElementById('med-principio').value,
        document.getElementById('med-apresentacao').value,
      );
      modal.classList.remove('open');
      event.target.reset();
      await openView('medicamento', 'Medicamento', document.querySelector('.menu__item'));
    } catch (err) {
      alert('Não foi possível cadastrar: ' + (err.message || err));
    } finally {
      btn.disabled = false;
    }
  });

  // Delegação global: funciona também após a tabela ser filtrada.
  document.addEventListener('click', async (event) => {
    const actionBtn = event.target.closest('.status-btn');
    if (actionBtn) {
      actionBtn.disabled = true;
      try {
        await window.afPortal.setStatus(
          Number(actionBtn.dataset.id), actionBtn.dataset.status, 'Ação via painel administrativo',
        );
        await openView(currentViewKey, breadcrumb.textContent, document.querySelector('.submenu__item.active') || document.querySelector('.menu__item.active'));
      } catch (err) {
        alert('Não foi possível alterar: ' + (err.message || err));
        actionBtn.disabled = false;
      }
      return;
    }

    const receiptBtn = event.target.closest('.receipt-btn');
    if (receiptBtn) {
      receiptBtn.disabled = true;
      try {
        const result = await window.afPortal.validateLmeReceipt(Number(receiptBtn.dataset.id));
        if (result) {
          showInfo('Validação da receita',
            `<p><b>Status:</b> ${escapeHtml(result.status)}</p>` +
            `<p><b>Inconsistências:</b> ${(result.inconsistencies || []).map(escapeHtml).join('; ') || 'nenhuma'}</p>` +
            `<p><b>Princípio ativo:</b> ${escapeHtml(result.extracted?.activeIngredient || '—')}</p>`);
        }
      } catch (err) {
        alert('Não foi possível validar: ' + (err.message || err));
      } finally {
        receiptBtn.disabled = false;
      }
      return;
    }

    const exportBtn = event.target.closest('.btn-export');
    if (exportBtn) {
      exportBtn.disabled = true;
      const old = exportBtn.textContent;
      exportBtn.textContent = 'Exportando…';
      try {
        const path = await window.afPortal.exportView(currentViewKey, exportBtn.dataset.formato);
        alert(`Relatório salvo em:\n${path}`);
      } catch (err) {
        alert('Não foi possível exportar: ' + (err.message || err));
      } finally {
        exportBtn.textContent = old;
        exportBtn.disabled = false;
      }
      return;
    }

    const btn = event.target.closest('.pdf-btn');
    if (!btn) return;
    btn.disabled = true;
    try {
      await window.afPortal.openPdf(Number(btn.dataset.id));
    } catch (err) {
      alert('Não foi possível abrir o PDF: ' + (err.message || err));
    } finally {
      btn.disabled = false;
    }
  });

  const infoModal = document.getElementById('modal-info');
  const infoTitle = document.getElementById('info-title');
  const infoBody = document.getElementById('info-body');
  const showInfo = (title, html) => {
    infoTitle.textContent = title;
    infoBody.innerHTML = html;
    infoModal.classList.add('open');
  };
  document.getElementById('info-close').addEventListener('click', () => infoModal.classList.remove('open'));

  document.getElementById('btn-menu').addEventListener('click', () => {
    sidebar.classList.toggle('collapsed');
    const btn = document.getElementById('btn-menu');
    btn.textContent = sidebar.classList.contains('collapsed') ? '☰' : '☰';
    btn.title = sidebar.classList.contains('collapsed') ? 'Expandir menu' : 'Recolher menu';
  });

  document.getElementById('btn-help').addEventListener('click', () => showInfo(
    'Ajuda rápida',
    '<p><b>Navegação:</b> use o menu lateral para abrir cadastros, LMEs, farmácia e relatórios.</p>' +
    '<p><b>Copiloto:</b> selecione um termo no painel do AFSESAB ou digite em um campo; o painel direito captura somente dados clínicos.</p>' +
    '<p><b>Relatórios:</b> use os botões CSV/PDF para exportar a tela atual.</p>' +
    '<p><b>IA:</b> pergunte sobre fornecedores, LMEs pendentes ou gere insights para o administrador.</p>',
  ));

  document.getElementById('btn-user').addEventListener('click', () => showInfo(
    'Meu perfil',
    `<p><b>Nome:</b> ${escapeHtml(sessionUser.nome)}</p>` +
    `<p><b>Perfil:</b> ${escapeHtml(sessionUser.perfil)}</p>` +
    `<p><b>E-mail:</b> ${escapeHtml(sessionUser.username)}@sesab.ba.gov.br</p>` +
    `<p><b>Unidade:</b> ${escapeHtml(sessionUser.unidade)}</p>`,
  ));

  document.getElementById('btn-logout').addEventListener('click', async () => {
    await window.afPortal.logout();
  });

  const doSearch = async () => {
    const q = document.getElementById('global-search').value.trim();
    if (!q) return;
    const result = await window.afPortal.askAdmin(q);
    const rows = result.rows.slice(0, 30).map(r => r.map(escapeHtml).join(' | ')).join('<br>');
    showInfo(`Busca: ${q}`, `<p>${escapeHtml(result.answer)}</p><div class="info-body">${rows}</div>`);
  };
  document.getElementById('btn-search').addEventListener('click', doSearch);
  document.getElementById('global-search').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') doSearch();
  });

  document.getElementById('btn-audit-view').addEventListener('click', async () => {
    try {
      const logs = await window.afPortal.getAudit();
      const rows = logs.slice(0, 40).map(l =>
        `${escapeHtml(String(l.created_at).slice(0, 16))} | ${escapeHtml(String(l.actor))} | ${escapeHtml(String(l.acao))} | ${escapeHtml(String(l.detalhes))}`
      ).join('<br>');
      showInfo('Log de auditoria', `<div class="info-body">${rows || 'Nenhuma ação registrada.'}</div>` +
        '<div class="modal__actions"><button type="button" class="btn-pri" id="audit-csv">Exportar CSV</button></div>');
      document.getElementById('audit-csv').addEventListener('click', async () => {
        await window.afPortal.exportAudit('csv');
      });
    } catch (err) {
      alert('Não foi possível carregar a auditoria: ' + (err.message || err));
    }
  });

  async function init() {
    renderMenu();
    try {
      const session = await window.afPortal.getSession();
      sessionUser = session;
      document.getElementById('clone-user').textContent = session.nome || session.username;
      document.getElementById('clone-profile').textContent = session.perfil || 'Farmacêutico';
      document.getElementById('clone-email').textContent = session.username + '@sesab.ba.gov.br';
      document.getElementById('unit').textContent = session.unidade || '';
    } catch (_) { /* sessão opcional */ }
    openView('dashboard', 'Dashboard', document.querySelector('.menu__item'));
  }

  init();
})();
