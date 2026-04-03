// script.js

// Contact Form Handling
function validateForm() {
    const name = document.getElementById('name').value;
    const email = document.getElementById('email').value;
    const message = document.getElementById('message').value;

    if (name === '' || email === '' || message === '') {
        alert('All fields must be filled out.');
        return false;
    }
    return true;
}

function submitForm(event) {
    event.preventDefault();
    if (validateForm()) {
        // Form submission logic here
        alert('Form submitted successfully!');
    }
}

document.getElementById('contactForm').addEventListener('submit', submitForm);

// Gallery Interactions
let currentIndex = 0;
const images = document.querySelectorAll('.gallery img');

function showImage(index) {
    images.forEach((img, i) => {
        img.style.display = i === index ? 'block' : 'none';
    });
}

function nextImage() {
    currentIndex = (currentIndex + 1) % images.length;
    showImage(currentIndex);
}

function prevImage() {
    currentIndex = (currentIndex - 1 + images.length) % images.length;
    showImage(currentIndex);
}

document.getElementById('nextButton').addEventListener('click', nextImage);
document.getElementById('prevButton').addEventListener('click', prevImage);

// Initialize gallery
showImage(currentIndex);