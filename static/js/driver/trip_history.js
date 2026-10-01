/* =========================================================
                    TRIP HISTORY PAGE
========================================================= */

document.addEventListener("DOMContentLoaded", function () {

    const menuBtn = document.getElementById("menuBtn");

    const sidebar = document.getElementById("driverSidebar");

    const overlay = document.getElementById("sidebarOverlay");


    /* =====================================================
                    OPEN SIDEBAR
    ===================================================== */

    if (menuBtn && sidebar) {

        menuBtn.addEventListener("click", function (event) {

            event.stopPropagation();

            sidebar.classList.toggle("show");

            if (overlay) {

                overlay.classList.toggle("show");

            }

        });

    }


    /* =====================================================
                    CLOSE SIDEBAR
    ===================================================== */

    function closeSidebar() {

        if (sidebar) {

            sidebar.classList.remove("show");

        }

        if (overlay) {

            overlay.classList.remove("show");

        }

    }


    /* =====================================================
                    OVERLAY CLICK
    ===================================================== */

    if (overlay) {

        overlay.addEventListener("click", function () {

            closeSidebar();

        });

    }


    /* =====================================================
                    SIDEBAR LINKS
    ===================================================== */

    if (sidebar) {

        const sidebarLinks =
            sidebar.querySelectorAll("a");

        sidebarLinks.forEach(function (link) {

            link.addEventListener("click", function () {

                if (window.innerWidth <= 991) {

                    closeSidebar();

                }

            });

        });

    }


    /* =====================================================
                    ESC KEY
    ===================================================== */

    document.addEventListener("keydown", function (event) {

        if (event.key === "Escape") {

            closeSidebar();

        }

    });


    /* =====================================================
                    DESKTOP RESIZE
    ===================================================== */

    window.addEventListener("resize", function () {

        if (window.innerWidth > 991) {

            closeSidebar();

        }

    });

});