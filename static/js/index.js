document.addEventListener('DOMContentLoaded', () => {
    const checkAuthentication = () => {
        const deviceToken = localStorage.getItem('deviceToken');
        const currentTime = new Date().getTime();

        if (deviceToken) {
            const tokenData = JSON.parse(deviceToken);
            if (currentTime - tokenData.timestamp < 30 * 24 * 60 * 60 * 1000) {
                // Redirect to home page if token is valid
                window.location.href = '/home';
                return;
            } else {
                // Token expired, remove it from local storage
                localStorage.removeItem('deviceToken');
            }
        }

        // Redirect to login page if no valid token
        window.location.href = '/login';
    };

    document.getElementById('get-started-btn').addEventListener('click', checkAuthentication);
});

const setDeviceToken = () => {
    const tokenData = {
        timestamp: new Date().getTime()
    };
    localStorage.setItem('deviceToken', JSON.stringify(tokenData));
};