"use client";

import { useMemo, useState } from "react";
import type { Homework, HomeworkSubmission } from "@/lib/school-modules";
import { HomeworkDeleteBtn, HomeworkEditBtn } from "@/components/homework-actions";

type Row = Record<string, unknown>;

function text(value: unknown) {
  return String(value ?? "").trim();
}

function lower(value: unknown) {
  return text(value)
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/\s+/g, " ")
    .toLowerCase();
}

function statusBadge(status: string) {
  const value = lower(status);
  if (value.includes("rascunho")) return "neutral";
  if (value.includes("encerr")) return "warning";
  return "success";
}

function studentName(row: Row) {
  return text(row.nome || row.name || row.aluno || row.login);
}

function studentClass(row: Row) {
  return text(row.turma || row.classe || row.class);
}

function list(value: unknown) {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  return text(value).split(/[,\n;]/).map((item) => item.trim()).filter(Boolean);
}

function uniqueList(items: string[]) {
  return [...new Set(items.map(text).filter(Boolean))];
}

function studentKeys(student: Row) {
  return [studentName(student), student.login, student.usuario, student.id].map(lower).filter(Boolean);
}

function bookMatches(lesson: Homework, student: Row) {
  const lessonBook = lower(lesson.livro);
  if (!lessonBook) return true;
  const studentBook = lower(student.livro || student.book || student.nivel);
  return Boolean(studentBook) && lessonBook === studentBook;
}

function targetStudents(lesson: Homework) {
  return uniqueList([
    text(lesson.aluno || lesson.target_aluno),
    ...list(lesson.alunos || lesson.alunos_especificos || lesson.target_alunos),
  ]);
}

function targetClasses(lesson: Homework) {
  return uniqueList([
    text(lesson.turma || lesson.target_turma),
    ...list(lesson.turmas || lesson.target_turmas || lesson.target_turmas_envio),
  ]).filter((item) => item && !["todas", "todos", "escola toda", "todas as turmas"].includes(lower(item)));
}

function matchesStudent(lesson: Homework, student: Row) {
  const keys = studentKeys(student);
  const turma = studentClass(student);
  const students = targetStudents(lesson);
  const classes = targetClasses(lesson);
  const rawClass = text(lesson.turma || lesson.target_turma);

  if (students.length > 0) return students.some((target) => keys.includes(lower(target)));
  return bookMatches(lesson, student) && (
    classes.length === 0 && (!rawClass || ["todas", "todos", "escola toda", "todas as turmas"].includes(lower(rawClass))) ||
    classes.some((target) => lower(target) === lower(turma))
  );
}

function questionCount(lesson: Homework) {
  return Array.isArray(lesson.questions) ? lesson.questions.length : 0;
}

function lessonTotal(lesson: Homework) {
  return (lesson.questions || []).reduce((sum, question) => sum + (Number(question.pontos) || 0), 0) || Number(lesson.peso || 0) || 10;
}

function deliveryCount(lesson: Homework, entregas: HomeworkSubmission[]) {
  const id = text(lesson.id);
  return entregas.filter((submission) => text(submission.activity_id) === id).length;
}

function questionTypeLabel(value: unknown) {
  const type = lower(value);
  if (type.includes("multipla")) return "Múltipla escolha";
  if (type.includes("verdadeiro") || type.includes("falso")) return "Verdadeiro/Falso";
  if (type.includes("upload")) return "Upload";
  return "Dissertativa";
}

function studentLabelByTarget(target: string, alunos: Row[]) {
  const normalized = lower(target);
  const found = alunos.find((aluno) => [
    aluno.id,
    aluno.login,
    aluno.usuario,
    studentName(aluno),
  ].map(lower).includes(normalized));
  if (!found) return target;
  const turma = studentClass(found);
  return `${studentName(found)}${turma ? ` - ${turma}` : ""}`;
}

function recipientStudentLabels(lesson: Homework, alunos: Row[]) {
  const students = targetStudents(lesson);
  const classes = targetClasses(lesson);
  if (students.length > 0) return students.map((student) => studentLabelByTarget(student, alunos));
  if (classes.length > 0) {
    return alunos
      .filter((aluno) => classes.some((turma) => lower(turma) === lower(studentClass(aluno))))
      .map((aluno) => `${studentName(aluno)}${studentClass(aluno) ? ` - ${studentClass(aluno)}` : ""}`);
  }
  return alunos.map((aluno) => `${studentName(aluno)}${studentClass(aluno) ? ` - ${studentClass(aluno)}` : ""}`);
}

