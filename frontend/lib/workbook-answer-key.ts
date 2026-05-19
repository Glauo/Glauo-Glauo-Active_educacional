import { text, type Homework, type HomeworkQuestion } from "./school-modules";

const WORKBOOK_1_ANSWERS: Record<number, "A" | "B" | "C" | "D"> = {
  1: "B", 2: "B", 3: "A", 4: "C", 5: "C", 6: "C", 7: "C", 8: "C", 9: "B", 10: "B",
  11: "C", 12: "B", 13: "C", 14: "C", 15: "B", 16: "B", 17: "D", 18: "C", 19: "A", 20: "A",
  21: "C", 22: "C", 23: "C", 24: "C", 25: "B", 26: "B", 27: "D", 28: "A", 29: "B", 30: "C",
  31: "D", 32: "B", 33: "C", 34: "B", 35: "B", 36: "C", 37: "B", 38: "A", 39: "B", 40: "C",
  41: "B", 42: "B", 43: "B", 44: "C", 45: "B", 46: "C", 47: "C", 48: "A", 49: "A", 50: "C",
  51: "B", 52: "C", 53: "A", 54: "C", 55: "A", 56: "B", 57: "C", 58: "B", 59: "C", 60: "A",
  61: "C", 62: "C", 63: "B", 64: "C", 65: "A", 66: "A", 67: "B", 68: "D", 69: "C", 70: "C",
  71: "C", 72: "A", 73: "C", 74: "C", 75: "B", 76: "C", 77: "C", 78: "B", 79: "B", 80: "A",
  81: "A", 82: "C", 83: "B", 84: "B", 85: "A", 86: "B", 87: "C", 88: "C", 89: "B", 90: "A",
  91: "B", 92: "B", 93: "C", 94: "C", 95: "B", 96: "C", 97: "B", 98: "B", 99: "B", 100: "B",
  101: "C", 102: "B", 103: "B", 104: "D", 105: "C", 106: "B", 107: "D", 108: "C", 109: "A", 110: "B",
  111: "B", 112: "D", 113: "B", 114: "B", 115: "C", 116: "C", 117: "B", 118: "C", 119: "B", 120: "B",
  121: "B", 122: "C", 123: "C", 124: "C", 125: "C", 126: "B", 127: "A", 128: "B", 129: "B", 130: "B",
  131: "C", 132: "B", 133: "C", 134: "B", 135: "B", 136: "D", 137: "B", 138: "C", 139: "B", 140: "C",
};

function letterToIndex(letter: string) {
  const upper = letter.trim().toUpperCase();
  if (upper === "A") return 0;
  if (upper === "B") return 1;
  if (upper === "C") return 2;
  if (upper === "D") return 3;
  return null;
}

function questionNumber(question: HomeworkQuestion) {
  const match = text(question.id).match(/(?:^|_)q(\d+)$/i) || text((question as { idSuffix?: unknown }).idSuffix).match(/^q(\d+)$/i);
  return match ? Number(match[1]) : null;
}

export function workbookAnswerLetter(book: unknown, question: HomeworkQuestion) {
  if (text(book) !== "1") return "";
  const number = questionNumber(question);
  return number ? WORKBOOK_1_ANSWERS[number] || "" : "";
}

export function applyWorkbookAnswerKey(homework: Homework): Homework {
  const bookMatch = text(homework.livro).match(/(?:livro|book)?\s*([123])/i);
  const book = bookMatch?.[1] || "";
  if (book !== "1" || !Array.isArray(homework.questions)) return homework;

  return {
    ...homework,
    questions: homework.questions.map((question) => {
      const letter = workbookAnswerLetter(book, question);
      const idx = letterToIndex(letter);
      if (idx === null || !Array.isArray(question.opcoes) || idx >= question.opcoes.length) return question;
      return {
        ...question,
        tipo: "multipla_escolha",
        correta_idx: idx,
        correta_texto: question.opcoes[idx],
        feedback: text(question.feedback) || `Gabarito oficial Workbook 1: alternativa ${letter}.`,
      };
    }),
  };
}

export function hasFullAutoCorrection(homework: Homework) {
  const questions = Array.isArray(homework.questions) ? homework.questions : [];
  return questions.length > 0 && questions.every((question) => (
    question.tipo === "multipla_escolha" &&
    question.correta_idx !== null &&
    question.correta_idx !== undefined
  ) || (
    question.tipo === "verdadeiro_falso" &&
    Boolean(text(question.correta_texto))
  ));
}

