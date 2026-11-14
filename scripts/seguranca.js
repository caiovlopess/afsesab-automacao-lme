const env = process.env;

function requiredEnv(name) {
  const value = env[name];
  if (!value) {
    throw new Error(`Variável de ambiente obrigatória ausente: ${name}`);
  }
  return value;
}

const rootUser = requiredEnv("MONGO_INITDB_ROOT_USERNAME");
const rootPassword = requiredEnv("MONGO_INITDB_ROOT_PASSWORD");
const authResult = db.getSiblingDB("admin").auth(rootUser, rootPassword);
if (authResult !== 1 && (!authResult || authResult.ok !== 1)) {
  throw new Error("Não foi possível autenticar o usuário administrador.");
}

const appDb = db.getSiblingDB("lme");
const patientCollection = appDb.getCollectionInfos({ name: "pacientes" })[0];
if (!patientCollection || patientCollection.type !== "collection") {
  throw new Error("Crie a coleção pacientes com scripts/gerar_dados.py primeiro.");
}

const cityViews = [
  { name: "pacientes_sai", city: "Santo Antônio de Jesus" },
  { name: "pacientes_amargosa", city: "Amargosa" },
  { name: "pacientes_nazare", city: "Nazaré" },
  { name: "pacientes_cruz", city: "Cruz das Almas" },
];

function viewPipeline(city) {
  const cpfDigits = {
    $replaceAll: {
      input: {
        $replaceAll: { input: "$cpf", find: ".", replacement: "" },
      },
      find: "-",
      replacement: "",
    },
  };

  return [
    { $match: { cidade: city } },
    {
      $project: {
        _id: 0,
        nome: 1,
        cidade: 1,
        lme: 1,
        cpf: {
          $concat: ["***.***.***-", { $substrBytes: [cpfDigits, 9, 2] }],
        },
      },
    },
  ];
}

for (const view of cityViews) {
  const existing = appDb.getCollectionInfos({ name: view.name })[0];
  if (existing) {
    if (existing.type !== "view") {
      throw new Error(`Já existe uma coleção que não é view: ${view.name}`);
    }
    appDb.getCollection(view.name).drop();
  }
  appDb.createView(view.name, "pacientes", viewPipeline(view.city));
}

const auditCollection = appDb.getCollectionInfos({ name: "audit_log" })[0];
if (!auditCollection) {
  appDb.createCollection("audit_log");
} else if (auditCollection.type !== "collection") {
  throw new Error("audit_log existe, mas não é uma coleção.");
}

const viewPrivileges = cityViews.map((view) => ({
  resource: { db: "lme", collection: view.name },
  actions: ["find"],
}));

function upsertRole(roleName, privileges) {
  const role = appDb.getRole(roleName);
  if (role) {
    appDb.updateRole(roleName, { privileges, roles: [] });
  } else {
    appDb.createRole({ role: roleName, privileges, roles: [] });
  }
}

upsertRole("farmaceutico_sai", [
  {
    resource: { db: "lme", collection: "pacientes_sai" },
    actions: ["find"],
  },
]);
upsertRole("auditor", [
  {
    resource: { db: "lme", collection: "audit_log" },
    actions: ["find"],
  },
  ...viewPrivileges,
]);
upsertRole("ia_leitura", [
  ...viewPrivileges,
  {
    resource: { db: "lme", collection: "audit_log" },
    actions: ["insert"],
  },
]);
upsertRole("workflow_audit", [
  {
    resource: { db: "lme", collection: "audit_log" },
    actions: ["insert"],
  },
]);

function upsertTestUser(userName, password, roleName) {
  const user = appDb.getUser(userName);
  const options = {
    pwd: password,
    roles: [{ role: roleName, db: "lme" }],
  };
  if (user) {
    appDb.updateUser(userName, options);
  } else {
    appDb.createUser({ user: userName, ...options });
  }
}

upsertTestUser(
  "teste_farmaceutico_sai",
  requiredEnv("TEST_FARMACEUTICO_SAI_PASSWORD"),
  "farmaceutico_sai",
);
upsertTestUser("teste_auditor", requiredEnv("TEST_AUDITOR_PASSWORD"), "auditor");
upsertTestUser("teste_ia", requiredEnv("TEST_IA_PASSWORD"), "ia_leitura");
upsertTestUser(
  "teste_workflow_audit",
  requiredEnv("TEST_WORKFLOW_AUDIT_PASSWORD"),
  "workflow_audit",
);

print("Views mascaradas, audit_log, roles e usuários de teste configurados.");
