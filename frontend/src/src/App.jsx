import React, { useCallback, useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

// ============================================================
// HELPERS
// ============================================================

// FastAPI returns `detail` as a string for HTTPException, but as an
// ARRAY of objects for 422 validation errors. Rendering that array
// directly in React crashes the page, so normalise it to a string.
function extractErrorMessage(data, fallback) {
  if (!data) return fallback;

  const detail = data.detail;

  if (typeof detail === "string") return detail;

  if (Array.isArray(detail)) {
    return (
      detail
        .map((item) => {
          const field = Array.isArray(item.loc) ? item.loc[item.loc.length - 1] : "";
          const msg = item.msg || "Invalid value";
          return field ? `${field}: ${msg}` : msg;
        })
        .join(", ") || fallback
    );
  }

  if (typeof data.message === "string") return data.message;

  return fallback;
}

async function safeJson(response) {
  try {
    return await response.json();
  } catch {
    return null;
  }
}

function App() {
  const [token, setToken] = useState(() => localStorage.getItem("token") || "");
  const [currentUser, setCurrentUser] = useState(
    () => localStorage.getItem("username") || ""
  );

  const [showRegister, setShowRegister] = useState(false);

  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  const [tasks, setTasks] = useState([]);

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);

  const isLoggedIn = Boolean(token);

  const logout = useCallback(() => {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    setToken("");
    setCurrentUser("");
    setTasks([]);
  }, []);

  // Single place where every authenticated request is built.
  const apiFetch = useCallback(
    async (path, options = {}) => {
      const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`,
          ...(options.headers || {}),
        },
      });

      const data = await safeJson(response);

      if (response.status === 401) {
        logout();
        throw new Error(
          extractErrorMessage(data, "Your session ended. Please log in again.")
        );
      }

      if (!response.ok) {
        throw new Error(extractErrorMessage(data, "Request failed"));
      }

      return data;
    },
    [token, logout]
  );

  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(event) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email, password }),
      });

      const data = await safeJson(response);

      if (!response.ok) {
        throw new Error(extractErrorMessage(data, "Login failed"));
      }

      localStorage.setItem("token", data.access_token);
      localStorage.setItem("username", data.username);

      setToken(data.access_token);
      setCurrentUser(data.username);

      setEmail("");
      setPassword("");
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the server. Is the backend running on port 8000?"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // REGISTER
  // ==========================================================

  async function handleRegister(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (password.length < 6) {
      setError("Password must be at least 6 characters");
      return;
    }

    setLoading(true);

    try {
      const response = await fetch(`${API_URL}/register`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, email, password }),
      });

      const data = await safeJson(response);

      if (!response.ok) {
        throw new Error(extractErrorMessage(data, "Registration failed"));
      }

      setMessage("Registration successful. You can now log in.");

      setUsername("");
      setEmail("");
      setPassword("");
      setShowRegister(false);
    } catch (err) {
      setError(
        err instanceof TypeError
          ? "Cannot reach the server. Is the backend running on port 8000?"
          : err.message
      );
    } finally {
      setLoading(false);
    }
  }

  // ==========================================================
  // TASKS
  // ==========================================================

  const loadTasks = useCallback(async () => {
    if (!token) return;

    try {
      const data = await apiFetch("/tasks");
      setTasks(Array.isArray(data) ? data : []);
    } catch (err) {
      setError(err.message);
    }
  }, [token, apiFetch]);

  useEffect(() => {
    if (token) loadTasks();
  }, [token, loadTasks]);

  async function handleCreateTask(event) {
    event.preventDefault();
    setError("");
    setMessage("");

    if (!title.trim()) {
      setError("Task title is required");
      return;
    }

    try {
      const data = await apiFetch("/tasks", {
        method: "POST",
        body: JSON.stringify({ title: title.trim(), description }),
      });

      setTasks((prev) => [data, ...prev]);
      setTitle("");
      setDescription("");
      setMessage("Task created successfully");
    } catch (err) {
      setError(err.message);
    }
  }

  async function completeTask(taskId) {
    setError("");

    try {
      const data = await apiFetch(`/tasks/${taskId}/complete`, {
        method: "PATCH",
      });

      setTasks((prev) => prev.map((task) => (task.id === taskId ? data : task)));
    } catch (err) {
      setError(err.message);
    }
  }

  async function deleteTask(taskId) {
    setError("");
    setMessage("");

    try {
      await apiFetch(`/tasks/${taskId}`, { method: "DELETE" });

      setTasks((prev) => prev.filter((task) => task.id !== taskId));
      setMessage("Task deleted successfully");
    } catch (err) {
      setError(err.message);
    }
  }

  // ==========================================================
  // LOGIN / REGISTER PAGE
  // ==========================================================

  if (!isLoggedIn) {
    return (
      <div className="auth-container">
        <div className="auth-card">
          <h1>Task Manager</h1>
          <p className="subtitle">3-Tier Task Management Application</p>

          {error && <div className="error">{error}</div>}
          {message && <div className="message">{message}</div>}

          {!showRegister ? (
            <>
              <h2>Login</h2>

              <form onSubmit={handleLogin}>
                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />

                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                />

                <button type="submit" disabled={loading}>
                  {loading ? "Logging in..." : "Login"}
                </button>
              </form>

              <p>Don't have an account?</p>

              <button
                className="secondary-button"
                onClick={() => {
                  setShowRegister(true);
                  setError("");
                  setMessage("");
                }}
              >
                Create Account
              </button>
            </>
          ) : (
            <>
              <h2>Create Account</h2>

              <form onSubmit={handleRegister}>
                <input
                  type="text"
                  placeholder="Username"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  required
                />

                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />

                <input
                  type="password"
                  placeholder="Password (min 6 characters)"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  minLength={6}
                  required
                />

                <button type="submit" disabled={loading}>
                  {loading ? "Creating..." : "Register"}
                </button>
              </form>

              <p>Already have an account?</p>

              <button
                className="secondary-button"
                onClick={() => {
                  setShowRegister(false);
                  setError("");
                  setMessage("");
                }}
              >
                Back to Login
              </button>
            </>
          )}
        </div>
      </div>
    );
  }

  // ==========================================================
  // TASK DASHBOARD
  // ==========================================================

  return (
    <div className="app">
      <header className="header">
        <div>
          <h1>Task Manager</h1>
          <p>
            Welcome, <strong>{currentUser}</strong>
          </p>
        </div>

        <button className="logout-button" onClick={logout}>
          Logout
        </button>
      </header>

      <main className="container">
        {error && <div className="error">{error}</div>}
        {message && <div className="message">{message}</div>}

        <section className="task-form">
          <h2>Create New Task</h2>

          <form onSubmit={handleCreateTask}>
            <input
              type="text"
              placeholder="Task title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
            />

            <textarea
              placeholder="Task description"
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />

            <button type="submit">Add Task</button>
          </form>
        </section>

        <section className="tasks-section">
          <h2>My Tasks ({tasks.length})</h2>

          {tasks.length === 0 ? (
            <div className="empty-state">
              <p>No tasks found.</p>
              <p>Create your first task above.</p>
            </div>
          ) : (
            <div className="task-list">
              {tasks.map((task) => (
                <div
                  className={`task-card ${task.completed ? "completed" : ""}`}
                  key={task.id}
                >
                  <div className="task-content">
                    <h3>{task.title}</h3>
                    <p>{task.description}</p>

                    <span
                      className={
                        task.completed
                          ? "status completed-status"
                          : "status pending-status"
                      }
                    >
                      {task.completed ? "Completed" : "Pending"}
                    </span>
                  </div>

                  <div className="task-actions">
                    <button onClick={() => completeTask(task.id)}>
                      {task.completed ? "Undo" : "Complete"}
                    </button>

                    <button
                      className="delete-button"
                      onClick={() => deleteTask(task.id)}
                    >
                      Delete
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

export default App;