function TargetBlock({ lesson, alunos }: { lesson: Homework; alunos: Row[] }) {
  const classes = targetClasses(lesson);
  const allClasses = classes.length === 0;
  const recipients = recipientStudentLabels(lesson, alunos);

  return (
    <div style={{ display: "grid", gap: 8 }}>
      <div>
        <div className="section-eyebrow" style={{ marginBottom: 4 }}>Turmas</div>
        <div style={{ display: "flex", gap: 6, flexWrap: "wrap" }}>
          {allClasses ? (
            <span className="badge badge-info">Todas as turmas</span>
          ) : classes.map((turma) => <span className="badge badge-info" key={turma}>{turma}</span>)}
        </div>
      </div>

      <div>
        <div className="section-eyebrow" style={{ marginBottom: 4 }}>Alunos</div>
        {recipients.length === 0 ? (
          <span className="table-name-secondary">Nenhum aluno encontrado no destino.</span>
        ) : (
          <details>
            <summary style={{ cursor: "pointer", color: "var(--blue-600)", fontWeight: 800, fontSize: "0.84rem" }}>
              {recipients.length} aluno(s) no destino
            </summary>
            <div style={{ display: "grid", gap: 3, marginTop: 6 }}>
              {recipients.slice(0, 30).map((student) => <span className="table-name-secondary" key={student}>{student}</span>)}
              {recipients.length > 30 && <span className="table-name-secondary">+ {recipients.length - 30} aluno(s)</span>}
            </div>
          </details>
        )}
      </div>
    </div>
  );
}

