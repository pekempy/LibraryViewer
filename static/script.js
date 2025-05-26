// script.js (patched to load media.json dynamically and build everything client-side)

document.addEventListener("DOMContentLoaded", async () => {
  const sortSelect = document.getElementById("sort");
  const genreSelect = document.getElementById("genre");
  const yearSelect = document.getElementById("year");
  const searchInput = document.getElementById("search");
  const scrollTopBtn = document.getElementById("scrollTopBtn");

  const modal = document.getElementById("modal");
  const closeButton = modal.querySelector(".close-button");
  const titleEl = document.getElementById("modal-title");
  const yearEl = document.getElementById("modal-year");
  const directorEl = document.getElementById("modal-director");
  const ratingEl = document.getElementById("modal-rating");
  const runtimeEl = document.getElementById("modal-runtime");
  const descriptionEl = document.getElementById("modal-description");

  const CARDS_PER_BATCH = 200;
  let currentIndex = 0;
  let filteredCards = [];
  let allCards = [];

  const movieGrid = document.getElementById("movies-grid");
  const showGrid = document.getElementById("shows-grid");

  function openModalFromCard(card) {
    const details = card.dataset;
    titleEl.textContent = details.title || "";
    yearEl.textContent = details.year ? `Year: ${details.year}` : "";
    directorEl.textContent = details.directors
      ? `Director(s): ${details.directors}`
      : "";
    ratingEl.textContent = details.rating ? `Rating: ${details.rating}` : "";

    if (details.runtime) {
      const minutes = Math.round(parseInt(details.runtime) / 600000000);
      runtimeEl.textContent = `Runtime: ${minutes} min`;
    } else {
      runtimeEl.textContent = "";
    }

    descriptionEl.textContent = details.description || "";
    modal.classList.add("show");
  }

  closeButton.addEventListener("click", () => modal.classList.remove("show"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  function createCard(item) {
    const card = document.createElement("div");
    card.className = "card clickable";
    card.dataset.title = item.title;
    card.dataset.year = item.year;
    card.dataset.size = item.size / (1024 * 1024 * 1024);
    card.dataset.genres = item.genres.join(",");
    card.dataset.directors = item.directors.join(", ");
    card.dataset.rating = item.official_rating || item.community_rating;
    card.dataset.runtime = item.runtime_ticks;
    card.dataset.description = item.overview || "";

    card.innerHTML = `
      <img src="${item.poster_path}" alt="${item.title}" loading="lazy" />
      <h3>${item.title}</h3>
      <p>${item.year || ""}</p>
      <p>${(item.size / (1024 * 1024 * 1024)).toFixed(2)} GB</p>
      <p style="margin-top: 0.5em; display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: space-evenly;">
        ${item.genres
          .map(
            (genre) =>
              `<span class="badge genre-${genre
                .replace(/\s+/g, "_")
                .toLowerCase()}">${genre}</span>`
          )
          .join("")}
      </p>
    `;

    card.addEventListener("click", () => openModalFromCard(card));
    return card;
  }

  function populateSelectors(items) {
    const allGenres = new Set();
    const allYears = new Set();

    items.forEach((item) => {
      (item.genres || []).forEach((g) => allGenres.add(g));
      if (item.year) allYears.add(item.year);
    });

    [...allGenres].sort().forEach((g) => {
      const opt = document.createElement("option");
      opt.value = g;
      opt.textContent = g;
      genreSelect.appendChild(opt);
    });

    [...allYears]
      .sort((a, b) => b - a)
      .forEach((y) => {
        const opt = document.createElement("option");
        opt.value = y;
        opt.textContent = y;
        yearSelect.appendChild(opt);
      });
  }

  function loadNextBatch() {
    const activeTab = document.querySelector(".tab-content.active");
    const grid = activeTab.querySelector(".grid");
    const nextBatch = filteredCards.slice(
      currentIndex,
      currentIndex + CARDS_PER_BATCH
    );
    nextBatch.forEach((card) => {
      card.style.display = "";
      grid.appendChild(card);
    });
    currentIndex += CARDS_PER_BATCH;
  }

  function handleScroll() {
    const nearBottom =
      window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
    if (nearBottom && currentIndex < filteredCards.length) {
      loadNextBatch();
    }
  }

  function render() {
    const activeTab = document.querySelector(".tab-content.active");
    const genre = genreSelect.value;
    const year = yearSelect.value;
    const query = searchInput.value.toLowerCase().trim();
    const sort = sortSelect.value;

    allCards.forEach((card) => (card.style.display = "none"));

    filteredCards = allCards.filter((card) => {
      const title = card.dataset.title.toLowerCase();
      const cardYear = card.dataset.year;
      const cardGenres = card.dataset.genres.split(",");
      return (
        (!genre || cardGenres.includes(genre)) &&
        (!year || cardYear === year) &&
        (!query || title.includes(query))
      );
    });

    filteredCards.sort((a, b) => {
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

    currentIndex = 0;
    const grid = activeTab.querySelector(".grid");
    grid.innerHTML = "";
    loadNextBatch();
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

  window.addEventListener("scroll", handleScroll);

  window.addEventListener("scroll", () => {
    if (window.scrollY > 400) {
      scrollTopBtn.classList.add("show");
    } else {
      scrollTopBtn.classList.remove("show");
    }
  });

  scrollTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  // Fetch and build cards from JSON
  const res = await fetch("media.json");
  const data = await res.json();
  const movieCount = document.getElementById("movie-count");
  const showCount = document.getElementById("show-count");

  const movieItems = data.filter((item) => item.type === "Movie");
  const showItems = data.filter((item) => item.type === "Series");

  movieItems.forEach((item) => {
    const card = createCard(item);
    movieGrid.appendChild(card);
    allCards.push(card);
  });

  showItems.forEach((item) => {
    const card = createCard(item);
    showGrid.appendChild(card);
    allCards.push(card);
  });

  movieCount.textContent = `${movieItems.length} titles`;
  showCount.textContent = `${showItems.length} series`;

  populateSelectors(data);
  render();
});
