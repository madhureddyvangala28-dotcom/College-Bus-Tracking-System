document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
                       MOBILE NAVIGATION
    ====================================================== */

    const menuBtn = document.getElementById("menuBtn");

    const sidebar = document.querySelector(".driver-sidebar");


    if (menuBtn && sidebar) {

        menuBtn.addEventListener("click", function () {

            /*
             * On the Notifications page the navigation
             * is already available across the top on mobile.
             *
             * Scroll the navigation to the active item
             * when the menu button is pressed.
             */

            const activeLink =
                sidebar.querySelector("a.active");

            if (activeLink) {

                activeLink.scrollIntoView({
                    behavior: "smooth",
                    inline: "center",
                    block: "nearest"
                });

            }

        });

    }



    /* =====================================================
                    NOTIFICATION SEARCH
    ====================================================== */

    const searchInput =
        document.getElementById("searchNotification");

    const clearSearch =
        document.getElementById("clearSearch");

    const notificationCards =
        document.querySelectorAll(".notification-card");

    const noSearchResults =
        document.getElementById("noSearchResults");


    if (searchInput) {


        searchInput.addEventListener("input", function () {


            const searchValue =
                searchInput.value
                    .trim()
                    .toLowerCase();


            let visibleCount = 0;


            notificationCards.forEach(function (card) {


                const cardText =
                    card.innerText.toLowerCase();


                if (
                    searchValue === "" ||
                    cardText.includes(searchValue)
                ) {

                    card.style.display = "flex";

                    visibleCount++;

                }

                else {

                    card.style.display = "none";

                }

            });


            /* Show / hide clear button */

            if (clearSearch) {

                if (searchValue.length > 0) {

                    clearSearch.style.display = "flex";

                }

                else {

                    clearSearch.style.display = "none";

                }

            }


            /* No results */

            if (noSearchResults) {

                if (
                    searchValue !== "" &&
                    visibleCount === 0
                ) {

                    noSearchResults.style.display = "block";

                }

                else {

                    noSearchResults.style.display = "none";

                }

            }

        });

    }



    /* =====================================================
                       CLEAR SEARCH
    ====================================================== */

    if (clearSearch && searchInput) {

        clearSearch.addEventListener("click", function () {

            searchInput.value = "";

            searchInput.focus();

            notificationCards.forEach(function (card) {

                card.style.display = "flex";

            });


            clearSearch.style.display = "none";


            if (noSearchResults) {

                noSearchResults.style.display = "none";

            }

        });

    }



    /* =====================================================
                     ESCAPE SEARCH
    ====================================================== */

    document.addEventListener("keydown", function (event) {

        if (
            event.key === "Escape" &&
            searchInput
        ) {

            searchInput.value = "";

            notificationCards.forEach(function (card) {

                card.style.display = "flex";

            });


            if (clearSearch) {

                clearSearch.style.display = "none";

            }


            if (noSearchResults) {

                noSearchResults.style.display = "none";

            }

        }

    });

});