function HomeworkContentDetails({ licao }: { licao: Homework }) {
  return (
    <details style={{ marginTop: 10 }}>
      <summary style={{ cursor: "pointer", color: "var(--blue-600)", fontWeight: 800, fontSize: "0.86rem" }}>
        Ver conteúdo completo da tarefa
      </summary>
      <div style={{ display: "grid", gap: 10, marginTop: 10 }}>
        {(licao.questions || []).map((question, index) => (
          <div key={text(question.id) || index} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 12 }}>
            <div className="section-eyebrow">Questão {index + 1} | {questionTypeLabel(question.tipo)} | {Number(question.pontos || 0)} pts</div>
            <div style={{ fontWeight: 800, marginTop: 5, color: "var(--text-primary)" }}>{text(question.enunciado)}</div>
            {Array.isArray(question.opcoes) && question.opcoes.length > 0 && (
              <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
                {question.opcoes.map((opcao, optionIndex) => (
                  <span key={`${text(question.id)}_${optionIndex}`} className="table-name-secondary">
                    {String.fromCharCode(65 + optionIndex)}) {opcao}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {questionCount(licao) === 0 && <span className="table-name-secondary">Sem questões estruturadas cadastradas.</span>}
      </div>
    </details>
  );
}

export function HomeworkStudentLessonsClient({
  licoes,
  entregas,
  alunos,
  turmaNames
}: {
  licoes: Homework[];
  entregas: HomeworkSubmission[];
  alunos: Row[];
  turmaNames: string[];
}) {
  const [open, setOpen] = useState(false);
  const [studentKey, setStudentKey] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [search, setSearch] = useState("");
  const selectedStudent = alunos.find((student, index) => text(student.id || student.login || index) === studentKey);
  const visibleLessons = useMemo(() => {
    if (!selectedStudent) return [];
    return licoes.filter((lesson) => matchesStudent(lesson, selectedStudent));
  }, [licoes, selectedStudent]);
  const filteredLessons = useMemo(() => {
    const query = lower(search);
    if (!query) return licoes;
    return licoes.filter((licao) => [
      licao.titulo,
      licao.disciplina,
      licao.livro,
      licao.turma,
      licao.status,
      licao.descricao,
      ...targetClasses(licao),
      ...targetStudents(licao),
    ].some((value) => lower(value).includes(query)));
  }, [licoes, search]);
  const listedLessons = showAll ? filteredLessons : filteredLessons.slice(0, 8);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Gestão completa</div>
            <h3 className="section-title">Todas as lições lançadas</h3>
            <p className="section-subtitle">ADM e coordenação veem título, conteúdo, destinatários e podem editar ou excluir.</p>
          </div>
          <span className="badge badge-info">{licoes.length} lição(ões)</span>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", justifyContent: "space-between", flexWrap: "wrap", marginBottom: 12 }}>
            <input
              className="form-input"
              value={search}
              onChange={(event) => { setSearch(event.target.value); setShowAll(false); }}
              placeholder="Buscar por título, turma, livro, aluno ou status..."
              style={{ maxWidth: 440 }}
            />
            <span className="table-name-secondary">Mostrando {listedLessons.length} de {filteredLessons.length} lições</span>
          </div>

          <div style={{ display: "grid", gap: 12 }}>
            {listedLessons.map((licao) => (
              <article className="card" key={text(licao.id || licao.titulo)} style={{ boxShadow: "none" }}>
                <div className="card-body" style={{ padding: 14 }}>
                  <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(230px, 1fr))", gap: 16, alignItems: "start" }}>
                    <div className="table-name-cell">
                      <span className="table-name-primary">{text(licao.titulo || "Lição de casa")}</span>
                      <span className="table-name-secondary">{text(licao.disciplina || "Geral")} | Livro: {text(licao.livro || "-")} | Prazo: {text(licao.due_date || "-")}</span>
                      {text(licao.descricao) && (
                        <span className="table-name-secondary">
                          {text(licao.descricao).slice(0, 130)}{text(licao.descricao).length > 130 ? "..." : ""}
                        </span>
                      )}
                      <HomeworkContentDetails licao={licao} />
                    </div>

                    <TargetBlock lesson={licao} alunos={alunos} />

                    <div style={{ display: "grid", gap: 8, justifyItems: "start" }}>
                      <span className={`badge badge-${statusBadge(text(licao.status || "Ativa"))}`}><span className="badge-dot" />{text(licao.status || "Ativa")}</span>
                      <span className="badge badge-gold">{questionCount(licao)} questão(ões) | {lessonTotal(licao)} pts</span>
                      <span className="table-name-secondary">{deliveryCount(licao, entregas)} entrega(s)</span>
                      <div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}>
                        <HomeworkEditBtn licao={licao} turmas={turmaNames} alunos={alunos} />
                        <HomeworkDeleteBtn licao={licao} />
                      </div>
                    </div>
                  </div>
                </div>
              </article>
            ))}
          </div>

          {filteredLessons.length > listedLessons.length && (
            <div style={{ display: "flex", justifyContent: "center", marginTop: 14 }}>
              <button className="btn btn-secondary" type="button" onClick={() => setShowAll(true)}>
                Mostrar todas as {filteredLessons.length} lições
              </button>
            </div>
          )}
        </div>
      </div>

      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Lições por aluno</div>
            <h3 className="section-title">Consultar lições lançadas</h3>
            <p className="section-subtitle">A lista completa fica recolhida. Selecione um aluno para ver somente as lições dele.</p>
          </div>
          <button className="btn btn-secondary" type="button" onClick={() => setOpen((value) => !value)}>
            {open ? "Ocultar consulta" : "Selecionar aluno e ver lições"}
          </button>
        </div>
        {open && (
          <div className="card-body">
            <div className="form-group" style={{ maxWidth: 420, marginBottom: 14 }}>
              <label className="form-label">Aluno</label>
              <select className="form-input" value={studentKey} onChange={(event) => setStudentKey(event.target.value)}>
                <option value="">Selecione um aluno</option>
                {alunos.map((student, index) => {
                  const key = text(student.id || student.login || index);
                  return <option key={key} value={key}>{studentName(student)}{studentClass(student) ? ` - ${studentClass(student)}` : ""}</option>;
                })}
              </select>
            </div>
            {!selectedStudent ? (
              <div className="empty-state"><div className="empty-title">Selecione um aluno</div><p className="empty-desc">As lições lançadas para ele aparecem aqui.</p></div>
            ) : visibleLessons.length === 0 ? (
              <div className="empty-state"><div className="empty-title">Nenhuma lição encontrada</div><p className="empty-desc">Não há lições direcionadas para este aluno ou turma.</p></div>
            ) : (
              <table className="data-table">
                <thead><tr><th>Lição</th><th>Destino</th><th>Prazo</th><th>Status</th><th>Entrega</th><th>Ações</th></tr></thead>
                <tbody>
                  {visibleLessons.map((licao) => {
                    const delivery = entregas.find((submission) =>
                      text(submission.activity_id) === text(licao.id) &&
                      (lower(submission.aluno) === lower(studentName(selectedStudent)) || lower(submission.aluno_login) === lower(text(selectedStudent.login || selectedStudent.usuario)))
                    );
                    return (
                      <tr key={text(licao.id)}>
                        <td><div className="table-name-cell"><span className="table-name-primary">{text(licao.titulo)}</span><span className="table-name-secondary">{(licao.questions || []).length} questões</span></div></td>
                        <td><TargetBlock lesson={licao} alunos={[selectedStudent]} /></td>
                        <td>{text(licao.due_date || "-")}</td>
                        <td><span className={`badge badge-${statusBadge(text(licao.status || "Ativa"))}`}><span className="badge-dot" />{text(licao.status || "Ativa")}</span></td>
                        <td>{delivery ? <span className={`badge badge-${lower(delivery.status).includes("corrigido") ? "success" : "warning"}`}><span className="badge-dot" />{text(delivery.status || "Enviada")}</span> : <span className="badge badge-neutral">Aguardando resposta</span>}</td>
                        <td><div style={{ display: "flex", gap: 4 }}><HomeworkEditBtn licao={licao} turmas={turmaNames} alunos={alunos} /><HomeworkDeleteBtn licao={licao} /></div></td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
