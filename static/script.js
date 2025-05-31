document.addEventListener("DOMContentLoaded", async () => {
  // ─────────────────────────────
  // 🔧 DOM Elements
  // ─────────────────────────────
  const sortSelect = document.getElementById("sort");
  const genreSelect = document.getElementById("genre");
  const yearSelect = document.getElementById("year");
  const sourceSelect = document.getElementById("source");
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

    activeCollectionFilter = collectionId;

    sortSelect.value = "year-asc";
    window.scrollTo({ top: 0, behavior: "smooth" });
    render();
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
    const item = data.find((d) => d.id === details.id);

    const posterEl = document.getElementById("modal-poster");
    posterEl.src = details.poster || "";
    posterEl.alt = details.title || "Poster";

    titleEl.textContent = details.title || "";
    yearEl.querySelector(".meta-text").textContent = details.year || "—";
    directorEl.textContent = details.directors
      ? `Director(s): ${details.directors}`
      : "";
    ratingEl.querySelector(".meta-text").textContent = details.rating || "—";
    const runtimeMinutes = details.runtime
      ? Math.round(parseInt(details.runtime) / 600000000)
      : null;
    runtimeEl.querySelector(".meta-text").textContent = runtimeMinutes
      ? `${runtimeMinutes} min`
      : "—";
    descriptionEl.textContent = details.description || "";
    descriptionEl.classList.remove("expanded", "needs-toggle");

    // Re-check height after rendering
    setTimeout(() => {
      if (descriptionEl.scrollHeight > descriptionEl.clientHeight + 10) {
        descriptionEl.classList.add("needs-toggle");
      }
    }, 0);

    // Attach ONE event listener
    descriptionEl.onclick = () => {
      if (descriptionEl.classList.contains("needs-toggle")) {
        descriptionEl.classList.toggle("expanded");
      }
    };

    const genres = (details.genres || "")
      .split(",")
      .filter(Boolean)
      .map(
        (g) =>
          `<span class="badge genre-${getGenreSlug(
            g.trim()
          )}">${g.trim()}</span>`
      )
      .join("");
    document.getElementById("modal-genres").innerHTML = genres;

    const collections = (item?.collections || [])
      .map(
        (c) =>
          `<button class="collection-btn" data-collection-id="${c.id}">${c.name}</button>`
      )
      .join("");
    const collectionsEl = document.getElementById("modal-collections");

    collectionsEl.innerHTML = collections;

    collectionsEl.querySelectorAll(".collection-btn").forEach((btn) => {
      btn.addEventListener("click", (e) => {
        e.stopPropagation();
        filterByCollection(btn.dataset.collectionId);
        modal.classList.remove("show");
      });
    });
    modal.classList.add("show");
  }

  closeButton.addEventListener("click", () => modal.classList.remove("show"));
  window.addEventListener("click", (e) => {
    if (e.target === modal) modal.classList.remove("show");
  });

  const seenLetters = { movies: new Set(), shows: new Set() };

  function createCard(item) {
    const card = document.createElement("div");
    const displayedGenres = item.genres.slice(0, 4);
    const extraGenres = item.genres.length > 4;
    card.dataset.id = item.id;
    card.className = `card clickable ${item.type}`;
    card.dataset.poster = item.poster_path;
    card.dataset.title = item.title;
    card.dataset.year = item.year;
    card.dataset.size = item.size / (1024 * 1024 * 1024);
    card.dataset.genres = item.genres.join(",");
    card.dataset.directors = item.directors.join(", ");
    card.dataset.rating = item.official_rating || item.community_rating;
    card.dataset.runtime = item.runtime_ticks;
    card.dataset.description = item.overview || "";
    card.dataset.source = item.source;
    card.dataset.season_count = item.season_count || 0;
    card.dataset.episode_count = item.episode_count || 0;


    const firstChar = (() => {
      const articles = ["a", "an", "the", "and", "(", ")"];
      const words = item.title.toLowerCase().split(" ");
      const index = words.length > 1 && articles.includes(words[0]) ? 1 : 0;
      const char = words[index]?.[0]?.toUpperCase() || "#";
      return /^[A-Z]$/.test(char) ? char : "#";
    })();

    const genreBadges = displayedGenres
      .map(
        (genre) =>
          `<span class="badge genre-${getGenreSlug(genre)}">${genre}</span>`
      )
      .join("") +
      (extraGenres
        ? `<span class="badge" style="background-color: #6a6a6a; color: #fff;">...</span>`
        : "");

    let anchor = "";
    const typeKey = item.type === "movie" ? "movies" : "shows";
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
      <div class="card-meta">
        <div class="meta-item"><span class="material-icons">calendar_today</span> <span class="meta-text">${
          item.year || "—"
        }</span></div>
        <div class="meta-item"><span class="material-icons">sd_storage</span> <span class="meta-text">${(
          item.size /
          (1024 * 1024 * 1024)
        ).toFixed(2)} GB</span></div>
        ${["show", "series"].includes(item.type) &&
          (parseInt(card.dataset.season_count) > 0 || parseInt(card.dataset.episode_count) > 0)
          ? `<div class="meta-item"><span class="material-icons">view_list</span> <span class="meta-text">${
              card.dataset.season_count
            } seasons • ${card.dataset.episode_count} episodes</span></div>`
          : ""
        }
      </div>
      <p style="margin-top: 0.5em; display: flex; flex-wrap: wrap; gap: 0.3em; justify-content: space-evenly;">
        ${genreBadges}
      </p>
      <div class="collection-buttons">
        ${(item.plex_collections || [])
          .map(
            (c) =>
              `<button class="collection-btn plex" data-collection-id="plex-${getGenreSlug(
                c
              )}" style="background-color: orange; color: black;">${c}</button>`
          )
          .join("")}
        ${(item.jellyfin_collections || [])
          .map(
            (c) =>
              `<button class="collection-btn jellyfin" data-collection-id="jellyfin-${getGenreSlug(
                c
              )}" style="background-color: purple;">${c}</button>`
          )
          .join("")}
      </div>
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
    const source = sourceSelect?.value || "both";

    filteredCards = allCards.filter((card) => {
      const isActive =
        (activeType === "Movie" && card.classList.contains("movie")) ||
        (activeType === "Series" && (card.classList.contains("show") || card.classList.contains("series")));
      if (!isActive) return false;

      const title = card.dataset.title.toLowerCase();
      const cardYear = card.dataset.year;
      const cardGenres = card.dataset.genres.split(",");

      if (activeCollectionFilter) {
        const id = card.dataset.id;
        const item = data.find((d) => d.id === id);
        const inCollection = (item?.collectionSlugs || []).includes(activeCollectionFilter);
        if (!inCollection) return false;
      }

      if (
        source === "jellyfin" && card.dataset.source !== "jellyfin"
      ) return false;
      if (source === "plex" && card.dataset.source !== "plex") return false;

      return (
        (!genre || cardGenres.includes(genre)) &&
        (!year || cardYear === year) &&
        (!query || title.includes(query))
      );
    });
    filteredCards.sort((a, b) => {
      const getTitle = (card) => getSortTitle(card.dataset.title);
      const aTitle = getTitle(a);
      const bTitle = getTitle(b);
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
  const raw = await res.json();

  const all = raw.all || [];
  const movies = all.filter((item) => item.type?.toLowerCase() === "movie");
  const shows = all.filter((item) =>
    ["show", "series"].includes(item.type?.toLowerCase())
  );
  const data = [...movies, ...shows];
  data.forEach((item) => {
    item.type = item.type?.toLowerCase();
    const plexSlugs = (item.plex_collections || []).map(c => `plex-${getGenreSlug(c)}`);
    const jfSlugs = (item.jellyfin_collections || []).map(c => `jellyfin-${getGenreSlug(c)}`);
    item.collectionSlugs = [...plexSlugs, ...jfSlugs];
  });
  function getSortTitle(title) {
    const articles = ["a", "an", "the"];
    const words = title.toLowerCase().split(" ");
    if (articles.includes(words[0]) && words.length > 1) {
      words.shift();
    }
    return words.join(" ");
  }

  const movieItems = data
    .filter((item) => item.type === "movie")
    .sort((a, b) => getSortTitle(a.title).localeCompare(getSortTitle(b.title)));

  const showItems = data
    .filter((item) => ["show", "series"].includes(item.type));
    
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
  sourceSelect.addEventListener("input", render);

  document.querySelectorAll(".tab-button").forEach((btn) => {
    btn.addEventListener("click", () => {
      document
        .querySelectorAll(".tab-button")
        .forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeType = btn.dataset.tab === "movies" ? "Movie" : "Series";

      sortSelect.value = "title";
      genreSelect.value = "";
      yearSelect.value = "";
      searchInput.value = "";
      activeCollectionFilter = null;

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
