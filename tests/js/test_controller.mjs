// Exercita o debugger_controller.js REAL do Exportador, sob um `chrome`
// simulado. Nao substitui o smoke em Chrome de verdade — prova a LOGICA do
// controller (alvo, recusas, normalizacao), que e o que da para provar sem
// o navegador instalado.
//
// Rode: node tests/js/test_controller.mjs
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';

const CAMINHO = '/media/sf_sf_exportador/claude-exporter-v4.2/copilot/debugger_controller.js';
const TAB = 42, ORIGEM = 'http://127.0.0.1:8000';
const PROTOCOLO = 'edp.browser.v1';

let falhas = 0, feitos = 0;
async function teste(nome, fn) {
  try { await fn(); feitos++; console.log(`  ok   ${nome}`); }
  catch (e) { falhas++; console.log(`  FALHA ${nome}\n        ${e.message}`); }
}

/** Monta um mundo novo: chrome falso + o controller real dentro dele. */
function mundo({ tabUrl = ORIGEM + '/dashboard', anexado = true,
                 abaExiste = true, comandos = {} } = {}) {
  const chamados = [];
  const chrome = {
    tabs: {
      get: async (id) => {
        if (!abaExiste) throw new Error('No tab with id');
        return { id, url: tabUrl };
      },
    },
    debugger: {
      attach: async () => {},
      detach: async () => {},
      getTargets: async () => (anexado
        ? [{ tabId: TAB, attached: true, type: 'page', url: tabUrl }] : []),
      sendCommand: async (alvo, nome, params) => {
        chamados.push({ tabId: alvo.tabId, nome, params });
        if (comandos[nome]) return comandos[nome];
        if (nome === 'Runtime.evaluate') {
          return { result: { value: { url: tabUrl, title: 'EDP Runtime' } } };
        }
        if (nome === 'DOM.getDocument') {
          return { root: { children: [{ children: [] }, { children: [] }] } };
        }
        if (nome === 'Page.getNavigationHistory') return { entries: [1, 2, 3] };
        return {};
      },
    },
  };
  const ctx = vm.createContext({ chrome, window: {}, URL, console,
                                 setTimeout, clearTimeout, Promise, Date });
  vm.runInContext(readFileSync(CAMINHO, 'utf8'), ctx, { filename: CAMINHO });
  const C = ctx.window.CopilotController;
  // A resposta atravessa JSON de verdade (vai por HTTP ate o Runtime). Passar
  // por JSON aqui e mais fiel que comparar o objeto do outro realm do `vm` —
  // e de quebra evita o falso negativo de deepEqual entre realms.
  const executar = async (p) => JSON.parse(JSON.stringify(await C.executar(p)));
  return { C, executar, chamados, chrome };
}

function pedido(extra = {}) {
  return { protocol: PROTOCOLO, kind: 'capability.request',
           request_id: 'R-abc', capability: 'browser.inspect',
           target: { tab_id: TAB, origin: ORIGEM, session_id: 'S-1' }, ...extra };
}

console.log('debugger_controller.js — controller real, chrome simulado\n');

// ── caminho feliz: register -> attach -> inspect -> observation ────────────
await teste('register -> attach -> inspect devolve as tres observacoes', async () => {
  const { C, executar, chamados } = mundo();
  await C.registrarAlvo(TAB, 'S-1');
  await C.anexar(TAB);
  const r = await executar(pedido());
  assert.equal(r.type, 'browser.observation', JSON.stringify(r));
  assert.equal(r.protocol, PROTOCOLO);
  assert.deepEqual(r.target, { tab_id: TAB, origin: ORIGEM });
  const kinds = r.observations.map(o => o.kind).sort();
  assert.deepEqual(kinds, ['dom', 'history', 'page']);
  assert.equal(r.observations.find(o => o.kind === 'page').url, ORIGEM + '/dashboard');
  assert.equal(r.observations.find(o => o.kind === 'dom').dom_nodes, 3);
  assert.equal(r.observations.find(o => o.kind === 'history').history_len, 3);
  // so os tres comandos permitidos, e so na aba alvo
  const nomes = chamados.filter(c => c.nome !== 'DOM.enable' && c.nome !== 'Page.enable')
                        .map(c => c.nome);
  assert.deepEqual([...new Set(nomes)].sort(),
    ['DOM.getDocument', 'Page.getNavigationHistory', 'Runtime.evaluate']);
  assert.ok(chamados.every(c => c.tabId === TAB), 'comando fora da aba alvo');
});

await teste('inspect sem registrar alvo e recusado', async () => {
  const { C, executar, chamados } = mundo();
  const r = await executar(pedido());
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /nenhum alvo registrado/);
  assert.equal(chamados.length, 0, 'mandou comando CDP sem alvo');
});

