(function () {
     const toggleBtn = document.getElementById("themeToggle");
     const body = document.body;

     const savedTheme = localStorage.getItem("theme");

     if (savedTheme) {
         body.setAttribute("data-bs-theme", savedTheme);
     }

     function updateLabel() {
         const theme = body.getAttribute("data-bs-theme");
         toggleBtn.textContent = theme === "dark" ? "☀️ Light" : "🌙 Dark";
     }

     toggleBtn.addEventListener("click", () => {
         const current = body.getAttribute("data-bs-theme");
         const next = current === "dark" ? "light" : "dark";
         body.setAttribute("data-bs-theme", next);
         localStorage.setItem("theme", next);
         updateLabel();
     });

     updateLabel();
 })();
