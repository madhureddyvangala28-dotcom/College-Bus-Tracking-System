// ==============================
// Sticky Header
// ==============================

const stickyHeader = document.querySelector(".sticky-header");

window.addEventListener("scroll", () => {

    if (window.scrollY > 120) {

        stickyHeader.classList.add("show");

    } else {

        stickyHeader.classList.remove("show");

    }

});