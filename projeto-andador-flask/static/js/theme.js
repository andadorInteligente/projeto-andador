document.addEventListener("DOMContentLoaded", function () {
    const body = document.body;
    const themeButton = document.getElementById("theme-toggle");

    const savedTheme = localStorage.getItem("theme");

    if (savedTheme === "dark") {
        body.classList.add("dark-theme");
        if (themeButton) {
            themeButton.innerHTML = "☀️ Tema Claro";
        }
    }

    if (themeButton) {
        themeButton.addEventListener("click", function () {
            body.classList.toggle("dark-theme");

            if (body.classList.contains("dark-theme")) {
                localStorage.setItem("theme", "dark");
                themeButton.innerHTML = "☀️ Tema Claro";
            } else {
                localStorage.setItem("theme", "light");
                themeButton.innerHTML = "🌙 Tema Escuro";
            }
        });
    }
});