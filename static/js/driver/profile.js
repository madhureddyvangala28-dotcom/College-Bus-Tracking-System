document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
                        MOBILE SIDEBAR
    ===================================================== */

    const menuBtn = document.getElementById("menuBtn");
    const sidebar = document.getElementById("driverSidebar");

    if (!menuBtn || !sidebar) {
        return;
    }


    /* =====================================================
                        OPEN / CLOSE
    ===================================================== */

    menuBtn.addEventListener("click", function (event) {

        event.stopPropagation();

        sidebar.classList.toggle("show");

    });


    /* =====================================================
                    CLOSE OUTSIDE SIDEBAR
    ===================================================== */

    document.addEventListener("click", function (event) {

        if (window.innerWidth > 768) {
            return;
        }

        const clickedInsideSidebar =
            sidebar.contains(event.target);

        const clickedMenuButton =
            menuBtn.contains(event.target);

        if (
            !clickedInsideSidebar &&
            !clickedMenuButton
        ) {

            sidebar.classList.remove("show");

        }

    });


    /* =====================================================
                CLOSE AFTER MENU SELECTION
    ===================================================== */

    const sidebarLinks =
        sidebar.querySelectorAll("a");

    sidebarLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 768) {

                sidebar.classList.remove("show");

            }

        });

    });


    /* =====================================================
                CLOSE SIDEBAR ON RESIZE
    ===================================================== */

    window.addEventListener("resize", function () {

        if (window.innerWidth > 768) {

            sidebar.classList.remove("show");

        }

    });

});