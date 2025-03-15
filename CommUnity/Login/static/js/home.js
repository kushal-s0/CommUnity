let index = 0;
const images = document.querySelectorAll(".gallery img");

function updateGallery() {
    images.forEach((img, i) => {
        img.classList.remove("active");
        if (i === index) {
            img.classList.add("active");
        }
    });
}

function nextSlide() {
    index = (index + 1) % images.length;
    updateGallery();
}

function prevSlide() {
    index = (index - 1 + images.length) % images.length;
    updateGallery();
}

document.addEventListener("DOMContentLoaded", function() {
    updateGallery(); // Initialize gallery
    setInterval(nextSlide, 3000); // Auto-slide every 3 seconds
});

// Attach event listeners to buttons
document.querySelector(".prev").addEventListener("click", prevSlide);
document.querySelector(".next").addEventListener("click", nextSlide);

document.addEventListener("DOMContentLoaded", function () {
    const userIcon = document.querySelector(".user-icon");
    const sidebar = document.querySelector(".dropdown-menu");
    const body = document.body;

    userIcon.addEventListener("click", function (event) {
        event.stopPropagation(); // Prevents closing when clicking the icon
        sidebar.classList.toggle("show"); // Show/hide sidebar
        body.classList.toggle("sidebar-active"); // Add blur effect
    });

    document.addEventListener("click", function (event) {
        if (!sidebar.contains(event.target) && !userIcon.contains(event.target)) {
            sidebar.classList.remove("show");
            body.classList.remove("sidebar-active");
        }
    });
});
