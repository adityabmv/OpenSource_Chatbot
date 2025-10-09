import React from "react";
import ReactDOM from "react-dom/client";
import "./styles/tailwind.css";
import App from "./MainApp.tsx";
import { AuthProvider } from "./auth/AuthContext.tsx";

const root = ReactDOM.createRoot(
  document.getElementById("root") as HTMLElement
);
root.render(
  <React.StrictMode>
    <AuthProvider>
      <App />
    </AuthProvider>
  </React.StrictMode>
);
