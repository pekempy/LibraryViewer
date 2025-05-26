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

  function openModal(data) {
    titleEl.textContent = data.title;
    yearEl.textContent = data.year ? `Year: ${data.year}` : "";
    directorEl.textContent = data.directors?.length
      ? `Director(s): ${data.directors.join(", ")}`
      : "";
    ratingEl.textContent =
      data.official_rating || data.community_rating
        ? `Rating: ${data.official_rating || data.community_rating}`
        : "";
    runtimeEl.textContent = data.runtime_ticks
      ? `Runtime: ${Math.round(data.runtime_ticks / 600000000)} min`
      : "";
    descriptionEl.textContent = data.overview || "";
    modal.classList.add("show");
  }

  closeButton.addEventListener("click", () => modal.classList.remove("show"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  document.querySelectorAll(".card").forEach((card) => {
    card.addEventListener("click", () => {
      const key = card.dataset.key;
      const data = itemDetails[key];
      if (data) openModal(data);
    });
  });

  function render() {
    document.querySelectorAll(".grid").forEach((grid) => {
      const type =
        grid.closest(".tab-content").id === "movies" ? "Movie" : "Series";
      const genre = genreSelect.value;
      const year = yearSelect.value;
      const sort = sortSelect.value;
      const query = searchInput?.value.toLowerCase().trim() || "";

      let cards = Array.from(grid.querySelectorAll(".card"));

      cards.forEach((card) => {
        const title = card.dataset.title?.toLowerCase() || "";
        const cardYear = card.dataset.year;
        const cardGenres = card.dataset.genres?.split(",") || [];
        const matchesType = itemDetails[card.dataset.key]?.type === type;
        const matchesGenre = !genre || cardGenres.includes(genre);
        const matchesYear = !year || cardYear === year;
        const matchesSearch = title.includes(query);
        const visible =
          matchesType && matchesGenre && matchesYear && matchesSearch;
        card.style.display = visible ? "" : "none";
      });

      const sortedCards = cards
        .filter((card) => card.style.display !== "none")
        .sort((a, b) => {
          const aYear = parseInt(a.dataset.year) || 0;
          const bYear = parseInt(b.dataset.year) || 0;
          const aSize = parseFloat(a.dataset.size) || 0;
          const bSize = parseFloat(b.dataset.size) || 0;
          switch (sort) {
            case "title":
              return a.dataset.title.localeCompare(b.dataset.title);
            case "title-desc":
              return b.dataset.title.localeCompare(a.dataset.title);
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

      sortedCards.forEach((card) => grid.appendChild(card));
    });
  }

  [sortSelect, genreSelect, yearSelect, searchInput].forEach((el) => {
    if (el) el.addEventListener("input", render);
  });

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

  render();
});
