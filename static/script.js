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

    // ─────────────────────────────
    // 🔁 Load Data First
    // ─────────────────────────────
    const res = await fetch("media.json");
    const raw = await res.json();
    const all = raw.all || [];
    const data = all.map(item => ({
        ...item,
        type: item.type?.toLowerCase(),
        collectionSlugs: [
            ...(item.plex_collections || []).map(c => `plex-${getGenreSlug(c)}`),
            ...(item.jellyfin_collections || []).map(c => `jellyfin-${getGenreSlug(c)}`)
        ]
    }));

    const availableLibraries = [...new Set(data.map(item => item.library))];
    // Always the lowercase slug (matches gridMap keys, tab data-tab
    // attributes, and jump-list anchor ids) - never the display-cased
    // library name.
    let activeLibrary = availableLibraries[0]?.toLowerCase();

    const gridMap = {};
    availableLibraries.forEach(lib => {
        const gridId = `${lib.toLowerCase()}-grid`;
        const gridEl = document.getElementById(gridId);
        if (gridEl) gridMap[lib.toLowerCase()] = gridEl;
    });


    // ─────────────────────────────
    // 📦 App State
    // ─────────────────────────────
    const CARDS_PER_BATCH = 200;
    let currentIndex = 0;
    let filteredCards = [];
    let allCards = [];
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

    function generateColorMap(genres) {
        // Muted, deterministic per-genre hue - distinct enough to tell
        // genres apart at a glance without turning the grid into a rainbow.
        // Same low saturation/lightness for every genre keeps them reading
        // as one coherent badge system rather than each fighting for
        // attention.
        const sortedGenres = [...genres].map(getGenreSlug).sort();
        const colorMap = {};
        const step = 360 / sortedGenres.length;

        sortedGenres.forEach((slug, i) => {
            const hue = Math.round(step * i);
            colorMap[slug] = hue;
        });

        return colorMap;
    }

    function injectGenreStyles(colorMap) {
        const style = document.createElement("style");
        document.head.appendChild(style);
        const sheet = style.sheet;

        for (const [slug, hue] of Object.entries(colorMap)) {
            const rule = `.genre-${slug} {
        background-color: hsla(${hue}, 38%, 42%, 0.22);
        border-color: hsla(${hue}, 45%, 65%, 0.4);
        color: hsl(${hue}, 55%, 78%);
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
        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
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
        directorEl.textContent = details.directors ?
            `Director(s): ${details.directors}` :
            "";
        ratingEl.querySelector(".meta-text").textContent = details.rating || "—";
        const runtimeMinutes = details.runtime ? parseInt(details.runtime) : null;
        runtimeEl.querySelector(".meta-text").textContent = runtimeMinutes ?
            `${runtimeMinutes} min` :
            "—";
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

        const collections = [
            ...(item?.plex_collections || []).map(
                (c) => `<button class="collection-btn plex" data-collection-id="plex-${getGenreSlug(c)}">${c}</button>`
            ),
            ...(item?.jellyfin_collections || []).map(
                (c) => `<button class="collection-btn jellyfin" data-collection-id="jellyfin-${getGenreSlug(c)}">${c}</button>`
            ),
        ].join("");
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

    // Jump-list letter buckets, one per library (not per movie/show type -
    // this used to be a hardcoded {movies, shows} pair, which only worked
    // when every library was literally named "Movies" or "Shows". A
    // library named anything else (e.g. "TV Shows", "Theatre") fell
    // through every type check in render() and rendered as empty.
    const seenLetters = {};

    function createCard(item) {
        const card = document.createElement("div");
        const displayedGenres = item.genres.slice(0, 4);
        const extraGenres = item.genres.length > 4;
        card.dataset.library = item.library;
        card.dataset.id = item.id;
        card.className = `card clickable ${
          item.type === "movie" ? "movie" : "show"
        }`;
        card.dataset.poster = item.poster_path;
        card.dataset.title = item.title;
        card.dataset.year = item.year;
        card.dataset.size = item.size / (1024 * 1024 * 1024);
        card.dataset.genres = item.genres.join(",");
        card.dataset.directors = item.directors.join(", ");
        card.dataset.rating = item.official_rating || item.community_rating;
        card.dataset.runtime = item.runtime_minutes;
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
            (extraGenres ?
                `<span class="badge badge-more">+${item.genres.length - 4}</span>` :
                "");

        let anchor = "";
        const librarySlug = item.library.toLowerCase();
        seenLetters[librarySlug] = seenLetters[librarySlug] || new Set();
        const isFirstCard =
            allCards.filter((c) => c.dataset.library?.toLowerCase() === librarySlug)
            .length === 0;

        if (
            !seenLetters[librarySlug].has(firstChar) ||
            (firstChar === "#" && isFirstCard)
        ) {
            seenLetters[librarySlug].add(firstChar);
            anchor = `<a id="jump-${librarySlug}-${firstChar}"></a>`;
        }

        const isShow = ["show", "series"].includes(item.type);

        card.innerHTML = `
      ${anchor}
      <div class="card-poster">
        <img src="${item.poster_path}" alt="${item.title}" loading="lazy" />
        <span class="source-dots" aria-hidden="true">
          ${(item.source || []).map((s) => `<span class="source-dot ${s}" title="${s === "plex" ? "Plex" : "Jellyfin"}"></span>`).join("")}
        </span>
      </div>
      <div class="card-body">
        <h3>${item.title}</h3>
        <div class="card-meta">
          <span class="meta-item">${item.year || "—"}</span>
          <span class="meta-item">${(item.size / (1024 * 1024 * 1024)).toFixed(2)} GB</span>
          ${isShow
            ? `<span class="meta-item">${item.season_count || 0} season${item.season_count === 1 ? "" : "s"} · ${item.episode_count || 0} ep</span>`
            : ""
          }
        </div>
        <div class="card-genres">
          ${genreBadges}
        </div>
        <div class="collection-buttons">
          ${(item.plex_collections || [])
            .map(
              (c) =>
                `<button class="collection-btn plex" data-collection-id="plex-${getGenreSlug(c)}">${c}</button>`
            )
            .join("")}
          ${(item.jellyfin_collections || [])
            .map(
              (c) =>
                `<button class="collection-btn jellyfin" data-collection-id="jellyfin-${getGenreSlug(c)}">${c}</button>`
            )
            .join("")}
        </div>
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
        const nextBatch = filteredCards.slice(
            currentIndex,
            currentIndex + CARDS_PER_BATCH
        );
        nextBatch.forEach((card) => {
            gridMap[activeLibrary.toLowerCase()].appendChild(card);
        });
        currentIndex += CARDS_PER_BATCH;
    }

    function render() {
        const genre = genreSelect.value;
        const year = yearSelect.value;
        const query = searchInput.value.toLowerCase().trim();
        const sort = sortSelect.value;
        const grid = gridMap[activeLibrary.toLowerCase()];
        if (!grid) {
            console.warn(`❌ No grid found for library "${activeLibrary}"`);
            return;
        }

        filteredCards = allCards.filter((card) => {
            if (card.dataset.library?.toLowerCase() !== activeLibrary.toLowerCase()) return false;

            const title = card.dataset.title.toLowerCase();
            const cardYear = card.dataset.year;
            const cardGenres = card.dataset.genres.split(",");

            if (activeCollectionFilter) {
                const id = card.dataset.id;
                const item = data.find((d) => d.id === id);
                const inCollection = (item?.collectionSlugs || []).includes(activeCollectionFilter);
                if (!inCollection) return false;
            }

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

        const librarySlug = activeLibrary.toLowerCase();

        grid.innerHTML = "";
        document.querySelectorAll(".jump-list a").forEach((link) => {
            const letter = link.textContent.trim().toUpperCase();
            link.setAttribute("href", `#jump-${librarySlug}-${letter || "#"}`);
        });

        seenLetters[librarySlug] = new Set();

        filteredCards.forEach((card) => {
            const title = card.dataset.title;

            const articles = ["a", "an", "the"];
            const words = title.toLowerCase().split(" ");
            const index = words.length > 1 && articles.includes(words[0]) ? 1 : 0;
            const char = words[index]?.[0]?.toUpperCase() || "#";
            const firstChar = /^[A-Z]$/.test(char) ? char : "#";

            seenLetters[librarySlug].add(firstChar);
        });
        loadNextBatch();
    }

    // ─────────────────────────────
    // 🔁 Data Setup
    // ─────────────────────────────

    const movies = all.filter((item) => item.type?.toLowerCase() === "movie");
    const shows = all.filter((item) => ["show", "series"].includes(item.type?.toLowerCase()));
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

    data.forEach((item) => {
        if (!item.poster_path) return;
        const card = createCard(item);
        allCards.push(card);

        const lib = item.library?.toLowerCase();
        if (gridMap[lib]) {
            gridMap[lib].appendChild(card);
        }
    });


    function updateJumpList() {
        const librarySlug = activeLibrary.toLowerCase();
        const currentSet = seenLetters[librarySlug] || new Set();

        document.querySelectorAll(".jump-list a").forEach((link) => {
            const raw = link
                .getAttribute("href")
                .replace(`#jump-${librarySlug}-`, "")
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
    sortSelect.addEventListener("change", () => render());
    genreSelect.addEventListener("change", () => render());
    yearSelect.addEventListener("change", () => render());
    searchInput.addEventListener("input", () => render());
    const allGenres = new Set(data.flatMap((item) => item.genres || []));
    const genreColorMap = generateColorMap(allGenres);
    injectGenreStyles(genreColorMap);

    document.querySelectorAll(".tab-button").forEach((btn) => {
        btn.addEventListener("click", () => {
            document.querySelectorAll(".tab-button").forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");

            const rawTab = btn.dataset.tab;
            // rawTab is already the lowercase slug used everywhere else
            // (grid ids, jump-list anchors, dataset.library comparisons) -
            // no need to reconstruct a display-cased name nobody reads.
            activeLibrary = rawTab;

            document.querySelectorAll(".tab-content").forEach((tab) => tab.classList.remove("active"));

            const activeContent = document.getElementById(rawTab); // Lowercase
            if (activeContent) activeContent.classList.add("active");

            sortSelect.value = "title";
            genreSelect.value = "";
            yearSelect.value = "";
            searchInput.value = "";
            activeCollectionFilter = null;

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
        window.scrollTo({
            top: 0,
            behavior: "smooth"
        });
    });

    document.querySelectorAll(".jump-list a").forEach((link) => {
        link.addEventListener("click", async (e) => {
            e.preventDefault();
            const targetId = `jump-${activeLibrary.toLowerCase()}-${
        link.textContent.trim().toUpperCase() || "#"
      }`;
            window.scrollTo({
                top: 0
            });
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
                finalAnchor.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            }
        });
    });

    render();
    updateJumpList();
});