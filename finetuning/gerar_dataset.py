"""Gera o dataset sintético do experimento de fine-tuning.

Tarefa: a partir de um texto livre de solicitação de LME, extrair o
medicamento e a quantidade e devolver um JSON no formato:

    {"medicamento": "...", "quantidade": 0}

O dataset é fictício e reprodutível (semente fixa). São 300 exemplos:
270 para treino (``train.jsonl``) e 30 para teste (``test.jsonl``), com
5 exemplos de teste por medicamento.
"""

import json
import random
from collections import Counter
from pathlib import Path

SEED = 42
TOTAL = 300
TESTE = 30

MEDICAMENTOS = [
    "Adalimumabe 40mg",
    "Etanercepte 50mg",
    "Sirolimo 1mg",
    "Imatinibe 400mg",
    "Rituximabe 500mg",
    "Olanzapina 10mg",
]
QUANTIDADES = [30, 60, 90]
# Unidade coerente com a forma farmacêutica de cada medicamento fictício.
UNIDADES_POR_MEDICAMENTO = {
    "Adalimumabe 40mg": ["canetas", "frascos"],
    "Etanercepte 50mg": ["canetas", "frascos"],
    "Sirolimo 1mg": ["comprimidos"],
    "Imatinibe 400mg": ["comprimidos"],
    "Rituximabe 500mg": ["frascos", "ampolas"],
    "Olanzapina 10mg": ["comprimidos"],
}
CIDADES = ["Santo Antônio de Jesus", "Amargosa", "Nazaré", "Cruz das Almas"]
STATUS = ["ATIVA", "VENCIDA", "PENDENTE", "CANCELADA"]
NOMES = [
    "Ana Souza",
    "Bruno Lima",
    "Carla Mendes",
    "Diego Alves",
    "Elisa Rocha",
    "Felipe Santos",
    "Gabriela Nunes",
    "Henrique Dias",
]

INSTRUCAO = (
    "Extraia o medicamento e a quantidade da solicitação de LME. "
    'Responda somente com JSON no formato {"medicamento": "...", "quantidade": 0}.'
)

# Cada template usa os mesmos campos, mas muda a redação e a ordem da
# informação. O modelo precisa aprender a extrair, não a decorar um formato.
TEMPLATES = [
    "Paciente {nome}, da cidade de {cidade}, com LME {status}, solicita "
    "{quantidade} {unidade} de {medicamento}.",
    "Renovação de LME: {medicamento}, {quantidade} {unidade}, para o "
    "paciente {nome} ({cidade}).",
    "Solicito {quantidade} {unidade} do medicamento {medicamento} para "
    "seguir o tratamento do paciente {nome}.",
    "LME {status} do paciente {nome}. Medicamento: {medicamento}. "
    "Quantidade solicitada: {quantidade} {unidade}.",
    "Processo {processo} - {cidade}\nPaciente: {nome}\nMedicamento: "
    "{medicamento}\nQuantidade: {quantidade} {unidade}\nStatus: {status}",
    "Para o paciente {nome}, residente em {cidade}, prescrevo "
    "{medicamento} na quantidade de {quantidade} {unidade}.",
    "A solicitação de {nome} refere-se a {quantidade} {unidade} de "
    "{medicamento}; a LME está {status}.",
    "Medicamento solicitado: {medicamento}; quantidade: {quantidade} "
    "{unidade}; paciente: {nome}; cidade: {cidade}; CID: {cid}.",
    "{nome} precisa de {quantidade} {unidade} de {medicamento} para "
    "renovar a LME ({status}) em {cidade}.",
    "Encaminhamento para {cidade}: paciente {nome}, {quantidade} {unidade} "
    "de {medicamento}, processo {processo}.",
    "LME nº {processo}. Cidade: {cidade}. Status: {status}. Item: "
    "{medicamento}. Quantidade: {quantidade} {unidade}. Paciente: {nome}.",
    "Solicitação médica para {nome}: usar {medicamento}, {quantidade} "
    "{unidade}, conforme LME {status}.",
    "Paciente {nome} deu entrada com pedido de {quantidade} {unidade} de "
    "{medicamento}; cidade de atendimento: {cidade}.",
    "Consta na LME {status} de {nome}: {medicamento} - {quantidade} "
    "{unidade}. CID {cid}. Processo {processo}.",
    "Para renovação em {cidade}, o paciente {nome} aguarda {quantidade} "
    "{unidade} de {medicamento}.",
    "Medicamento: {medicamento} | Quantidade: {quantidade} {unidade} | "
    "Paciente: {nome} | Cidade: {cidade} | Status: {status}",
    "A LME do paciente {nome} foi aberta em {cidade} para {medicamento}, "
    "com {quantidade} {unidade}.",
    "Solicitação: {medicamento}. Quantidade: {quantidade} {unidade}. "
    "Paciente: {nome}. Cidade: {cidade}. Processo: {processo}.",
    "Paciente {nome} ({cidade}) tem LME {status} para {medicamento} e "
    "requer {quantidade} {unidade}.",
    "Segue pedido de {quantidade} {unidade} de {medicamento} referente ao "
    "paciente {nome}, processo {processo}, cidade {cidade}.",
]


