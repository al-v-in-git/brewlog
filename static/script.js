function initReveal() {
    document.querySelectorAll(".panel, .hero-card, .favorite-card, .feature-tile").forEach((element, index) => {
        element.classList.add("reveal");
        element.style.animationDelay = `${index * 70}ms`;
    });
}

function initThemeToggle() {
    const themeToggle = document.getElementById("themeToggle");
    const storedTheme = window.localStorage.getItem("brewlog-theme");

    if (storedTheme === "dark") {
        document.body.classList.add("dark-mode");
    }

    if (!themeToggle) {
        return;
    }

    themeToggle.textContent = document.body.classList.contains("dark-mode") ? "Light" : "Dark";

    themeToggle.addEventListener("click", () => {
        document.body.classList.toggle("dark-mode");
        const mode = document.body.classList.contains("dark-mode") ? "dark" : "light";
        window.localStorage.setItem("brewlog-theme", mode);
        themeToggle.textContent = mode === "dark" ? "Light" : "Dark";
    });
}

function initBrewForm() {
    const brewForm = document.querySelector("[data-brew-form]");
    if (!brewForm) {
        return;
    }

    brewForm.addEventListener("submit", (event) => {
        const rating = Number(document.getElementById("rating").value);
        if (rating < 1 || rating > 5) {
            event.preventDefault();
            window.alert("Rating must be between 1 and 5.");
        }
    });

    const imageInput = document.getElementById("brew_image");
    const preview = document.getElementById("imagePreview");

    if (imageInput && preview) {
        imageInput.addEventListener("change", () => {
            const [file] = imageInput.files;
            if (!file) {
                preview.src = "";
                preview.classList.add("hidden");
                return;
            }

            preview.src = URL.createObjectURL(file);
            preview.classList.remove("hidden");
        });
    }
}

function initCalculator() {
    const coffeeInput = document.querySelector("[data-coffee-input]");
    const waterOutput = document.querySelector("[data-water-output]");
    const resultText = document.querySelector(".calculator-result");

    if (!coffeeInput || !waterOutput || !resultText) {
        return;
    }

    const updateResult = () => {
        const coffeeGrams = Number(coffeeInput.value || 20);
        const waterAmount = coffeeGrams * 15;
        waterOutput.value = `${waterAmount} ml`;
        resultText.textContent = `${coffeeGrams}g coffee -> ${waterAmount}ml water`;
    };

    coffeeInput.addEventListener("input", updateResult);
    updateResult();
}

function initHistoryFilters() {
    const controls = document.querySelector("[data-history-controls]");
    const rows = Array.from(document.querySelectorAll("[data-history-row]"));
    const sortControl = document.querySelector("[data-sort-control]");

    if (!controls || rows.length === 0) {
        return;
    }

    const searchInput = document.getElementById("search");
    const methodFilter = document.getElementById("methodFilter");
    const ratingFilter = document.getElementById("ratingFilter");
    const tableBody = document.querySelector("[data-history-table] tbody");

    const applyClientFilters = () => {
        const searchValue = (searchInput.value || "").trim().toLowerCase();
        const methodValue = (methodFilter.value || "").trim().toLowerCase();
        const ratingValue = (ratingFilter.value || "").trim();

        rows.forEach((row) => {
            const matchesSearch =
                !searchValue ||
                row.dataset.bean.includes(searchValue) ||
                row.dataset.notes.includes(searchValue);
            const matchesMethod = !methodValue || row.dataset.method === methodValue;
            const matchesRating = !ratingValue || row.dataset.rating === ratingValue;

            row.style.display = matchesSearch && matchesMethod && matchesRating ? "" : "none";
        });
    };

    const sortRows = () => {
        if (!tableBody || !sortControl) {
            return;
        }

        const sortValue = sortControl.value;
        const sortedRows = [...rows].sort((left, right) => {
            if (sortValue === "bean_asc") {
                return left.dataset.bean.localeCompare(right.dataset.bean);
            }
            if (sortValue === "method_asc") {
                return left.dataset.method.localeCompare(right.dataset.method);
            }
            if (sortValue === "rating_desc") {
                return Number(right.dataset.rating) - Number(left.dataset.rating);
            }
            if (sortValue === "rating_asc") {
                return Number(left.dataset.rating) - Number(right.dataset.rating);
            }
            return 0;
        });

        sortedRows.forEach((row) => tableBody.appendChild(row));
    };

    [searchInput, methodFilter, ratingFilter].forEach((element) => {
        if (element) {
            element.addEventListener("input", applyClientFilters);
            element.addEventListener("change", applyClientFilters);
        }
    });

    if (sortControl) {
        sortControl.addEventListener("change", sortRows);
    }

    applyClientFilters();
    sortRows();
}

function initAnalyticsCharts() {
    if (!window.analyticsPayload || typeof Chart === "undefined") {
        return;
    }

    const methodCanvas = document.getElementById("methodChart");
    const ratingCanvas = document.getElementById("ratingChart");

    if (methodCanvas) {
        new Chart(methodCanvas, {
            type: "bar",
            data: {
                labels: window.analyticsPayload.methodLabels,
                datasets: [
                    {
                        label: "Brews",
                        data: window.analyticsPayload.methodValues,
                        backgroundColor: ["#b3541e", "#d1783c", "#7d3610", "#f0b387"],
                        borderRadius: 10,
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { display: false },
                },
            },
        });
    }

    if (ratingCanvas) {
        new Chart(ratingCanvas, {
            type: "doughnut",
            data: {
                labels: window.analyticsPayload.ratingLabels,
                datasets: [
                    {
                        data: window.analyticsPayload.ratingValues,
                        backgroundColor: ["#ffcf8b", "#f0a95d", "#d1783c", "#b3541e", "#7d3610"],
                    },
                ],
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        position: "bottom",
                    },
                },
            },
        });
    }
}

document.addEventListener("DOMContentLoaded", () => {
    initReveal();
    initThemeToggle();
    initBrewForm();
    initCalculator();
    initHistoryFilters();
    initAnalyticsCharts();
});
