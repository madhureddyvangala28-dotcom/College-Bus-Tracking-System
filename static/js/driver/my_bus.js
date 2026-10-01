/* =========================================================
   DRIVER MY BUS
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const menuBtn = document.getElementById("mobileMenuBtn");

    const sidebar = document.querySelector(".sidebar");

    const overlay = document.getElementById("sidebarOverlay");


    /* ==========================================
       OPEN MOBILE SIDEBAR
    ========================================== */

    if (menuBtn) {

        menuBtn.addEventListener("click", function () {

            sidebar.classList.toggle("open");

            overlay.classList.toggle("active");

        });

    }


    /* ==========================================
       CLOSE MOBILE SIDEBAR
    ========================================== */

    if (overlay) {

        overlay.addEventListener("click", function () {

            sidebar.classList.remove("open");

            overlay.classList.remove("active");

        });

    }


    /* ==========================================
       CLOSE SIDEBAR WHEN NAV LINK CLICKED
    ========================================== */

    const navLinks =
        document.querySelectorAll(".sidebar-nav a");

    navLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            sidebar.classList.remove("open");

            overlay.classList.remove("active");

        });

    });

});