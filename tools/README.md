# Ferramentas REA (Reverse Engineering & Analysis)

Script de calibração que conecta ao **seu Chrome já logado** no AFSESAB via CDP
e mapeia a estrutura da SPA para ajustar os seletores do copiloto.

## 1. Preparar o Chrome com remote debugging

Opção A — abrir um perfil dedicado e fazer login uma vez:

```powershell
& "C:\Program Files\Google\Chrome\Application\chrome.exe" `
  --remote-debugging-port=9222 `
  --user-data-dir="C:\Users\$env:USERNAME\AppData\Local\Temp\af-chrome-profile" `
  "https://afsesab.sesab.ba.gov.br/#/"
```

Opção B — se o Chrome já estiver rodando com `--remote-debugging-port=9222`,
basta usá-lo diretamente (não é possível adicionar a flag a um processo já iniciado).

## 2. Rodar a captura

```powershell
cd C:\Users\offsechen1\Desktop\AF\tools
npm install
npm run capture
```

Saídas:

- `recon/dom-map.json` — seletores CSS/XPath, iframes e URLs dos bundles JS;
- `recon/js/*.js` — cópia dos bundles para análise estática;
- `recon/routes/*.json` — mapeamento das telas `lista-medicamento`, `lme`,
  `cid`, `consulta-atendimento` e `parametros-pcdt-list` (via `node capture-routes.mjs`);
- `node analyze-bundle.mjs recon/js/app.*.js` — extrai rotas/endpoints do bundle.

Resultado já obtido nesta sessão (Chrome autenticado, 2026-11-16):
- 63 elementos no dashboard, 3 bundles (app 2.7 MB, vendor 3.8 MB);
- SPA em **Vuetify 1.x**, filtros identificados por `placeholder` (sem `name`/`id`);
- tela LME expõe CPF/CNS/Nome do Paciente/Prontuário -> campos bloqueados no REA;
- rotas úteis: `#/app/lista-medicamento`, `#/app/lme`, `#/app/cid`,
  `#/app/parametros-pcdt-list`.

> **Privacidade:** o script não captura `value` de campos nem texto de pacientes.
> Apenas estrutura e URLs de assets.

## 3. Usar o resultado

1. Abra `recon/dom-map.json` e identifique os seletores dos campos de busca
   (medicamento, princípio ativo, CID/IME).
2. Compare com `desktop-client/src/main/rea/webview-preload.ts`.
3. Ajuste `CLINICAL_LEXICON` em ambos os lados (client e backend) com os termos
   encontrados nos bundles/PCDTs.

Alternativamente, no próprio app use o botão **Inspecionar estrutura da tela**,
que executa o mesmo mapeamento de dentro do BrowserView autenticado.
