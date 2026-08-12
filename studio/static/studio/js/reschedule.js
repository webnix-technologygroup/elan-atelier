const detail = document.querySelector("[data-reschedule]");
if (detail) {
  const form = detail.querySelector("[data-reschedule-form]");
  if (form) {
    const date = form.elements.date;
    const time = form.elements.time;
    const grid = detail.querySelector("[data-reschedule-slots]");
    const status = detail.querySelector(".slots-status");
    const nearest = detail.querySelector("[data-reschedule-nearest]");
    detail
      .querySelector("[data-load-reschedule]")
      .addEventListener("click", async () => {
        time.value = "";
        grid.replaceChildren();
        nearest.replaceChildren();
        status.textContent = "Загружаем свободное время…";
        const url = new URL(detail.dataset.slotsUrl, location.origin);
        url.search = new URLSearchParams({
          service: detail.dataset.service,
          master: detail.dataset.master,
          date: date.value,
        });
        try {
          const response = await fetch(url);
          const data = await response.json();
          if (!response.ok)
            throw new Error(data.error || "Не удалось загрузить время.");
          status.textContent = data.slots.length
            ? "Выберите новое время."
            : "Свободного времени нет.";
          (data.nearest_dates || []).forEach((value) => {
            const button = document.createElement("button");
            button.type = "button";
            button.className = "text-link";
            button.textContent = value;
            button.addEventListener("click", () => {
              date.value = value;
              detail.querySelector("[data-load-reschedule]").click();
            });
            nearest.append(button);
          });
          data.slots.forEach((slot) => {
            const label = document.createElement("label");
            label.className = "slot-button";
            const input = document.createElement("input");
            input.type = "radio";
            input.name = "reschedule_slot";
            input.addEventListener("change", () => {
              time.value = slot.time;
            });
            const text = document.createElement("span");
            text.textContent = `${slot.time} · ${slot.master_name}`;
            label.append(input, text);
            grid.append(label);
          });
        } catch (error) {
          status.textContent = error.message;
        }
      });
  }
}
