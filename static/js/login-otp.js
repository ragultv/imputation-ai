document.addEventListener('DOMContentLoaded', function () {
    const otpForm = document.querySelector('form');
    const resendLink = document.querySelector('.resend-link');
    const resendTimer = document.getElementById('resend-timer');
    const countdownSpan = document.getElementById('countdown');
    const otpInputs = document.querySelectorAll('.otp-input');
    const urlParams = new URLSearchParams(window.location.search);
    const identifier = urlParams.get('identifier');
    let countdownInterval;

    // OTP input focus handling
    otpInputs.forEach((input, index) => {
        input.addEventListener('input', (e) => {
            if (e.target.value && index < otpInputs.length - 1) {
                otpInputs[index + 1].focus();
            }
        });

        input.addEventListener('keydown', (e) => {
            if (e.key === 'Backspace' && !e.target.value && index > 0) {
                otpInputs[index - 1].focus();
            }
        });
    });

    // Form submission for OTP verification
    otpForm.addEventListener('submit', async (e) => {
        e.preventDefault();

        const otp = Array.from(otpInputs).map(input => input.value).join('');
        try {
            const response = await fetch('/verify-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ identifier, otp }),
            });

            const data = await response.json();

            if (response.ok) {
                window.location.href = '/'; // Redirect to home page
            } else {
                alert(data.error);
            }
        } catch (error) {
            alert('An error occurred. Please try again.');
        }
    });

    // Resend OTP functionality
    resendLink.addEventListener('click', async (e) => {
        e.preventDefault();

        try {
            const response = await fetch('/resend-otp', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ identifier }),
            });

            const data = await response.json();

            if (response.ok) {
                
                startResendTimer(30); // Start 30-second cooldown
            } else {
                alert(data.error || 'Failed to resend OTP. Please try again.');
            }
        } catch (error) {
            alert('An error occurred while resending OTP. Please try again.');
        }
    });

    // Start a countdown timer for Resend OTP
    function startResendTimer(seconds) {
        resendLink.style.pointerEvents = 'none';
        resendTimer.style.display = 'inline';
        countdownSpan.textContent = seconds;

        countdownInterval = setInterval(() => {
            seconds--;
            countdownSpan.textContent = seconds;

            if (seconds <= 0) {
                clearInterval(countdownInterval);
                resendTimer.style.display = 'none';
                resendLink.style.pointerEvents = 'auto';
            }
        }, 1000);
    }
});