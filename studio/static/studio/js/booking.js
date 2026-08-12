const wizard = document.querySelector("[data-booking]");

if (wizard) {
  const form = wizard.querySelector("form");
  const steps = [...wizard.querySelectorAll("[data-step]")];
  const progress = [...wizard.querySelectorAll(".wizard-progress li")];
  const service = form.elements.service;
  const master = form.elements.master;
  const date = form.elements.date;
  const time = form.elements.time;
  const selectedMaster = form.elements.selected_master;
  const slots = wizard.querySelector(".slot-grid");
  const status = wizard.querySelector(".slots-status");
  const errorRegions = [...wizard.querySelectorAll("[data-step-error]")];
  const nearest = wizard.querySelector("[data-nearest-dates]");
  let currentStep = 0;
  let selectedMasterName = "";
  let serviceMeta = {};

  function showStep(index) {
    currentStep = Math.max(0, Math.min(index, steps.length - 1));
    steps.forEach((step, position) => {
      step.hidden = position !== currentStep;
    });
    progress.forEach((item, position) => {
      if (position === currentStep) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
    });
    const heading = steps[currentStep].querySelector("h2");
    if (heading) {
      heading.setAttribute("tabindex", "-1");
      heading.focus();
    }
  }

  function resetSlot() {
    time.value = "";
    selectedMaster.value = "";
    selectedMasterName = "";
    slots.replaceChildren();
    nearest.replaceChildren();
    status.textContent = "";
  }

  function createMasterCard(item) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "master-choice-card";
    button.setAttribute("aria-pressed", "false");
    button.dataset.masterId = String(item.id);
    const image = document.createElement("img");
    image.src = item.image || "/static/studio/img/atelier.svg";
    image.alt = item.name
      ? `Мастер ${item.name}`
      : "Выбор любого подходящего мастера";
    const copy = document.createElement("span");
    const title = document.createElement("strong");
    title.textContent = item.name || "Любой подходящий мастер";
    const detailText = document.createElement("small");
    detailText.textContent = item.name
      ? [item.specialization, item.experience].filter(Boolean).join(" · ")
      : "Назначим доступного специалиста для выбранного слота";
    copy.append(title, detailText);
    button.append(image, copy);
    button.addEventListener("click", () => {
      master.value = item.id;
      wizard.querySelectorAll(".master-choice-card").forEach((card) => {
        card.classList.remove("selected");
        card.setAttribute("aria-pressed", "false");
      });
      button.classList.add("selected");
      button.setAttribute("aria-pressed", "true");
      resetSlot();
    });
    return button;
  }

  function syncMasterCard() {
    wizard.querySelectorAll(".master-choice-card").forEach((card) => {
      const selected = card.dataset.masterId === master.value;
      card.classList.toggle("selected", selected);
      card.setAttribute("aria-pressed", String(selected));
    });
  }

  async function loadMasters() {
    const previousMaster = master.value;
    master.replaceChildren(new Option("Любой подходящий мастер", ""));
    const cards = wizard.querySelector("[data-master-cards]");
    cards.replaceChildren(
      createMasterCard({
        id: "",
        name: "",
        specialization: "",
        experience: "",
        image: "",
      }),
    );
    if (!service.value) return;
    const url = new URL(wizard.dataset.mastersUrl, location.origin);
    url.searchParams.set("service", service.value);
    const response = await fetch(url);
    const data = await response.json();
    serviceMeta = data.service || {};
    if (!response.ok)
      throw new Error(data.error || "Не удалось загрузить мастеров.");
    data.masters.forEach((item) => {
      master.append(
        new Option(`${item.name} · ${item.specialization}`, item.id),
      );
      cards.append(createMasterCard(item));
    });
    if ([...master.options].some((option) => option.value === previousMaster)) {
      master.value = previousMaster;
    }
    selectedMaster.value = "";
    time.value = "";
    syncMasterCard();
  }

  function selectSlot(slot) {
    time.value = slot.time;
    selectedMaster.value = slot.master_id;
    selectedMasterName = slot.master_name;
    slots.querySelectorAll("input").forEach((input) => {
      input.checked = false;
    });
    const input = document.getElementById(
      `slot-${slot.master_id}-${slot.time.replace(":", "")}`,
    );
    if (input) input.checked = true;
  }

  function renderNearestDates(values) {
    nearest.replaceChildren();
    if (!values.length) return;
    const label = document.createElement("p");
    label.textContent = "Ближайшие доступные даты:";
    nearest.append(label);
    values.forEach((value) => {
      const button = document.createElement("button");
      button.type = "button";
      button.className = "text-link";
      button.textContent = value;
      button.addEventListener("click", () => {
        date.value = value;
        loadSlots();
      });
      nearest.append(button);
    });
  }

  async function loadSlots() {
    resetSlot();
    if (!service.value || !date.value) return;
    showStep(3);
    status.textContent = "Загружаем свободное время…";
    try {
      const url = new URL(wizard.dataset.slotsUrl, location.origin);
      url.search = new URLSearchParams({
        service: service.value,
        master: master.value || "any",
        date: date.value,
      });
      const response = await fetch(url);
      const data = await response.json();
      if (!response.ok)
        throw new Error(data.error || "Не удалось загрузить время.");
      status.textContent = data.slots.length
        ? "Выберите интервал."
        : "На эту дату свободного времени нет.";
      data.slots.forEach((slot) => {
        const id = `slot-${slot.master_id}-${slot.time.replace(":", "")}`;
        const label = document.createElement("label");
        label.className = "slot-button";
        const input = document.createElement("input");
        input.type = "radio";
        input.name = "available_slot";
        input.id = id;
        input.addEventListener("change", () => selectSlot(slot));
        const text = document.createElement("span");
        text.textContent = `${slot.time} · ${slot.master_name}`;
        label.append(input, text);
        slots.append(label);
      });
      renderNearestDates(data.nearest_dates || []);
    } catch (error) {
      showStep(3);
      showError(error.message, null, 3);
    }
  }

  function appendReview(term, value) {
    const row = document.createElement("div");
    const dt = document.createElement("dt");
    const dd = document.createElement("dd");
    dt.textContent = term;
    dd.textContent = value || "—";
    row.append(dt, dd);
    wizard.querySelector(".booking-review").append(row);
  }

  function renderReview() {
    if (!time.value) {
      status.textContent = "Сначала выберите свободное время.";
      showStep(3);
      return;
    }
    const review = wizard.querySelector(".booking-review");
    review.replaceChildren();
    appendReview("Услуга", service.options[service.selectedIndex].text);
    appendReview("Категория", serviceMeta.category);
    appendReview("Стоимость", serviceMeta.price);
    appendReview(
      "Длительность",
      serviceMeta.duration ? `${serviceMeta.duration} минут` : "—",
    );
    appendReview(
      "Мастер",
      selectedMasterName || master.options[master.selectedIndex]?.text || "—",
    );
    appendReview("Дата и время", `${date.value} · ${time.value}`);
    appendReview("Имя", form.elements.name.value);
    appendReview("Телефон", form.elements.phone.value);
    appendReview("Email", form.elements.email.value);
    appendReview("Комментарий", form.elements.message.value);
    appendReview("Отмена и перенос", "Не позднее чем за 12 часов до визита");
    showStep(5);
  }

  function clearFieldError(field) {
    if (!field) return;
    field.removeAttribute("aria-invalid");
    const previous = field.dataset.previousDescribedby;
    if (previous) field.setAttribute("aria-describedby", previous);
    else field.removeAttribute("aria-describedby");
    delete field.dataset.previousDescribedby;
  }

  function clearStepError(index = currentStep) {
    const region = errorRegions[index];
    if (region) region.textContent = "";
    steps[index]?.querySelectorAll('[aria-invalid="true"]').forEach(clearFieldError);
  }

  function showError(message, field, stepIndex = currentStep) {
    const region = errorRegions[stepIndex];
    if (region) {
      region.textContent = message;
      if (field) {
        if (field.hasAttribute("aria-describedby")) {
          field.dataset.previousDescribedby = field.getAttribute("aria-describedby");
        }
        field.setAttribute("aria-invalid", "true");
        field.setAttribute("aria-describedby", region.id);
        field.focus();
      }
    }
    return false;
  }

  function validateStep(index) {
    if (index === 0 && !service.value)
      return showError("Выберите услугу.", service);
    if (index === 2) {
      if (!date.value) return showError("Выберите дату.", date);
      const chosen = new Date(`${date.value}T00:00:00`);
      const today = new Date();
      today.setHours(0, 0, 0, 0);
      const limit = new Date(today);
      limit.setDate(limit.getDate() + 60);
      if (chosen < today || chosen > limit)
        return showError("Дата должна быть в пределах 60 дней.", date);
    }
    if (index === 3 && (!time.value || !selectedMaster.value))
      return showError(
        "Выберите свободный слот.",
        slots.querySelector("input"),
      );
    if (index === 4) {
      for (const field of [
        form.elements.name,
        form.elements.phone,
        form.elements.email,
        form.elements.consent,
      ]) {
        if (!field.checkValidity())
          return showError(
            field.validationMessage || "Заполните обязательное поле.",
            field,
          );
      }
      const digits = form.elements.phone.value.match(/\d/g) || [];
      if (digits.length < 10 || digits.length > 15)
        return showError(
          "Введите от 10 до 15 цифр телефона.",
          form.elements.phone,
        );
    }
    clearStepError(index);
    return true;
  }

  service.addEventListener("change", async () => {
    resetSlot();
    master.value = "";
    await loadMasters();
  });
  master.addEventListener("change", () => { clearStepError(1); syncMasterCard(); resetSlot(); });
  date.addEventListener("change", () => { clearStepError(2); resetSlot(); });
  [service, form.elements.name, form.elements.phone, form.elements.email, form.elements.consent].forEach((field) => field.addEventListener("input", () => clearFieldError(field)));
  wizard.querySelectorAll("[data-next]").forEach((button) =>
    button.addEventListener("click", () => {
      if (validateStep(currentStep)) showStep(currentStep + 1);
    }),
  );
  wizard
    .querySelectorAll("[data-back]")
    .forEach((button) =>
      button.addEventListener("click", () => showStep(currentStep - 1)),
    );
  wizard
    .querySelector("[data-load-slots]")
    .addEventListener("click", loadSlots);
  wizard.querySelector("[data-review]").addEventListener("click", () => {
    if (validateStep(4)) renderReview();
  });
  form.addEventListener("submit", (event) => {
    if (!validateStep(4) || !time.value || !selectedMaster.value) {
      event.preventDefault();
      showStep(!time.value ? 3 : 4);
      return;
    }
    const button = wizard.querySelector("[data-submit]");
    button.disabled = true;
    button.textContent = "Создаём запись…";
  });
  const initialStep = Math.max(1, Number(wizard.dataset.initialStep || 1));
  showStep(initialStep - 1);
  if (service.value)
    loadMasters().catch((error) => {
      showStep(1);
      showError(error.message, master, 1);
    });
}
