document.addEventListener("DOMContentLoaded", async () => {
  // ─────────────────────────────
  // 🔧 DOM Elements
  // ─────────────────────────────
  const sortSelect = document.getElementById("sort");
  const genreSelect = document.getElementById("genre");
  const yearSelect = document.getElementById("year");
  const searchInput = document.getElementById("search");
  const scrollTopBtn = document.getElementById("scrollTopBtn");
  const clearFiltersBtn = document.getElementById("clear-filters");

  const modal = document.getElementById("modal");
  const closeButton = modal.querySelector(".close-button");
  const titleEl = document.getElementById("modal-title");
  const yearEl = document.getElementById("modal-year");
  const directorEl = document.getElementById("modal-director");
  const ratingEl = document.getElementById("modal-rating");
  const runtimeEl = document.getElementById("modal-runtime");
  const descriptionEl = document.getElementById("modal-description");

  const movieGrid = document.getElementById("movies-grid");
  const showGrid = document.getElementById("shows-grid");
  const movieCount = document.getElementById("movie-count");
  const showCount = document.getElementById("show-count");

  // ─────────────────────────────
  // 📦 App State
  // ─────────────────────────────
  const CARDS_PER_BATCH = 200;
  let currentIndex = 0;
  let filteredCards = [];
  let allCards = [];
  let activeType = "Movie";
  let data = [];
  let activeCollectionFilter = null;

  // ─────────────────────────────
  // 🎨 Utility Functions
  // ─────────────────────────────
  function getGenreSlug(genre) {
    return genre
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/&/g, "and")
      .replace(/[^\w-]/g, "");
  }

  function getContrastTextColor(hsl) {
    const [h, s, l] = hsl.match(/\d+/g).map(Number);
    return l > 60 ? "#000" : "#fff";
  }

  function generateColorMap(genres) {
    const sortedGenres = [...genres].map(getGenreSlug).sort();
    const colorMap = {};
    const step = 360 / sortedGenres.length;

    sortedGenres.forEach((slug, i) => {
      const hue = Math.round(step * i);
      const color = `hsl(${hue}, 65%, 55%)`;
      colorMap[slug] = color;
    });

    return colorMap;
  }

  function injectGenreStyles(colorMap) {
    const style = document.createElement("style");
    document.head.appendChild(style);
    const sheet = style.sheet;

    for (const [slug, color] of Object.entries(colorMap)) {
      const textColor = getContrastTextColor(color);
      const hsla = color.replace("hsl", "hsla").replace(")", ", 0.3)");
      const rule = `.genre-${slug} {
        background-color: ${hsla};
        outline: 1px solid ${color};
        color: ${textColor};
      }`;
      try {
        sheet.insertRule(rule, sheet.cssRules.length);
      } catch (e) {
        console.warn("Failed to insert rule for genre:", slug, rule, e);
      }
    }
  }

  // ─────────────────────────────
  // 🧼 Filtering
  // ─────────────────────────────
  function filterByCollection(collectionId) {
    genreSelect.value = "";
    yearSelect.value = "";
    searchInput.value = "";
    sortSelect.value = "title";

    activeCollectionFilter = collectionId;

    filteredCards = allCards.filter((card) => {
      const id = card.dataset.id;
      const item = data.find((d) => d.id === id);
      return (item.collections || []).some((c) => c.id === collectionId);
    });

    window.scrollTo({ top: 0, behavior: "smooth" });
    currentIndex = 0;
    const grid = activeType === "Movie" ? movieGrid : showGrid;
    grid.innerHTML = "";
    loadNextBatch();
  }

  clearFiltersBtn.addEventListener("click", () => {
    sortSelect.value = "title";
    genreSelect.value = "";
    yearSelect.value = "";
    searchInput.value = "";
    activeCollectionFilter = null;
    render();
  });

  // ─────────────────────────────
  // 🎴 UI Functions
  // ─────────────────────────────
  function openModalFromCard(card) {
    const details = card.dataset;
    titleEl.textContent = details.title || "";
    yearEl.textContent = details.year ? `Year: ${details.year}` : "";
    directorEl.textContent = details.directors
      ? `Director(s): ${details.directors}`
      : "";
    ratingEl.textContent = details.rating ? `Rating: ${details.rating}` : "";
    runtimeEl.textContent = details.runtime
      ? `Runtime: ${Math.round(parseInt(details.runtime) / 600000000)} min`
      : "";
    descriptionEl.textContent = details.description || "";
    modal.classList.add("show");
  }

  closeButton.addEventListener("click", () => modal.classList.remove("show"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  const seenLetters = { movies: new Set(), shows: new Set() };

  function createCard(item) {
    const card = document.createElement("div");
    card.dataset.id = item.id;
    card.className = `card clickable ${
      item.type === "Movie" ? "movie" : "show"
    }`;
    card.dataset.title = item.title;
    card.dataset.year = item.year;
    card.dataset.size = item.size / (1024 * 1024 * 1024);
    card.dataset.genres = item.genres.join(",");
    card.dataset.directors = item.directors.join(", ");
    card.dataset.rating = item.official_rating || item.community_rating;
    card.dataset.runtime = item.runtime_ticks;
    card.dataset.description = item.overview || "";

    const firstChar = (() => {
      const articles = ["a", "an", "the", "and", "(", ")"];
      const words = item.title.toLowerCase().split(" ");
      const index = words.length > 1 && articles.includes(words[0]) ? 1 : 0;
      const char = words[index]?.[0]?.toUpperCase() || "#";
      return /^[A-Z]$/.test(char) ? char : "#";
    })();

    let anchor = "";
    const typeKey = item.type === "Movie" ? "movies" : "shows";
    const isFirstCard =
      allCards.filter((c) => c.classList.contains(typeKey.slice(0, -1)))
        .length === 0;

    if (
      !seenLetters[typeKey].has(firstChar) ||
      (firstChar === "#" && isFirstCard)
    ) {
      seenLetters[typeKey].add(firstChar);
      anchor = `<a id="jump-${typeKey}-${firstChar}"></a>`;
    }

    card.innerHTML = `
      ${anchor}
      <img src="${item.poster_path}" alt="${item.title}" loading="lazy" />
      <h3>${item.title}</h3>
      <p>${item.year || ""}</p>
      <p>${(item.size / (1024 * 1024 * 1024)).toFixed(2)} GB</p>
      <div class="collection-buttons">
        ${(item.collections || [])
          .map(
            (c) =>
              `<button class="collection-btn" data-collection-id="${c.id}">${c.name}</button>`
          )
          .join("")}
      </div>
      <p style="margin-top: 0.5em; display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: space-evenly;">
        ${item.genres
          .map(
            (genre) =>
              `<span class="badge genre-${getGenreSlug(genre)}">${genre}</span>`
          )
          .join("")}
      </p>
    `;

    card.addEventListener("click", () => openModalFromCard(card));
    card.querySelectorAll(".collection-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        filterByCollection(btn.dataset.collectionId);
      });
    });

    return card;
  }

  function loadNextBatch() {
    const grid = activeType === "Movie" ? movieGrid : showGrid;
    const nextBatch = filteredCards.slice(
      currentIndex,
      currentIndex + CARDS_PER_BATCH
    );
    nextBatch.forEach((card) => {
      grid.appendChild(card);
    });
    currentIndex += CARDS_PER_BATCH;
  }

  function render() {
    const genre = genreSelect.value;
    const year = yearSelect.value;
    const query = searchInput.value.toLowerCase().trim();
    const sort = sortSelect.value;

    filteredCards = allCards.filter((card) => {
      const isActive =
        (activeType === "Movie" && card.classList.contains("movie")) ||
        (activeType === "Series" && card.classList.contains("show"));
      if (!isActive) return false;

      const title = card.dataset.title.toLowerCase();
      const cardYear = card.dataset.year;
      const cardGenres = card.dataset.genres.split(",");

      if (activeCollectionFilter) {
        const id = card.dataset.id;
        const item = data.find((d) => d.id === id);
        const inCollection = (item?.collections || []).some(
          (c) => c.id === activeCollectionFilter
        );
        if (!inCollection) return false;
      }

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
    const grid = activeType === "Movie" ? movieGrid : showGrid;
    document.querySelectorAll(".jump-list a").forEach((link) => {
      const letter = link.textContent.trim().toUpperCase();
      link.setAttribute(
        "href",
        `#jump-${activeType === "Movie" ? "movies" : "shows"}-${letter || "#"}`
      );
    });
    grid.innerHTML = "";

    seenLetters.movies = new Set();
    seenLetters.shows = new Set();

    filteredCards.forEach((card) => {
      const title = card.dataset.title;
      const type = card.classList.contains("movie") ? "movies" : "shows";

      const articles = ["a", "an", "the"];
      const words = title.toLowerCase().split(" ");
      const index = words.length > 1 && articles.includes(words[0]) ? 1 : 0;
      const char = words[index]?.[0]?.toUpperCase() || "#";
      const firstChar = /^[A-Z]$/.test(char) ? char : "#";

      seenLetters[type].add(firstChar);
    });
    loadNextBatch();
  }

  // ─────────────────────────────
  // 🔁 Data Setup
  // ─────────────────────────────
  const res = await fetch("media.json");
  data = await res.json();

  function getSortTitle(title) {
    const articles = ["a", "an", "the"];
    const words = title.toLowerCase().split(" ");
    if (articles.includes(words[0]) && words.length > 1) {
      words.shift();
    }
    return words.join(" ");
  }

  const movieItems = data
    .filter((item) => item.type === "Movie")
    .sort((a, b) => getSortTitle(a.title).localeCompare(getSortTitle(b.title)));

  const showItems = data
    .filter((item) => item.type === "Series")
    .sort((a, b) => getSortTitle(a.title).localeCompare(getSortTitle(b.title)));

  movieItems.forEach((item) => {
    if (!item.poster_path) {
      console.warn("❌ Skipping movie with no poster_path:", item.title);
      return;
    }
    const card = createCard(item);
    movieGrid.appendChild(card);
    allCards.push(card);
  });

  showItems.forEach((item) => {
    const card = createCard(item);
    showGrid.appendChild(card);
    allCards.push(card);
  });

  function updateJumpList() {
    const typeKey = activeType === "Movie" ? "movies" : "shows";
    const currentSet = seenLetters[typeKey] || new Set();

    document.querySelectorAll(".jump-list a").forEach((link) => {
      const raw = link
        .getAttribute("href")
        .replace(`#jump-${typeKey}-`, "")
        .toUpperCase();
      const letter = raw === "" ? "#" : raw;

      if (currentSet.has(letter)) {
        link.classList.remove("disabled");
        link.removeAttribute("disabled");
        link.setAttribute("tabindex", "0");
      } else {
        link.classList.add("disabled");
        link.setAttribute("disabled", "true");
        link.setAttribute("tabindex", "-1");
      }
    });
  }

  movieCount.textContent = `${movieItems.length} titles`;
  showCount.textContent = `${showItems.length} series`;

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

  populateSelectors(data);
  const allGenres = new Set(data.flatMap((item) => item.genres || []));
  const genreColorMap = generateColorMap(allGenres);
  injectGenreStyles(genreColorMap);

  [sortSelect, genreSelect, yearSelect, searchInput].forEach((el) =>
    el.addEventListener("input", render)
  );

  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-button")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeType = btn.dataset.tab === "movies" ? "Movie" : "Series";
      document
        .getElementById("movies")
        .classList.toggle("active", activeType === "Movie");
      document
        .getElementById("shows")
        .classList.toggle("active", activeType === "Series");
      render();
      updateJumpList();
    });
  });

  window.addEventListener("scroll", () => {
    if (window.scrollY > 400) {
      scrollTopBtn.classList.add("show");
    } else {
      scrollTopBtn.classList.remove("show");
    }

    const nearBottom =
      window.innerHeight + window.scrollY >= document.body.offsetHeight - 300;
    if (nearBottom && currentIndex < filteredCards.length) {
      loadNextBatch();
    }
  });

  scrollTopBtn.addEventListener("click", () => {
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  document.querySelectorAll(".jump-list a").forEach((link) => {
    link.addEventListener("click", async (e) => {
      e.preventDefault();
      const targetId = `jump-${activeType === "Movie" ? "movies" : "shows"}-${
        link.textContent.trim().toUpperCase() || "#"
      }`;
      window.scrollTo({ top: 0 });
      await new Promise((r) => setTimeout(r, 100));

      let finalAnchor = null;

      while (currentIndex < filteredCards.length) {
        loadNextBatch();
        await new Promise((r) => setTimeout(r, 10));

        finalAnchor = document.getElementById(targetId);
        const exists = !!finalAnchor;

        if (
          exists &&
          finalAnchor.closest(".tab-content").classList.contains("active")
        ) {
          break;
        }
      }

      if (finalAnchor) {
        await new Promise((r) => setTimeout(r, 50));
        finalAnchor.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });

  render();
  updateJumpList();
});
