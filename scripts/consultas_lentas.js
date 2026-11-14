function requiredEnv(name) {
  const value = process.env[name];
  if (!value) {
    throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
  }
  return value;
}

const authResult = db
  .getSiblingDB("admin")
  .auth(
    requiredEnv("MONGO_INITDB_ROOT_USERNAME"),
    requiredEnv("MONGO_INITDB_ROOT_PASSWORD"),
  );
if (authResult !== 1 && (!authResult || authResult.ok !== 1)) {
  throw new Error("Não foi possível autenticar o usuário administrador.");
}

const appDb = db.getSiblingDB("lme");
const pacientes = appDb.getCollection("pacientes");
const consultaSelecionada = process.env.CONSULTA_LENTA || "todas";

const consultas = {
  cidade: {
    descricao: "Cidade + status + vigencia",
    filtro: {
      cidade: "Santo Antônio de Jesus",
      "lme.status": "ATIVA",
      "lme.vigencia_fim": {
        $gte: new Date().toISOString().slice(0, 10),
      },
    },
    indice: {
      cidade: 1,
      "lme.status": 1,
      "lme.vigencia_fim": 1,
    },
    nomeIndice: "cidade_status_vigencia",
  },
  medicamento: {
    descricao: "Medicamento + status",
    filtro: {
      "lme.medicamento": "Adalimumabe 40mg",
      "lme.status": "ATIVA",
    },
    indice: {
      "lme.medicamento": 1,
      "lme.status": 1,
    },
    nomeIndice: "medicamento_status",
  },
};

if (consultaSelecionada !== "todas" && !consultas[consultaSelecionada]) {
  throw new Error(
    "CONSULTA_LENTA deve ser 'cidade', 'medicamento' ou 'todas'.",
  );
}

function findStages(value, stages = []) {
  if (!value || typeof value !== "object") {
    return stages;
  }
  if (typeof value.stage === "string") {
    stages.push(value.stage);
  }
  for (const child of Object.values(value)) {
    if (Array.isArray(child)) {
      child.forEach((item) => findStages(item, stages));
    } else if (child && typeof child === "object") {
      findStages(child, stages);
    }
  }
  return stages;
}

function printExplain(consulta, etapa, explain) {
  const stats = explain.executionStats;
  const stages = [...new Set(findStages(explain.queryPlanner.winningPlan))];
  printjson({
    consulta: consulta.descricao,
    etapa,
    winningPlanStages: stages,
    nReturned: stats.nReturned,
    docsExamined: stats.totalDocsExamined,
    keysExamined: stats.totalKeysExamined,
    executionTimeMillis: stats.executionTimeMillis,
  });
}

function measure(consulta) {
  print(`\n=== ${consulta.descricao} ===`);

  const beforeIndex = pacientes
    .find(consulta.filtro)
    .hint({ $natural: 1 })
    .explain("executionStats");
  printExplain(consulta, "sem indice (COLLSCAN forcado)", beforeIndex);

  pacientes.createIndex(consulta.indice, { name: consulta.nomeIndice });

  const afterIndex = pacientes.find(consulta.filtro).explain("executionStats");
  printExplain(consulta, "com indice", afterIndex);
}

if (consultaSelecionada === "todas" || consultaSelecionada === "cidade") {
  measure(consultas.cidade);
}
if (consultaSelecionada === "todas" || consultaSelecionada === "medicamento") {
  measure(consultas.medicamento);
}
