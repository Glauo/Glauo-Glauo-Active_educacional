import { NextRequest, NextResponse } from "next/server";
import { getSession } from "@/lib/auth";

function text(value: unknown) {
  return String(value || "").trim();
}

function isEnglishQuestion(value: string) {
  const q = value.toLowerCase();
  const allowed = [
    "ingl", "english", "grammar", "gramática", "gramatica", "vocabulary", "vocabul",
    "tradu", "translate", "pronunciation", "pronúncia", "pronuncia", "verb", "verbo",
    "past", "present", "future", "simple", "continuous", "perfect", "phrase", "frase",
    "word", "palavra", "sentence", "preposition", "preposição", "preposicao", "adjective",
    "adjetivo", "adverb", "advérbio", "adverbio", "plural", "singular", "question",
  ];
  return allowed.some((item) => q.includes(item));
}

function answerEnglish(question: string) {
  const q = question.toLowerCase();
  if (q.includes("present perfect")) {
    return "Present perfect liga uma ação passada ao presente. Estrutura: have/has + particípio. Exemplo: I have studied English for two years. Use para experiências, resultados atuais e ações que começaram no passado e continuam.";
  }
  if (q.includes("simple past") || q.includes("passado simples")) {
    return "Simple past fala de ações terminadas no passado. Use verbo regular com -ed ou verbo irregular. Exemplo: I studied yesterday. / She went to school.";
  }
  if (q.includes("tradu") || q.includes("translate")) {
    return "Posso ajudar com tradução de palavras e frases de inglês. Envie a frase completa e, se possível, o contexto para eu explicar o sentido, não apenas traduzir palavra por palavra.";
  }
  if (q.includes("pron")) {
    return "Para pronúncia em inglês, separe a palavra em sons e pratique com frases curtas. Envie a palavra específica que eu explico a pronúncia aproximada em português e um exemplo de uso.";
  }
  if (q.includes("verb") || q.includes("verbo")) {
    return "Em inglês, o verbo muda conforme tempo verbal e sujeito. Para estudar bem: identifique o tempo, monte a estrutura e pratique com frases afirmativas, negativas e perguntas.";
  }
  if (q.includes("vocab") || q.includes("palavra") || q.includes("word")) {
    return "Para vocabulário, aprenda a palavra junto com uma frase. Exemplo: 'book' significa livro. Frase: I read a book every night. Envie a palavra que você quer estudar.";
  }
  return "Posso ajudar com inglês. Reformule sua dúvida com o tópico específico: gramática, vocabulário, tradução, pronúncia, verbo ou frase. Exemplo: 'Explique o simple past com 3 exemplos'.";
}

export async function POST(req: NextRequest) {
  const session = await getSession();
  if (!session || !session.perfil.toLowerCase().includes("aluno")) {
    return NextResponse.json({ error: "Nao autorizado" }, { status: 401 });
  }
  const body = await req.json().catch(() => ({}));
  const pergunta = text(body.pergunta || body.prompt);
  if (!pergunta) return NextResponse.json({ error: "Digite uma pergunta de ingles." }, { status: 400 });
  if (!isEnglishQuestion(pergunta)) {
    return NextResponse.json({
      error: "A Wiz do aluno é bloqueada para pesquisar apenas assuntos de inglês. Pergunte sobre gramática, vocabulário, tradução, pronúncia ou frases em inglês.",
    }, { status: 400 });
  }
  return NextResponse.json({ ok: true, resposta: answerEnglish(pergunta) });
}
