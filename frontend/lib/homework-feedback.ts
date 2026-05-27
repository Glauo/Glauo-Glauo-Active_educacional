import { polishPortugueseText } from "./portuguese-text";

function formatScore(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(".", ",");
}

export function homeworkEvaluationMessage(score: number, total: number) {
  const max = total > 0 ? total : 10;
  const normalized = max > 0 ? (score / max) * 10 : score;
  const note = `${formatScore(score)} / ${formatScore(max)}`;
  const body = normalized >= 7
    ? "Parabéns pelo resultado! Continue acompanhando as correções e feedbacks, pois isso faz parte do seu processo de evolução e ajuda a acelerar ainda mais seus resultados."
    : "Você precisa reforçar os estudos e revisar com mais atenção os pontos corrigidos. Acompanhar as correções e feedbacks faz parte do seu processo de evolução e vai ajudar você a melhorar seus resultados.";

  return polishPortugueseText([
    "📚 *Avaliação de Tarefas - Mister Wiz*",
    "",
    "Olá! 👋",
    "",
    `Informamos que sua tarefa foi avaliada. Sua nota é ${note}.`,
    body,
  ].join("\n"));
}
