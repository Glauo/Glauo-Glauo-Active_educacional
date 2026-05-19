import { normalizeList, text, type Homework, type HomeworkSubmission, type Row } from "./school-modules";
import { applyWorkbookAnswerKey } from "./workbook-answer-key";
import { WORKBOOK_LESSON_CONTENT, WORKBOOK_LESSON_QUESTIONS } from "./workbook-content";

type WorkbookPart = {
  book: "1" | "2" | "3";
  title: string;
  url: string;
  firstLesson: number;
  lastLesson: number;
  firstPage: number;
  lastPage: number;
};

const WORKBOOK_PARTS: WorkbookPart[] = [
  { book: "1", title: "Workbook 1 - Parte 1", url: "/uploads/workbooks/workbook-1-parte-1.pdf", firstLesson: 1, lastLesson: 14, firstPage: 5, lastPage: 58 },
  { book: "1", title: "Workbook 1 - Parte 2", url: "/uploads/workbooks/workbook-1-parte-2.pdf", firstLesson: 15, lastLesson: 28, firstPage: 3, lastPage: 59 },
  { book: "2", title: "Workbook 2 - Parte 1", url: "/uploads/workbooks/workbook-2-parte-1.pdf", firstLesson: 31, lastLesson: 45, firstPage: 4, lastPage: 62 },
  { book: "2", title: "Workbook 2 - Parte 2", url: "/uploads/workbooks/workbook-2-parte-2.pdf", firstLesson: 46, lastLesson: 60, firstPage: 2, lastPage: 62 },
  { book: "3", title: "Workbook 3", url: "/uploads/workbooks/workbook-3.pdf", firstLesson: 61, lastLesson: 90, firstPage: 4, lastPage: 124 },
];

function normalizeBook(value: unknown) {
  const raw = text(value).toLowerCase().replace(",", ".");
  const match = raw.match(/\b([123])(?:\.|$|\s)/) || raw.match(/livro\s*([123])/i) || raw.match(/book\s*([123])/i);
  return match?.[1] as "1" | "2" | "3" | undefined;
}

function pageRange(part: WorkbookPart, lesson: number) {
  const start = part.firstPage + ((lesson - part.firstLesson) * 4);
  const nextStart = start + 4;
  return { start, end: Math.min(nextStart - 1, part.lastPage) };
}

export function studentWorkbookBook(student?: Row | null, unit?: unknown) {
  return normalizeBook(student?.livro || student?.book || student?.nivel || unit);
}

export function workbookLessonsForBook(book?: string): Homework[] {
  if (book !== "1" && book !== "2" && book !== "3") return [];
  return WORKBOOK_PARTS
    .filter((part) => part.book === book)
    .flatMap((part) => Array.from({ length: part.lastLesson - part.firstLesson + 1 }, (_, index) => {
      const lesson = part.firstLesson + index;
      const pages = pageRange(part, lesson);
      const id = `workbook-book-${book}-lesson-${String(lesson).padStart(3, "0")}`;
      const exactContent = WORKBOOK_LESSON_CONTENT[book]?.[lesson] || "";
      const exactQuestions = (WORKBOOK_LESSON_QUESTIONS[book]?.[lesson] || []).map((question, questionIndex) => ({
        id: `${id}_${question.idSuffix || `q${questionIndex + 1}`}`,
        tipo: "multipla_escolha" as const,
        enunciado: question.section ? `${question.section}\n${question.question}` : question.question,
        opcoes: question.options,
        correta_idx: null,
        pontos: 1,
      }));
      const fallbackQuestion = {
        id: `${id}_resposta`,
        tipo: "upload" as const,
        enunciado: `Abra o PDF ${part.title}, faca a licao ${lesson} nas paginas ${pages.start} a ${pages.end} e envie aqui sua resposta, foto ou link do arquivo.`,
        pontos: 10,
      };
      return applyWorkbookAnswerKey({
        id,
        tipo: "Licao de Casa",
        origem: "workbook_pdf",
        titulo: `Workbook ${book} - Licao ${lesson}`,
        descricao: exactContent || `Faca a licao ${lesson} no ${part.title}, paginas ${pages.start} a ${pages.end}. Envie sua resposta ou anexe o comprovante conforme orientacao do professor.`,
        disciplina: "Ingles",
        turma: "Todas",
        livro: `Livro ${book}`,
        status: "Ativa",
        autor: "Active Educacional",
        sequencia: lesson,
        material_titulo: part.title,
        material_url: part.url,
        material_page_start: pages.start,
        material_page_end: pages.end,
        allow_resubmission: false,
        questions: exactQuestions.length > 0 ? exactQuestions : [fallbackQuestion],
        peso: exactQuestions.length > 0 ? exactQuestions.length : 10,
      } satisfies Homework);
    }));
}

export function workbookLibraryBooks() {
  return WORKBOOK_PARTS.map((part) => ({
    id: `workbook-book-${part.book}-part-${part.firstLesson}`,
    titulo: part.title,
    autor: "Mister Wiz",
    nivel: `Livro ${part.book}`,
    categoria: "Workbook",
    tipo: "Workbook PDF",
    turma: "Todas",
    url: part.url,
    pdf_nome: `${part.title}.pdf`,
    status: "Ativo",
    origem: "workbook_pdf",
  }));
}

export function getWorkbookHomeworkById(id: unknown) {
  const wanted = text(id);
  for (const book of ["1", "2", "3"] as const) {
    const homework = workbookLessonsForBook(book).find((item) => text(item.id) === wanted);
    if (homework) return homework;
  }
  return null;
}

export function hasWorkbookStudentTarget(homework: Row) {
  return Boolean(
    text(homework.aluno || homework.aluno_nome || homework.target_aluno) ||
    normalizeList(homework.alunos || homework.alunos_especificos).length > 0
  );
}

export function releasedWorkbookLessons(lessons: Homework[], submissions: HomeworkSubmission[]) {
  const submitted = new Set(submissions.map((submission) => text(submission.activity_id)).filter(Boolean));
  const ordered = [...lessons].sort((a, b) => Number(a.sequencia || 0) - Number(b.sequencia || 0));
  const firstPendingIndex = ordered.findIndex((lesson) => !submitted.has(text(lesson.id)));
  if (firstPendingIndex === -1) return ordered;
  return ordered.slice(0, firstPendingIndex + 1);
}
