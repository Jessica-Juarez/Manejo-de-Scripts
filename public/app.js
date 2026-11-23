const form = document.querySelector("#task-form");
const input = document.querySelector("#task-title");
const list = document.querySelector("#task-list");
const emptyState = document.querySelector("#empty-state");
const count = document.querySelector("#task-count");
const message = document.querySelector("#message");

async function request(path, options) {
  const response = await fetch(path, options);
  if (!response.ok) {
    const result = await response.json();
    throw new Error(result.error || "No se pudo completar la solicitud.");
  }
  return response.status === 204 ? null : response.json();
}

function renderTasks(tasks) {
  list.replaceChildren();
  for (const task of tasks) {
    const item = document.createElement("li");
    item.className = "task-item";

    const title = document.createElement("span");
    title.textContent = task.title;

    const remove = document.createElement("button");
    remove.type = "button";
    remove.className = "delete-button";
    remove.textContent = "Eliminar";
    remove.setAttribute("aria-label", `Eliminar: ${task.title}`);
    remove.addEventListener("click", async () => {
      try {
        await request(`/api/tasks/${task.id}`, { method: "DELETE" });
        message.textContent = "";
        await loadTasks();
      } catch (error) {
        message.textContent = error.message;
      }
    });

    item.append(title, remove);
    list.append(item);
  }

  emptyState.hidden = tasks.length > 0;
  count.textContent = `${tasks.length} ${tasks.length === 1 ? "tarea" : "tareas"}`;
}

async function loadTasks() {
  const result = await request("/api/tasks");
  renderTasks(result.tasks);
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const title = input.value.trim();
  if (!title) return;

  try {
    await request("/api/tasks", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    input.value = "";
    message.textContent = "";
    await loadTasks();
    input.focus();
  } catch (error) {
    message.textContent = error.message;
  }
});

loadTasks().catch((error) => {
  message.textContent = error.message;
});
