document.addEventListener("DOMContentLoaded", () => {
  const sortSelect = document.getElementById("sort");
  const genreSelect = document.getElementById("genre");
  const yearSelect = document.getElementById("year");
  const searchInput = document.getElementById("search");

  const modal = document.getElementById("modal");
  const closeButton = modal.querySelector(".close-button");
  const titleEl = document.getElementById("modal-title");
  const yearEl = document.getElementById("modal-year");
  const directorEl = document.getElementById("modal-director");
  const ratingEl = document.getElementById("modal-rating");
  const runtimeEl = document.getElementById("modal-runtime");
  const descriptionEl = document.getElementById("modal-description");

  function openModalFromCard(card) {
    const details = card.querySelector(".hidden-details");
    if (!details) return;

    titleEl.textContent = details.dataset.title || "";
    yearEl.textContent = details.dataset.year
      ? `Year: ${details.dataset.year}`
      : "";
    directorEl.textContent = details.dataset.directors
      ? `Director(s): ${details.dataset.directors}`
      : "";
    ratingEl.textContent = details.dataset.rating
      ? `Rating: ${details.dataset.rating}`
      : "";

    if (details.dataset.runtime) {
      const minutes = Math.round(parseInt(details.dataset.runtime) / 600000000);
      runtimeEl.textContent = `Runtime: ${minutes} min`;
    } else {
      runtimeEl.textContent = "";
    }

    descriptionEl.textContent = details.dataset.description || "";
    modal.classList.add("show");
  }

  closeButton.addEventListener("click", () => modal.classList.remove("show"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  function render() {
    const activeTab = document.querySelector(".tab-content.active");
    const type = activeTab.id === "movies" ? "Movie" : "Series";
    const genre = genreSelect.value;
    const year = yearSelect.value;
    const query = searchInput.value.toLowerCase().trim();
    const sort = sortSelect.value;

    const allCards = Array.from(activeTab.querySelectorAll(".card"));

    allCards.forEach((card) => {
      const title = card.dataset.title.toLowerCase();
      const cardYear = card.dataset.year;
      const cardGenres = card.dataset.genres.split(",");

      const matchesGenre = !genre || cardGenres.includes(genre);
      const matchesYear = !year || cardYear === year;
      const matchesSearch = !query || title.includes(query);

      const shouldShow = matchesGenre && matchesYear && matchesSearch;
      card.style.display = shouldShow ? "" : "none";
    });

    const visibleCards = allCards.filter(
      (card) => card.style.display !== "none"
    );

    visibleCards.sort((a, b) => {
      const aTitle = a.dataset.title;
      const bTitle = b.dataset.title;
      const aYear = parseInt(a.dataset.year) || 0;
      const bYear = parseInt(b.dataset.year) || 0;
      const aSize = parseFloat(a.dataset.size) || 0;
      const bSize = parseFloat(b.dataset.size) || 0;

      switch (sort) {
        case "title":
          return aTitle.localeCompare(bTitle);
        case "title-desc":
          return bTitle.localeCompare(aTitle);
        case "year":
          return bYear - aYear;
        case "year-asc":
          return aYear - bYear;
        case "size":
          return bSize - aSize;
        case "size-asc":
          return aSize - bSize;
        default:
          return 0;
      }
    });

    const grid = activeTab.querySelector(".grid");
    visibleCards.forEach((card) => grid.appendChild(card));
  }

  [sortSelect, genreSelect, yearSelect, searchInput].forEach((el) =>
    el.addEventListener("input", render)
  );

  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-button")
        .forEach((b) => b.classList.remove("active"));
      document
        .querySelectorAll(".tab-content")
        .forEach((tab) => tab.classList.remove("active"));
      btn.classList.add("active");
      document.getElementById(btn.dataset.tab).classList.add("active");
      render();
    });
  });

  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("click", () => openModalFromCard(card));
  });

  render();
});
