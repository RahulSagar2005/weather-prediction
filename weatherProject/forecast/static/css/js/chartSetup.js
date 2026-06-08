document.addEventListener('DOMContentLoaded', () => {
    // ✅ Display current date
    const dateElement = document.querySelector('.weather__location-date');
    if (dateElement) {
        const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
        const currentDate = new Date().toLocaleDateString('en-US', options);
        dateElement.textContent = ` - ${currentDate}`;
    }

    // ✅ Chart setup
    const chartElement = document.getElementById('chart');
    if (!chartElement) {
        console.error('Canvas Element not found');
        return;
    }

    const ctx = chartElement.getContext('2d');
    if (!ctx) {
        console.error('Could not get canvas context');
        return;
    }

    // ✅ Collect forecast data from HTML
    const forecastItems = document.querySelectorAll('.forecast-item');
    const temps = [];
    const times = [];

    forecastItems.forEach((item) => {
        const timeEl = item.querySelector('.forecast-time');
        const tempEl = item.querySelector('.forecast-temperatureValue');

        const time = timeEl?.textContent?.trim();
        const temp = parseFloat(tempEl?.textContent?.trim());

        if (time && !isNaN(temp)) {
            times.push(time);
            temps.push(temp);
        }
    });

    // ✅ If no valid data, provide sample fallback values
    if (temps.length === 0 || times.length === 0) {
        console.warn('Temperature or time values are missing. Using sample data.');
        times.push('6 AM', '9 AM', '12 PM', '3 PM', '6 PM');
        temps.push(22, 26, 30, 28, 24);
    }

    // ✅ Create smooth gradient for the line
    const gradient = ctx.createLinearGradient(0, 0, chartElement.clientWidth, 0);
    gradient.addColorStop(0, 'rgba(255, 107, 53, 1)');
    gradient.addColorStop(0.5, 'rgba(255, 160, 100, 1)');
    gradient.addColorStop(1, 'rgba(255, 107, 53, 1)');

    // ✅ Destroy existing chart if it exists (for hot reload or re-render)
    if (window.weatherChart) {
        window.weatherChart.destroy();
    }

    // ✅ Create new chart instance
    window.weatherChart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: times,
            datasets: [{
                label: 'Temperature (°C)',
                data: temps,
                borderColor: gradient,
                backgroundColor: 'transparent',
                borderWidth: 2.5,
                tension: 0.4,
                pointRadius: 3,
                pointHoverRadius: 5,
                pointBackgroundColor: 'rgba(255,107,53,0.8)',
                fill: false,
            }],
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true },
            },
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#555', font: { size: 12 } },
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#555', font: { size: 12 } },
                },
            },
            animation: {
                duration: 1500,
                easing: 'easeInOutQuart',
            },
            interaction: {
                intersect: false,
                mode: 'index',
            },
        },
    });
});
