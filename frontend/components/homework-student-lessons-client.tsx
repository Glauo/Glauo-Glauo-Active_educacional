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
  if (targetStudent) return keys.includes(lower(targetStudent));
  if (targetStudents.length > 0) return targetStudents.some((target) => keys.includes(lower(target)));
  return bookMatches(lesson, student) &&
    (!targetClass || ["todas", "todos"].includes(lower(targetClass)) || lower(targetClass) === lower(turma));
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
                      <td><div style={{ display: "flex", gap: 4 }}><HomeworkEditBtn licao={licao} turmas={turmaNames} /><HomeworkDeleteBtn licao={licao} /></div></td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          )}
        </div>
      )}
    </div>
  );
}
