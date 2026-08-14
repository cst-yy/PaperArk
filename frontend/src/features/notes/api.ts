import { api } from "@/services/api";
import type { Note, NoteAggregate, NoteCreate, NoteUpdate } from "./types";

export async function listNotes(paperId?: string): Promise<Note[]> {
  const params = paperId ? { paper_id: paperId } : {};
  const response = await api.get<Note[]>("/notes/", { params });
  return response.data;
}

export async function getNote(noteId: string): Promise<Note> {
  const response = await api.get<Note>(`/notes/${noteId}`);
  return response.data;
}

export async function createNote(data: NoteCreate): Promise<Note> {
  const response = await api.post<Note>("/notes/", data);
  return response.data;
}

export async function updateNote(noteId: string, data: NoteUpdate): Promise<Note> {
  const response = await api.patch<Note>(`/notes/${noteId}`, data);
  return response.data;
}

export async function saveNote(noteId: string, data: NoteAggregate): Promise<Note> {
  const response = await api.put<Note>(`/notes/${noteId}`, data);
  return response.data;
}

export async function deleteNote(noteId: string): Promise<void> {
  await api.delete(`/notes/${noteId}`);
}

export async function replaceEvidence(noteId: string, annotationIds: string[]): Promise<Note> {
  const response = await api.put<Note>(`/notes/${noteId}/evidence`, { annotation_ids: annotationIds });
  return response.data;
}

export async function attachEvidence(noteId: string, annotationId: string): Promise<Note> {
  const response = await api.post<Note>(`/notes/${noteId}/evidence/${annotationId}`);
  return response.data;
}

export async function detachEvidence(noteId: string, annotationId: string): Promise<Note> {
  const response = await api.delete<Note>(`/notes/${noteId}/evidence/${annotationId}`);
  return response.data;
}
