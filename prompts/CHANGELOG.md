# Histórico de prompts

Os prompts valem apenas para dados fictícios deste protótipo. Eles reduzem o
risco de resposta inventada, mas não substituem as permissões do MongoDB nem a
validação de cidade/perfil.

## v1

- Usa somente o contexto recuperado de `docs/regras_lme/` e os dados da consulta
  autorizada.
- Não inventa dados nem completa lacunas por suposição.
- Declara quando a informação não foi encontrada.
- Identifica as regras como material fictício de demonstração.

## v2

- **Permissão explícita:** recusa quando o backend não confirmar a autorização
  para o perfil e a cidade solicitados.
  *Por quê:* a v1 não deixava claro que uma pergunta do usuário não é uma
  permissão. O modelo podia tratar “quero ver todas as cidades” como autorizado.
- **Uso restrito ao contexto recuperado:** mantém a regra da v1, mas a torna
  explícita também para os registros consultados, proibindo conhecimento
  externo e inferência de fatos.
  *Por quê:* evitar respostas clínicas ou administrativas que não estejam nos
  documentos fictícios ou nos dados retornados.
- **Proteção de dados:** nunca revela CPF completo; quando houver CPF, apresenta
  apenas `***.***.***-NN` ou omite o campo.
  *Por quê:* a v1 não tratava privacidade; o modelo poderia repetir um CPF que
  aparecesse em um contexto mal formado.
- **Resposta previsível:** fixa o formato `Resultado`, `Fonte` e `Observação`.
  *Por quê:* facilita a revisão, o teste de recusa e a comparação entre
  execuções.
- **Limites e incerteza:** define a frase “Não informado nas fontes/dados
  consultados.” e reforça que as regras são fictícias.
  *Por quê:* impedir que ausência de dado vire conclusão ou orientação.
