import { api } from "@/services/api"; import type { Todo,TodoCreate,TodoPatch } from "./types";
export const listTodos=async()=> (await api.get<Todo[]>("/todos/",{params:{completed:false,limit:20}})).data;
export const createTodo=async(data:TodoCreate)=>(await api.post<Todo>("/todos/",data)).data;
export const updateTodo=async(id:string,data:TodoPatch)=>(await api.patch<Todo>(`/todos/${id}`,data)).data;
export const deleteTodo=async(id:string)=>{await api.delete(`/todos/${id}`);};