def exemplo(rng, medicamento, quantidade):
    """Monta um exemplo com um medicamento/quantidade fixos e texto variado."""
    valores = {
        "nome": rng.choice(NOMES),
        "cidade": rng.choice(CIDADES),
        "status": rng.choice(STATUS),
        "medicamento": medicamento,
        "quantidade": quantidade,
        "unidade": rng.choice(UNIDADES_POR_MEDICAMENTO[medicamento]),
        "processo": f"{rng.randint(1000, 9999)}/{rng.randint(2024, 2026)}",
        "cid": f"M{rng.randint(10, 99)}.{rng.randint(0, 9)}",
    }
    texto = rng.choice(TEMPLATES).format(**valores)
    resposta = json.dumps(
        {"medicamento": medicamento, "quantidade": quantidade},
        ensure_ascii=False,
    )
    return {
        "instruction": INSTRUCAO,
        "input": texto,
        "output": resposta,
    }


def gerar():
    rng = random.Random(SEED)
    vistos = set()
    exemplos = []

    # Distribui os exemplos igualmente entre os medicamentos e garante que
    # cada texto seja único.
    while len(exemplos) < TOTAL:
        medicamento = MEDICAMENTOS[len(exemplos) % len(MEDICAMENTOS)]
        quantidade = rng.choice(QUANTIDADES)
        item = exemplo(rng, medicamento, quantidade)
        if item["input"] in vistos:
            continue
        vistos.add(item["input"])
        exemplos.append(item)

    rng.shuffle(exemplos)

    # Teste estratificado: 5 exemplos por medicamento (30 no total).
    teste = []
    for medicamento in MEDICAMENTOS:
        do_medicamento = [e for e in exemplos if medicamento in e["input"]]
        teste.extend(do_medicamento[:5])
    ids_teste = {id(item) for item in teste}
    treino = [item for item in exemplos if id(item) not in ids_teste]

    assert len(treino) == TOTAL - TESTE, len(treino)
    assert len(teste) == TESTE, len(teste)
    return treino, teste


def salvar(caminho, itens):
    with Path(caminho).open("w", encoding="utf-8", newline="\n") as arquivo:
        for item in itens:
            arquivo.write(json.dumps(item, ensure_ascii=False) + "\n")


def main():
    treino, teste = gerar()
    pasta = Path(__file__).resolve().parent
    salvar(pasta / "train.jsonl", treino)
    salvar(pasta / "test.jsonl", teste)

    print(f"Total: {len(treino) + len(teste)}")
    print(f"Treino: {len(treino)}")
    print(f"Teste: {len(teste)}")
    print("Teste por medicamento:")
    contagem = Counter(
        next(m for m in MEDICAMENTOS if m in item["input"]) for item in teste
    )
    for medicamento, total in sorted(contagem.items()):
        print(f"  {medicamento}: {total}")
    print("\nExemplo de treino:")
    print(json.dumps(treino[0], ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
