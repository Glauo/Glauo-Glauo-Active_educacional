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

function list(value: unknown) {
  if (Array.isArray(value)) return value.map(text).filter(Boolean);
  return text(value).split(/[,\n;]/).map((item) => item.trim()).filter(Boolean);
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

function matchesStudent(lesson: Homework, student: Row) {
  const keys = studentKeys(student);
  const turma = text(student.turma || student.classe);
  const targetStudent = text(lesson.aluno || lesson.target_aluno);
  const targetStudents = list(lesson.alunos || lesson.alunos_especificos || lesson.target_alunos);
  const targetClass = text(lesson.turma || lesson.target_turma);
  const targetClasses = [targetClass, ...list(lesson.turmas || lesson.target_turmas || lesson.target_turmas_envio)].filter(Boolean);
  if (targetStudent) return keys.includes(lower(targetStudent));
  if (targetStudents.length > 0) return targetStudents.some((target) => keys.includes(lower(target)));
  return bookMatches(lesson, student) &&
    (targetClasses.length === 0 || targetClasses.some((target) => ["todas", "todos", "escola toda", "todas as turmas"].includes(lower(target)) || lower(target) === lower(turma)));
}

function questionCount(lesson: Homework) {
  return Array.isArray(lesson.questions) ? lesson.questions.length : 0;
}


function TargetCell({ lesson }: { lesson: Homework }) {
  const students = [text(lesson.aluno), ...list(lesson.alunos)].filter(Boolean);
  const classes = [text(lesson.turma), ...list(lesson.turmas)].filter(
    (item) => item && !["todas", "todos"].includes(lower(item))
  );

  if (students.length === 0 && classes.length === 0) {
    return <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>Todas as turmas</span>;
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 3 }}>
      {classes.length > 0 && (
        <span style={{ fontSize: "0.78rem", fontWeight: 700, color: "var(--blue-600)" }}>
          {classes.join(", ")}
        </span>
      )}
      {students.length > 0 && (
        students.length <= 3 ? (
          <span style={{ fontSize: "0.8rem" }}>{students.join(", ")}</span>
        ) : (
          <details>
            <summary style={{ cursor: "pointer", fontSize: "0.8rem", color: "var(--blue-600)", fontWeight: 600 }}>
              {students.length} aluno(s) — ver nomes
            </summary>
            <div style={{ marginTop: 4, display: "flex", flexDirection: "column", gap: 2, paddingLeft: 4 }}>
              {students.map((name, i) => (
                <span key={i} style={{ fontSize: "0.78rem", color: "var(--text-secondary)" }}>{name}</span>
              ))}
            </div>
          </details>
        )
      )}
    </div>
  );
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
  if (type.includes("multipla")) return "Multipla escolha";
  if (type.includes("verdadeiro") || type.includes("falso")) return "Verdadeiro/Falso";
  if (type.includes("upload")) return "Upload";
  return "Dissertativa";
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
  const selectedStudent = alunos.find((student, index) => (text(student.id || student.login || index) === studentKey));
  const visibleLessons = useMemo(() => {
    if (!selectedStudent) return [];
    return licoes.filter((lesson) => matchesStudent(lesson, selectedStudent));
  }, [licoes, selectedStudent]);

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
      <div className="card">
        <div className="card-header">
          <div>
            <div className="section-eyebrow">Gestao completa</div>
            <h3 className="section-title">Todas as licoes lancadas</h3>
            <p className="section-subtitle">ADM e coordenacao veem titulo, conteudo, destinatarios e podem editar ou excluir.</p>
          </div>
          <span className="badge badge-info">{licoes.length} licao(oes)</span>
        </div>
        <div className="card-body" style={{ paddingTop: 12 }}>
          <table className="data-table">
            <thead>
              <tr>
                <th>Licao</th>
                <th>Destino</th>
                <th>Questoes</th>
                <th>Entregas</th>
                <th>Status</th>
                <th>Acoes</th>
              </tr>
            </thead>
            <tbody>
              {licoes.map((licao) => (
                <tr key={text(licao.id || licao.titulo)}>
                  <td>
                    <div className="table-name-cell">
                      <span className="table-name-primary">{text(licao.titulo || "Licao de casa")}</span>
                      <span className="table-name-secondary">{text(licao.disciplina || "Geral")} | Livro: {text(licao.livro || "-")} | Prazo: {text(licao.due_date || "-")}</span>
                      {text(licao.descricao) && <span className="table-name-secondary">{text(licao.descricao).slice(0, 100)}{text(licao.descricao).length > 100 ? "..." : ""}</span>}
                      <details style={{ marginTop: 8 }}>
                        <summary style={{ cursor: "pointer", color: "var(--blue-600)", fontWeight: 700, fontSize: "0.8rem" }}>Ver conteudo da tarefa</summary>
                        <div style={{ display: "grid", gap: 8, marginTop: 8 }}>
                          {(licao.questions || []).map((question, index) => (
                            <div key={text(question.id) || index} style={{ border: "1px solid var(--border)", borderRadius: 8, padding: 10 }}>
                              <div className="section-eyebrow">Questao {index + 1} | {questionTypeLabel(question.tipo)} | {Number(question.pontos || 0)} pts</div>
                              <div style={{ fontWeight: 700, marginTop: 4 }}>{text(question.enunciado)}</div>
                              {Array.isArray(question.opcoes) && question.opcoes.length > 0 && (
                                <div style={{ display: "grid", gap: 4, marginTop: 8 }}>
                                  {question.opcoes.map((opcao, optionIndex) => <span key={`${text(question.id)}_${optionIndex}`} className="table-name-secondary">{String.fromCharCode(65 + optionIndex)}) {opcao}</span>)}
                                </div>
                              )}
                            </div>
                          ))}
                          {questionCount(licao) === 0 && <span className="table-name-secondary">Sem questoes estruturadas cadastradas.</span>}
                        </div>
                      </details>
                    </div>
                  </td>
                  <td><TargetCell lesson={licao} /></td>
                  <td><span className="badge badge-gold">{questionCount(licao)} | {lessonTotal(licao)} pts</span></td>
                  <td>{deliveryCount(licao, entregas)}</td>
                  <td><span className={`badge badge-${statusBadge(text(licao.status || "Ativa"))}`}><span className="badge-dot" />{text(licao.status || "Ativa")}</span></td>
                  <td><div style={{ display: "flex", gap: 4, flexWrap: "wrap" }}><HomeworkEditBtn licao={licao} turmas={turmaNames} alunos={alunos} /><HomeworkDeleteBtn licao={licao} /></div></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      <div className="card">
      <div className="card-header">
        <div>
          <div className="section-eyebrow">Licoes por aluno</div>
          <h3 className="section-title">Consultar licoes lancadas</h3>
          <p className="section-subtitle">A lista completa fica recolhida. Selecione um aluno para ver somente as licoes dele.</p>
        </div>
        <button className="btn btn-secondary" type="button" onClick={() => setOpen((value) => !value)}>
          {open ? "Ocultar consulta" : "Selecionar aluno e ver licoes"}
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
                return <option key={key} value={key}>{studentName(student)}{text(student.turma || student.classe) ? ` - ${text(student.turma || student.classe)}` : ""}</option>;
              })}
            </select>
          </div>
          {!selectedStudent ? (
            <div className="empty-state"><div className="empty-title">Selecione um aluno</div><p className="empty-desc">As licoes lancadas para ele aparecem aqui.</p></div>
          ) : visibleLessons.length === 0 ? (
            <div className="empty-state"><div className="empty-title">Nenhuma licao encontrada</div><p className="empty-desc">Nao ha licoes direcionadas para este aluno ou turma.</p></div>
          ) : (
            <table className="data-table">
              <thead><tr><th>Licao</th><th>Turma</th><th>Prazo</th><th>Status</th><th>Entrega</th><th>Acoes</th></tr></thead>
              <tbody>
                {visibleLessons.map((licao) => {
                  const delivery = entregas.find((submission) =>
                    text(submission.activity_id) === text(licao.id) &&
                    (lower(submission.aluno) === lower(studentName(selectedStudent)) || lower(submission.aluno_login) === lower(text(selectedStudent.login || selectedStudent.usuario)))
                  );
                  return (
                    <tr key={text(licao.id)}>
                      <td><div className="table-name-cell"><span className="table-name-primary">{text(licao.titulo)}</span><span className="table-name-secondary">{(licao.questions || []).length} questoes</span></div></td>
                      <td>{text(licao.turma || "Todas")}</td>
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
