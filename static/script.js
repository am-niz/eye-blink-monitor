document.addEventListener('DOMContentLoaded', function() {
    const blinkCount = document.getElementById('blinkCount');
    const blinkRate = document.getElementById('blinkRate');
    const startBtn = document.getElementById('startBtn');
    const stopBtn = document.getElementById('stopBtn');
    const videoFeed = document.getElementById('video_feed');
    
    let isMonitoring = false;
    let startTime;
    let updateInterval;

    const alertSound = new Audio('/static/sounds/alert.mp3');
    alertSound.volume = 0.5;  // Set volume to 50%

    videoFeed.onerror = function() {
        console.error('Video feed error');
        // Retry loading the video feed
        if (isMonitoring) {
            videoFeed.src = '/video_feed?' + new Date().getTime();
        }
    };

    startBtn.addEventListener('click', async function() {
        if (!isMonitoring) {
            try {
                const response = await fetch('/api/start');
                if (response.ok) {
                    isMonitoring = true;
                    startTime = Date.now();
                    // Add timestamp to prevent caching
                    videoFeed.src = '/video_feed?' + new Date().getTime();
                    updateStats();
                    startBtn.disabled = true;
                    stopBtn.disabled = false;
                }
            } catch (error) {
                console.error('Error starting monitoring:', error);
            }
        }
    });

    stopBtn.addEventListener('click', async function() {
        if (isMonitoring) {
            try {
                const response = await fetch('/api/stop');
                if (response.ok) {
                    isMonitoring = false;
                    clearInterval(updateInterval);
                    videoFeed.src = '';
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                }
            } catch (error) {
                console.error('Error stopping monitoring:', error);
            }
        }
    });

    function updateStats() {
        updateInterval = setInterval(async () => {
            try {
                const response = await fetch('/api/blink-data');
                const data = await response.json();
                
                blinkCount.textContent = data.blink_count;
                const elapsedMinutes = (Date.now() - startTime) / 60000;
                const rate = (data.blink_count / elapsedMinutes).toFixed(1);
                blinkRate.textContent = `${rate} per minute`;
                
                // Play sound if alert is needed
                if (data.should_alert) {
                    alertSound.play().catch(e => {
                        console.error('Error playing sound:', e);
                    });
                }
            } catch (error) {
                console.error('Error fetching blink data:', error);
            }
        }, 1000);
    }

    // Initially disable stop button
    stopBtn.disabled = true;
}); 