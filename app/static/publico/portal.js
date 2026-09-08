document.addEventListener("DOMContentLoaded", function () {
    const toggle = document.getElementById("navToggle");
    const nav = document.getElementById("publicNav");

    if (toggle && nav) {
        toggle.addEventListener("click", function () {
            const abierto = nav.classList.toggle("open");
            toggle.setAttribute("aria-expanded", abierto ? "true" : "false");
        });

        nav.querySelectorAll("a").forEach(function (link) {
            link.addEventListener("click", function () {
                nav.classList.remove("open");
                toggle.setAttribute("aria-expanded", "false");
            });
        });
    }

    const countdown = document.querySelector("[data-countdown]");
    if (countdown) {
        const objetivo = new Date(countdown.dataset.countdown);

        function actualizarCuenta() {
            let diferencia = objetivo.getTime() - Date.now();

            if (diferencia <= 0) {
                diferencia = 0;
            }

            const dias = Math.floor(diferencia / 86400000);
            const horas = Math.floor((diferencia % 86400000) / 3600000);
            const minutos = Math.floor((diferencia % 3600000) / 60000);

            const days = countdown.querySelector("[data-days]");
            const hours = countdown.querySelector("[data-hours]");
            const minutes = countdown.querySelector("[data-minutes]");

            if (days) days.textContent = String(dias).padStart(2, "0");
            if (hours) hours.textContent = String(horas).padStart(2, "0");
            if (minutes) minutes.textContent = String(minutos).padStart(2, "0");
        }

        actualizarCuenta();
        setInterval(actualizarCuenta, 60000);
    }
});
