document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('signin-form');  // Corrected ID
    const errorMessage = document.getElementById('error-message');  // Optional, if present

    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const identifier = document.getElementById('identifier').value.trim();
        
        try {
            const response = await fetch('/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ identifier })
            });

            const data = await response.json();

            if (response.ok) {
                window.location.href = `/login-otp?identifier=${encodeURIComponent(identifier)}`;
            } else {
                alert(data.error);
            }
        } catch (error) {
            console.error('Error:', error);
            if (errorMessage) errorMessage.textContent = 'An error occurred. Please try again.';
        }
    });
});