document.addEventListener("DOMContentLoaded", function () {

    /* =====================================================
                         SIDEBAR
    ====================================================== */

    const menuBtn = document.getElementById("menuBtn");

    const sidebar = document.getElementById("driverSidebar");


    /* Create mobile overlay */

    const overlay = document.createElement("div");

    overlay.className = "sidebar-overlay";

    document.body.appendChild(overlay);


    /* =====================================================
                       OPEN SIDEBAR
    ====================================================== */

    if (menuBtn && sidebar) {

        menuBtn.addEventListener("click", function () {

            sidebar.classList.toggle("show");

            overlay.classList.toggle("show");

        });

    }


    /* =====================================================
                     CLOSE SIDEBAR
    ====================================================== */

    overlay.addEventListener("click", function () {

        sidebar.classList.remove("show");

        overlay.classList.remove("show");

    });


    /* =====================================================
                CLOSE AFTER MENU SELECTION
    ====================================================== */

    const sidebarLinks =
        sidebar.querySelectorAll("a");

    sidebarLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 768) {

                sidebar.classList.remove("show");

                overlay.classList.remove("show");

            }

        });

    });


    /* =====================================================
                     CHANGE PASSWORD
    ====================================================== */

    const changePasswordBtn =
        document.getElementById("changePasswordBtn");

    if (changePasswordBtn) {

        changePasswordBtn.addEventListener(
            "click",
            function () {

                /*
                 * No unwanted popup or fake password
                 * functionality is added here.
                 *
                 * Connect this button to the real
                 * change-password route when that
                 * feature is implemented.
                 */

                alert("Change Password feature will be available here.");

            }
        );

    }


    /* =====================================================
                    NOTIFICATIONS TOGGLE
    ====================================================== */

    const notificationToggle =
        document.getElementById("notificationToggle");

    if (notificationToggle) {

        notificationToggle.addEventListener(
            "change",
            function () {

                if (this.checked) {

                    console.log(
                        "Driver notifications enabled."
                    );

                } else {

                    console.log(
                        "Driver notifications disabled."
                    );

                }

            }
        );

    }


    /* =====================================================
                         LOGOUT
    ====================================================== */

    const logoutBtn =
        document.getElementById("logoutBtn");

    if (logoutBtn) {

        logoutBtn.addEventListener(
            "click",
            function (event) {

                const confirmLogout =
                    confirm(
                        "Are you sure you want to logout?"
                    );

                if (!confirmLogout) {

                    event.preventDefault();

                }

            }
        );

    }


    /* =====================================================
                    WINDOW RESIZE
    ====================================================== */

    window.addEventListener("resize", function () {

        if (window.innerWidth > 768) {

            sidebar.classList.remove("show");

            overlay.classList.remove("show");

        }

    });

});