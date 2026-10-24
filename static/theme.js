
(() => {
    const validThemes = ["purple", "ocean", "forest", "rose"];
    const storageKey = "movieMagicTheme";
    const root = document.documentElement;

    function applyTheme(theme) {
        const selectedTheme = validThemes.includes(theme)
            ? theme
            : "purple";

        root.dataset.theme = selectedTheme;

        document.querySelectorAll(".theme-selector").forEach((select) => {
            select.value = selectedTheme;
        });

        return selectedTheme;
    }

    // Load the saved theme. Use purple if none has been saved.
    let savedTheme = "purple";

    try {
        savedTheme = localStorage.getItem(storageKey) || "purple";
    } catch (error) {
        // Continue using the default theme if storage is unavailable.
    }

    applyTheme(savedTheme);

    // Support selectors on every page.
    document.querySelectorAll(".theme-selector").forEach((select) => {
        select.addEventListener("change", () => {
            const selectedTheme = applyTheme(select.value);

            try {
                localStorage.setItem(storageKey, selectedTheme);
            } catch (error) {
                // The theme still works for the current page.
            }
        });
    });
})();
