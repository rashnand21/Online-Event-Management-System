document.addEventListener("DOMContentLoaded", function () {

    // 1. Auto-hide flash messages after 5 seconds
    document.querySelectorAll(".alert").forEach(function (alertBox) {
        setTimeout(function () {
            alertBox.classList.remove("show");
            setTimeout(function () { alertBox.remove(); }, 300);
        }, 5000);
    });

    // 2. Offer codes always in capital letters
    document.querySelectorAll("input[name='offer_code']").forEach(function (input) {
        input.addEventListener("input", function () {
            input.value = input.value.toUpperCase();
        });
    });

    // 3. Phone and contact fields accept digits only
    document.querySelectorAll("input[name='phone'], input[name='contact_no']").forEach(function (input) {
        input.addEventListener("input", function () {
            input.value = input.value.replace(/[^0-9]/g, "");
        });
    });

    // 4. Check that end time is after start time (schedule form)
    var startTime = document.querySelector("input[name='start_time']");
    var endTime = document.querySelector("input[name='end_time']");
    if (startTime && endTime) {
        var form = startTime.closest("form");
        form.addEventListener("submit", function (e) {
            if (endTime.value <= startTime.value) {
                e.preventDefault();
                alert("End time must be after start time.");
            }
        });
    }

    // 5. Check that valid-to date is after valid-from date (offer form)
    var validFrom = document.querySelector("input[name='valid_from']");
    var validTo = document.querySelector("input[name='valid_to']");
    if (validFrom && validTo) {
        validFrom.addEventListener("change", function () {
            validTo.min = validFrom.value;
        });
        validFrom.closest("form").addEventListener("submit", function (e) {
            if (validTo.value < validFrom.value) {
                e.preventDefault();
                alert("Valid-to date must be after valid-from date.");
            }
        });
    }

    // 6. Check that available-to date is after available-from date (hall form)
    var availFrom = document.querySelector("input[name='available_from']");
    var availTo = document.querySelector("input[name='available_to']");
    if (availFrom && availTo) {
        availFrom.addEventListener("change", function () {
            availTo.min = availFrom.value;
        });
        availFrom.closest("form").addEventListener("submit", function (e) {
            if (availTo.value < availFrom.value) {
                e.preventDefault();
                alert("Available-to date must be after available-from date.");
            }
        });
    }

    // 7. Disable the submit button after the first click (stops double booking)
    document.querySelectorAll("form[method='POST']").forEach(function (form) {
        form.addEventListener("submit", function () {
            var btn = form.querySelector("button[type='submit']");
            if (btn && !form.hasAttribute("onsubmit")) {
                setTimeout(function () {
                    btn.disabled = true;
                    btn.innerText = "Please wait...";
                }, 10);
            }
        });
    });

});