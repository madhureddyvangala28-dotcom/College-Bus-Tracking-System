/* ==========================================
   GREETING
========================================== */

const greeting = document.getElementById("greeting");

if (greeting) {

    const hour = new Date().getHours();

    if (hour < 12) {

        greeting.innerHTML = "Good Morning 👋";

    } else if (hour < 17) {

        greeting.innerHTML = "Good Afternoon ☀️";

    } else {

        greeting.innerHTML = "Good Evening 🌙";

    }

}


/* ==========================================
   PROFILE MENU
========================================== */

const profileBtn = document.getElementById("profileBtn");
const profileMenu = document.getElementById("profileMenu");

if (profileBtn && profileMenu) {

    // Open / Close menu
    profileBtn.addEventListener("click", function (e) {

        e.stopPropagation();

        profileMenu.classList.toggle("active");

    });

    // Prevent closing when clicking inside menu
    profileMenu.addEventListener("click", function (e) {

        e.stopPropagation();

    });

    // Close menu when clicking outside
    document.addEventListener("click", function () {

        profileMenu.classList.remove("active");

    });

    // Close with Escape key
    document.addEventListener("keydown", function (e) {

        if (e.key === "Escape") {

            profileMenu.classList.remove("active");

        }

    });

}