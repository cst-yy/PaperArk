import { Component, type ErrorInfo, type ReactNode } from "react";

export class AppErrorBoundary extends Component<{children:ReactNode},{error:Error|null}>{
  state:{error:Error|null}={error:null};
  static getDerivedStateFromError(error:Error){return{error}}
  componentDidCatch(error:Error,info:ErrorInfo){console.error("Application render failed",error,info)}
  render(){if(this.state.error)return <main className="flex min-h-screen items-center justify-center bg-gray-50 p-6"><div className="max-w-lg rounded-xl border border-red-200 bg-white p-6 shadow-sm"><h1 className="font-semibold text-red-700">页面加载失败</h1><p className="mt-2 text-sm text-gray-600">{this.state.error.message}</p><button className="btn-primary mt-4" onClick={()=>window.location.reload()}>重新加载</button></div></main>;return this.props.children}
}
