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

  let activeType = "Movie";
  function getGenreSlug(genre) {
    return genre
      .toLowerCase()
      .replace(/\s+/g, "_")
      .replace(/&/g, "and")
      .replace(/[^\w-]/g, "");
  }

  function generateColorMap(genres) {
    const sortedGenres = [...genres].map(getGenreSlug).sort();
    const colorMap = {};
    const count = sortedGenres.length || 1;
    const step = 360 / count;

    sortedGenres.forEach((slug, index) => {
      const hue = Math.round(step * index);
      const color = `hsl(${hue}, 65%, 55%)`;
      colorMap[slug] = color;
    });

    return colorMap;
  }

  function getContrastTextColor(hsl) {
    const [h, s, l] = hsl.match(/\d+/g).map(Number);
    return l > 60 ? "#000" : "#fff";
  }

  function injectGenreStyles(colorMap) {
    const style = document.createElement("style");
    document.head.appendChild(style);
    const sheet = style.sheet;

    for (const [slug, color] of Object.entries(colorMap)) {
      const safeSelector = `.genre-${slug}`;
      const textColor = getContrastTextColor(color);
      const hsla = color.replace("hsl", "hsla").replace(")", ", 0.3)");
      const rule = `${safeSelector} {
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

  const seenLetters = { movies: new Set(), shows: new Set() };
  function createCard(item) {
    const card = document.createElement("div");
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

    function getFirstCharForJump(title) {
      const articles = ["a", "an", "the", "and", "it"];
      const words = title.toLowerCase().split(" ");
      const index = articles.includes(words[0]) ? 1 : 0;
      const char = words[index]?.[0]?.toUpperCase() || "#";
      return /^[A-Z]$/.test(char) ? char : "#";
    }

    const firstChar = getFirstCharForJump(item.title);

    const typeKey = item.type === "Movie" ? "movies" : "shows";
    let anchor = "";

    if (!seenLetters[typeKey].has(firstChar)) {
      seenLetters[typeKey].add(firstChar);
      anchor = `<a id="jump-${firstChar}"></a>`;
    }

    card.innerHTML = `
      ${anchor}
      <img src="${item.poster_path}" alt="${item.title}" loading="lazy" />
      <h3>${item.title}</h3>
      <p>${item.year || ""}</p>
      <p>${(item.size / (1024 * 1024 * 1024)).toFixed(2)} GB</p>
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
    const grid = activeType === "Movie" ? movieGrid : showGrid;
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
    const movieTab = document.getElementById("movies");
    const showTab = document.getElementById("shows");
    movieTab.classList.toggle("active", activeType === "Movie");
    showTab.classList.toggle("active", activeType === "Series");

    const grid = activeType === "Movie" ? movieGrid : showGrid;
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
      btn.classList.add("active");
      activeType = btn.dataset.tab === "movies" ? "Movie" : "Series";
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

  const allGenres = new Set(data.flatMap((item) => item.genres || []));
  const genreColorMap = generateColorMap(allGenres);
  injectGenreStyles(genreColorMap);
  document.querySelectorAll(".jump-list a").forEach((link) => {
    link.addEventListener("click", async (e) => {
      e.preventDefault();
      const targetId = link.getAttribute("href").slice(1);
      const anchor = document.getElementById(targetId);

      if (!anchor) {
        // Try to load until the anchor appears or we exhaust cards
        while (
          !document.getElementById(targetId) &&
          currentIndex < filteredCards.length
        ) {
          loadNextBatch();
          await new Promise((r) => setTimeout(r, 0)); // let DOM update
        }
      }

      const finalAnchor = document.getElementById(targetId);
      if (finalAnchor) {
        finalAnchor.scrollIntoView({ behavior: "smooth", block: "start" });
      }
    });
  });
  render();
});
