(() => {
  const libraryList = document.querySelector('[data-scroll-memory="library"]');
  if (!libraryList || !window.sessionStorage) {
    return;
  }

  const params = new URLSearchParams(window.location.search);
  const filterName = params.get("filter") || "all";
  const storageKey = `github-ai-radar:library-scroll:${filterName}`;

  const saveScroll = () => {
    sessionStorage.setItem(storageKey, String(libraryList.scrollTop));
  };

  const restoreScroll = () => {
    const saved = sessionStorage.getItem(storageKey);
    if (saved === null) {
      return;
    }
    const scrollTop = Number.parseInt(saved, 10);
    if (Number.isFinite(scrollTop)) {
      libraryList.scrollTop = scrollTop;
    }
  };

  requestAnimationFrame(restoreScroll);

  let scrollFrame = 0;
  libraryList.addEventListener(
    "scroll",
    () => {
      if (scrollFrame) {
        return;
      }
      scrollFrame = requestAnimationFrame(() => {
        saveScroll();
        scrollFrame = 0;
      });
    },
    { passive: true },
  );

  libraryList.addEventListener(
    "click",
    (event) => {
      if (event.target.closest(".library-link, .delete-btn")) {
        saveScroll();
      }
    },
    true,
  );
})();
