import { useEffect } from "react";

import { AppRouter } from "./app/router";
import { useUIStore } from "./stores/uiStore";

export default function App() {
  const darkMode = useUIStore((state) => state.darkMode);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", darkMode);
  }, [darkMode]);

  return <AppRouter />;
}
