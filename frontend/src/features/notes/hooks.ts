import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { attachEvidence, createNote, deleteNote, detachEvidence, getNote, listNotes, saveNote } from "./api";
import type { NoteAggregate, NoteCreate } from "./types";

export const noteKeys = {
  all: ["notes"] as const,
  list: (paperId?: string) => ["notes", "list", paperId ?? "all"] as const,
  detail: (noteId: string) => ["notes", "detail", noteId] as const,
};

export function useNotes(paperId?: string) {
  return useQuery({ queryKey: noteKeys.list(paperId), queryFn: () => listNotes(paperId) });
}

export function useNote(noteId?: string) {
  return useQuery({ queryKey: noteKeys.detail(noteId ?? ""), queryFn: () => getNote(noteId!), enabled: Boolean(noteId) });
}

export function useCreateNote() {
  const client = useQueryClient();
  return useMutation({ mutationFn: (data: NoteCreate) => createNote(data), onSuccess: () => client.invalidateQueries({ queryKey: noteKeys.all }) });
}

export function useSaveNote(noteId: string) {
  const client = useQueryClient();
  return useMutation({ mutationFn: (data: NoteAggregate) => saveNote(noteId, data), onSuccess: (note) => {
    client.setQueryData(noteKeys.detail(note.id), note);
    client.invalidateQueries({ queryKey: noteKeys.all });
  }});
}

export function useDeleteNote() {
  const client = useQueryClient();
  return useMutation({ mutationFn: deleteNote, onSuccess: () => client.invalidateQueries({ queryKey: noteKeys.all }) });
}

function useEvidenceMutation(mutationFn: (noteId: string, annotationId: string) => Promise<import("./types").Note>) {
  const client = useQueryClient();
  return useMutation({ mutationFn: ({ noteId, annotationId }: { noteId: string; annotationId: string }) => mutationFn(noteId, annotationId), onSuccess: (note) => {
    client.setQueryData(noteKeys.detail(note.id), note);
    client.invalidateQueries({ queryKey: noteKeys.all });
  }});
}

export function useAttachEvidence() {
  return useEvidenceMutation(attachEvidence);
}

export function useDetachEvidence() {
  return useEvidenceMutation(detachEvidence);
}