// ── NEGATIVO 1: target errado ──────────────────────────────────────────────
await teste('NEGATIVO target errado -> REJECT', async () => {
  const { C, executar, chamados } = mundo();
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const antes = chamados.length;
  const r = await executar(pedido({ target: { tab_id: 999, origin: ORIGEM } }));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /não é o alvo/);
  assert.equal(chamados.length, antes, 'executou comando na aba errada');
});

await teste('NEGATIVO origem diferente no pedido -> REJECT', async () => {
  const { C, executar } = mundo();
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const r = await executar(pedido({
    target: { tab_id: TAB, origin: 'https://example.com' } }));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /origem autorizada/);
});

// ── NEGATIVO 2: a aba mudou de origem DEPOIS do registro ───────────────────
await teste('NEGATIVO origem mudou depois do registro -> REJECT', async () => {
  const m = mundo();
  await m.C.registrarAlvo(TAB, 'S-1'); await m.C.anexar(TAB);
  // o usuario navegou a aba para outro site
  m.chrome.tabs.get = async (id) => ({ id, url: 'https://example.com/qualquer' });
  const r = JSON.parse(JSON.stringify(await m.C.executar(pedido())));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /mudou de origem/);
  assert.equal(m.C.alvoAtual(), null, 'alvo nao foi invalidado');
});

// ── NEGATIVO 3: debugger desanexado ────────────────────────────────────────
await teste('NEGATIVO debugger desanexado -> REJECT', async () => {
  const m = mundo();
  await m.C.registrarAlvo(TAB, 'S-1'); await m.C.anexar(TAB);
  m.chrome.debugger.getTargets = async () => [];      // alguem desanexou
  const r = JSON.parse(JSON.stringify(await m.C.executar(pedido())));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /não está anexado/);
});

await teste('NEGATIVO aba fechada -> REJECT e invalida o alvo', async () => {
  const m = mundo();
  await m.C.registrarAlvo(TAB, 'S-1'); await m.C.anexar(TAB);
  m.chrome.tabs.get = async () => { throw new Error('No tab with id 42'); };
  const r = JSON.parse(JSON.stringify(await m.C.executar(pedido())));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /não está mais aberta/);
  assert.equal(m.C.alvoAtual(), null);
});

// ── registro so em loopback ────────────────────────────────────────────────
for (const url of ['https://example.com/x', 'https://claude.ai/chat',
                   'http://10.0.0.5:8000/d', 'https://127.0.0.1:8000/d']) {
  await teste(`NEGATIVO registrar alvo em ${url} -> REJECT`, async () => {
    const { C, executar } = mundo({ tabUrl: url });
    await assert.rejects(() => C.registrarAlvo(TAB, 'S-1'), /loopback/);
    assert.equal(C.alvoAtual(), null);
  });
}

// ── superficie: capacidade e comando ───────────────────────────────────────
await teste('capacidade desconhecida -> REJECT', async () => {
  const { C, executar, chamados } = mundo();
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const antes = chamados.length;
  for (const cap of ['browser.click', 'browser.evaluate', 'act.navigate']) {
    const r = await executar(pedido({ capability: cap }));
    assert.equal(r.type, 'browser.error');
    assert.match(r.error, /não implementada/);
  }
  assert.equal(chamados.length, antes);
});

await teste('comando fora da capacidade nao e obedecido', async () => {
  const { C, executar, chamados } = mundo();
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const antes = chamados.length;
  const r = await executar(pedido({
    comandos: ['Runtime.evaluate', 'Page.navigate', 'Input.dispatchKeyEvent'] }));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /fora da capacidade/);
  assert.equal(chamados.length, antes, 'obedeceu comando vindo de fora');
});

await teste('protocolo desconhecido -> REJECT', async () => {
  const { C, executar } = mundo();
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const r = await executar(pedido({ protocol: 'outro.v9' }));
  assert.equal(r.type, 'browser.error');
  assert.match(r.error, /protocolo desconhecido/);
});

// ── nenhum segredo atravessa ───────────────────────────────────────────────
await teste('objeto Chrome cru nao vira observacao', async () => {
  const { C, executar } = mundo({ comandos: {
    'Runtime.evaluate': { result: { value: {
      url: ORIGEM + '/dashboard', title: 'EDP',
      cookie: 'sess=SEGREDO', apiKey: 'sk-ant-SEGREDO' } },
      exceptionDetails: { text: 'sk-ant-SEGREDO' } } } });
  await C.registrarAlvo(TAB, 'S-1'); await C.anexar(TAB);
  const r = await executar(pedido());
  const txt = JSON.stringify(r);
  assert.ok(!txt.includes('SEGREDO'), 'segredo atravessou: ' + txt.slice(0, 200));
  assert.ok(!txt.includes('exceptionDetails'));
});

console.log(`\n${feitos} ok, ${falhas} falha(s)`);
process.exit(falhas ? 1 : 0);
