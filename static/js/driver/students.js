document.addEventListener("DOMContentLoaded", function () {

    const menuBtn = document.getElementById("menuBtn");
    const sidebar = document.querySelector(".driver-sidebar");

    if (!menuBtn || !sidebar) {
        return;
    }

    menuBtn.addEventListener("click", function () {

        sidebar.classList.toggle("show");

    });


    /*
     * Close sidebar when clicking outside
     * on mobile.
     */

    document.addEventListener("click", function (event) {

        const clickedInsideSidebar =
            sidebar.contains(event.target);

        const clickedMenuButton =
            menuBtn.contains(event.target);

        if (
            window.innerWidth <= 991 &&
            !clickedInsideSidebar &&
            !clickedMenuButton
        ) {

            sidebar.classList.remove("show");

        }

    });


    /*
     * Automatically close sidebar after
     * selecting a menu item on mobile.
     */

    const sidebarLinks =
        sidebar.querySelectorAll("a");

    sidebarLinks.forEach(function (link) {

        link.addEventListener("click", function () {

            if (window.innerWidth <= 991) {

                sidebar.classList.remove("show");

            }

        });

    });

});