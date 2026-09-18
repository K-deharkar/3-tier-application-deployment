import { useEffect, useState } from "react";

const API_URL = "http://localhost:8000";

function App() {

  const [isLoggedIn, setIsLoggedIn] = useState(
    Boolean(localStorage.getItem("token"))
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


  // ==========================================================
  // LOGIN
  // ==========================================================

  async function handleLogin(event) {

    event.preventDefault();

    setError("");
    setMessage("");

    try {

      const response = await fetch(
        `${API_URL}/login`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            email,
            password
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Login failed"
        );

      }

      localStorage.setItem(
        "token",
        data.access_token
      );

      localStorage.setItem(
        "username",
        data.username
      );

      setIsLoggedIn(true);

      setEmail("");
      setPassword("");

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // REGISTER
  // ==========================================================

  async function handleRegister(event) {

    event.preventDefault();

    setError("");
    setMessage("");

    try {

      const response = await fetch(
        `${API_URL}/register`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            username,
            email,
            password
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Registration failed"
        );

      }

      setMessage(
        "Registration successful. You can now login."
      );

      setUsername("");
      setEmail("");
      setPassword("");

      setShowRegister(false);

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // GET TASKS
  // ==========================================================

  async function loadTasks() {

    const token = localStorage.getItem("token");

    if (!token) {
      return;
    }

    try {

      const response = await fetch(
        `${API_URL}/tasks?token=${token}`
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Unable to load tasks"
        );

      }

      setTasks(data);

    } catch (err) {

      setError(err.message);

    }
  }


  useEffect(() => {

    if (isLoggedIn) {
      loadTasks();
    }

  }, [isLoggedIn]);


  // ==========================================================
  // CREATE TASK
  // ==========================================================

  async function handleCreateTask(event) {

    event.preventDefault();

    if (!title.trim()) {

      setError("Task title is required");

      return;
    }

    const token = localStorage.getItem("token");

    try {

      const response = await fetch(
        `${API_URL}/tasks?token=${token}`,
        {
          method: "POST",

          headers: {
            "Content-Type": "application/json"
          },

          body: JSON.stringify({
            title,
            description
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Unable to create task"
        );

      }

      setTasks([
        ...tasks,
        data
      ]);

      setTitle("");
      setDescription("");

      setMessage("Task created successfully");

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // COMPLETE TASK
  // ==========================================================

  async function completeTask(taskId) {

    const token = localStorage.getItem("token");

    try {

      const response = await fetch(
        `${API_URL}/tasks/${taskId}/complete?token=${token}`,
        {
          method: "PATCH"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Unable to complete task"
        );

      }

      setTasks(
        tasks.map(task =>
          task.id === taskId
            ? data
            : task
        )
      );

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // DELETE TASK
  // ==========================================================

  async function deleteTask(taskId) {

    const token = localStorage.getItem("token");

    try {

      const response = await fetch(
        `${API_URL}/tasks/${taskId}?token=${token}`,
        {
          method: "DELETE"
        }
      );

      const data = await response.json();

      if (!response.ok) {

        throw new Error(
          data.detail || "Unable to delete task"
        );

      }

      setTasks(
        tasks.filter(
          task => task.id !== taskId
        )
      );

      setMessage(
        "Task deleted successfully"
      );

    } catch (err) {

      setError(err.message);

    }
  }


  // ==========================================================
  // LOGOUT
  // ==========================================================

  function logout() {

    localStorage.removeItem("token");
    localStorage.removeItem("username");

    setTasks([]);
    setIsLoggedIn(false);

  }


  // ==========================================================
  // LOGIN / REGISTER PAGE
  // ==========================================================

  if (!isLoggedIn) {

    return (

      <div className="auth-container">

        <div className="auth-card">

          <h1>Task Manager</h1>

          <p className="subtitle">
            3-Tier Task Management Application
          </p>

          {error && (
            <div className="error">
              {error}
            </div>
          )}

          {message && (
            <div className="message">
              {message}
            </div>
          )}


          {!showRegister ? (

            <>
              <h2>Login</h2>

              <form onSubmit={handleLogin}>

                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={
                    e => setEmail(e.target.value)
                  }
                  required
                />

                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={
                    e => setPassword(e.target.value)
                  }
                  required
                />

                <button type="submit">
                  Login
                </button>

              </form>

              <p>
                Don't have an account?
              </p>

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
                  onChange={
                    e => setUsername(e.target.value)
                  }
                  required
                />

                <input
                  type="email"
                  placeholder="Email"
                  value={email}
                  onChange={
                    e => setEmail(e.target.value)
                  }
                  required
                />

                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={
                    e => setPassword(e.target.value)
                  }
                  required
                />

                <button type="submit">
                  Register
                </button>

              </form>

              <p>
                Already have an account?
              </p>

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
            Welcome,{" "}
            <strong>
              {localStorage.getItem("username")}
            </strong>
          </p>
        </div>

        <button
          className="logout-button"
          onClick={logout}
        >
          Logout
        </button>

      </header>


      <main className="container">

        {error && (
          <div className="error">
            {error}
          </div>
        )}

        {message && (
          <div className="message">
            {message}
          </div>
        )}


        {/* CREATE TASK */}

        <section className="task-form">

          <h2>Create New Task</h2>

          <form onSubmit={handleCreateTask}>

            <input
              type="text"
              placeholder="Task title"
              value={title}
              onChange={
                e => setTitle(e.target.value)
              }
            />

            <textarea
              placeholder="Task description"
              value={description}
              onChange={
                e => setDescription(e.target.value)
              }
            />

            <button type="submit">
              Add Task
            </button>

          </form>

        </section>


        {/* TASK LIST */}

        <section className="tasks-section">

          <h2>
            My Tasks ({tasks.length})
          </h2>

          {tasks.length === 0 ? (

            <div className="empty-state">
              <p>No tasks found.</p>
              <p>Create your first task above.</p>
            </div>

          ) : (

            <div className="task-list">

              {tasks.map(task => (

                <div
                  className={`task-card ${
                    task.completed
                      ? "completed"
                      : ""
                  }`}
                  key={task.id}
                >

                  <div className="task-content">

                    <h3>
                      {task.title}
                    </h3>

                    <p>
                      {task.description}
                    </p>

                    <span
                      className={
                        task.completed
                          ? "status completed-status"
                          : "status pending-status"
                      }
                    >
                      {task.completed
                        ? "Completed"
                        : "Pending"
                      }
                    </span>

                  </div>

                  <div className="task-actions">

                    {!task.completed && (

                      <button
                        onClick={() =>
                          completeTask(task.id)
                        }
                      >
                        Complete
                      </button>

                    )}

                    <button
                      className="delete-button"
                      onClick={() =>
                        deleteTask(task.id)
                      }
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