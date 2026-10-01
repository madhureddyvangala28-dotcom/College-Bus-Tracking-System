document.addEventListener("DOMContentLoaded", function () {


    /* =====================================================
       MOBILE MENU
    ===================================================== */

    const menuBtn = document.getElementById("menuBtn");

    const sidebar =
        document.querySelector(".driver-sidebar");


    if (menuBtn && sidebar) {

        menuBtn.addEventListener("click", function () {

            sidebar.classList.toggle("show");

        });


        document.addEventListener("click", function (event) {

            const clickedInsideSidebar =
                sidebar.contains(event.target);

            const clickedMenu =
                menuBtn.contains(event.target);


            if (
                window.innerWidth <= 991 &&
                !clickedInsideSidebar &&
                !clickedMenu
            ) {

                sidebar.classList.remove("show");

            }

        });


        const links =
            sidebar.querySelectorAll("a");


        links.forEach(function (link) {

            link.addEventListener("click", function () {

                if (window.innerWidth <= 991) {

                    sidebar.classList.remove("show");

                }

            });

        });

    }


    /* =====================================================
       SHOW / HIDE PASSWORD
    ===================================================== */

    const toggleButtons =
        document.querySelectorAll(".toggle-password");


    toggleButtons.forEach(function (button) {

        button.addEventListener("click", function () {

            const targetId =
                button.getAttribute("data-target");

            const input =
                document.getElementById(targetId);

            const icon =
                button.querySelector("i");


            if (!input) {
                return;
            }


            if (input.type === "password") {

                input.type = "text";

                icon.classList.remove("fa-eye");

                icon.classList.add("fa-eye-slash");

            }

            else {

                input.type = "password";

                icon.classList.remove("fa-eye-slash");

                icon.classList.add("fa-eye");

            }

        });

    });


    /* =====================================================
       PASSWORD ELEMENTS
    ===================================================== */

    const newPassword =
        document.getElementById("new_password");

    const confirmPassword =
        document.getElementById("confirm_password");

    const strengthBar =
        document.getElementById("strengthBar");

    const strengthText =
        document.getElementById("strengthText");

    const passwordMatch =
        document.getElementById("passwordMatch");


    const ruleLength =
        document.getElementById("ruleLength");

    const ruleUpper =
        document.getElementById("ruleUpper");

    const ruleLower =
        document.getElementById("ruleLower");

    const ruleNumber =
        document.getElementById("ruleNumber");


    /* =====================================================
       PASSWORD STRENGTH
    ===================================================== */

    function checkPasswordStrength(password) {


        let score = 0;


        const hasLength =
            password.length >= 8;

        const hasUpper =
            /[A-Z]/.test(password);

        const hasLower =
            /[a-z]/.test(password);

        const hasNumber =
            /[0-9]/.test(password);


        if (hasLength) {

            score++;

            ruleLength.classList.add("valid");

        }

        else {

            ruleLength.classList.remove("valid");

        }


        if (hasUpper) {

            score++;

            ruleUpper.classList.add("valid");

        }

        else {

            ruleUpper.classList.remove("valid");

        }


        if (hasLower) {

            score++;

            ruleLower.classList.add("valid");

        }

        else {

            ruleLower.classList.remove("valid");

        }


        if (hasNumber) {

            score++;

            ruleNumber.classList.add("valid");

        }

        else {

            ruleNumber.classList.remove("valid");

        }


        if (score === 0) {

            strengthBar.style.width = "0%";

            strengthText.textContent =
                "Password strength";

        }

        else if (score === 1) {

            strengthBar.style.width = "25%";

            strengthText.textContent =
                "Weak";

        }

        else if (score === 2) {

            strengthBar.style.width = "50%";

            strengthText.textContent =
                "Fair";

        }

        else if (score === 3) {

            strengthBar.style.width = "75%";

            strengthText.textContent =
                "Good";

        }

        else {

            strengthBar.style.width = "100%";

            strengthText.textContent =
                "Strong";

        }

    }


    if (newPassword) {

        newPassword.addEventListener(
            "input",
            function () {

                checkPasswordStrength(
                    newPassword.value
                );

                checkPasswordMatch();

            }
        );

    }


    /* =====================================================
       CONFIRM PASSWORD
    ===================================================== */

    function checkPasswordMatch() {

        if (!confirmPassword) {
            return;
        }


        if (!confirmPassword.value) {

            passwordMatch.textContent = "";

            passwordMatch.className =
                "password-match";

            return;

        }


        if (
            newPassword.value ===
            confirmPassword.value
        ) {

            passwordMatch.textContent =
                "✓ Passwords match";

            passwordMatch.className =
                "password-match match";

        }

        else {

            passwordMatch.textContent =
                "✕ Passwords do not match";

            passwordMatch.className =
                "password-match no-match";

        }

    }


    if (confirmPassword) {

        confirmPassword.addEventListener(
            "input",
            checkPasswordMatch
        );

    }


    /* =====================================================
       FORM VALIDATION
    ===================================================== */

    const form =
        document.getElementById("changePasswordForm");


    if (form) {

        form.addEventListener("submit", function (event) {


            const currentPassword =
                document.getElementById(
                    "current_password"
                ).value.trim();


            const newPass =
                newPassword.value;


            const confirmPass =
                confirmPassword.value;


            if (!currentPassword) {

                event.preventDefault();

                alert(
                    "Please enter your current password."
                );

                return;

            }


            if (newPass.length < 8) {

                event.preventDefault();

                alert(
                    "New password must contain at least 8 characters."
                );

                return;

            }


            if (newPass !== confirmPass) {

                event.preventDefault();

                alert(
                    "New password and confirm password do not match."
                );

                return;

            }


            if (newPass === currentPassword) {

                event.preventDefault();

                alert(
                    "New password must be different from your current password."
                );

                return;

            }

        });

    }

});