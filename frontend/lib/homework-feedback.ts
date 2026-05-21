function formatScore(value: number) {
  return Number.isInteger(value) ? String(value) : value.toFixed(1).replace(".", ",");
}

export function homeworkEvaluationMessage(score: number, total: number) {
  const max = total > 0 ? total : 10;
  const normalized = max > 0 ? (score / max) * 10 : score;
  const note = `${formatScore(score)} / ${formatScore(max)}`;
  const body = normalized >= 7
    ? "Parabens pelo resultado! Continue acompanhando as correcoes e feedbacks, pois isso faz parte do seu processo de evolucao e ajuda a acelerar ainda mais seus resultados."
    : "Voce precisa reforcar os estudos e revisar com mais atencao os pontos corrigidos. Acompanhar as correcoes e feedbacks faz parte do seu processo de evolucao e vai ajudar voce a melhorar seus resultados.";

  return [
    "📚 *Avaliação de Tarefas – Mister Wiz*",
    "",
    "Olá! 👋",
    "",
    `Informamos que sua tarefa foi avaliada. Sua nota é ${note}.`,
    body,
  ].join("\n");
}
