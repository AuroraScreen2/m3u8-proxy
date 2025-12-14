document.addEventListener('DOMContentLoaded', function() {
    const statusDiv = document.getElementById("status");
    const urlBox = document.getElementById("url_display");
    const copyBtn = document.getElementById("copy_btn");

    // Check storage
    chrome.storage.local.get(["last_stream", "timestamp"], function(result) {
        if (result.last_stream) {
            statusDiv.innerHTML = "✅ <b>STREAM FOUND!</b><br><small>Detected at: " + result.timestamp + "</small>";
            statusDiv.style.color = "green";
            
            urlBox.value = result.last_stream;
        } else {
            statusDiv.innerText = "No stream detected yet. Play the video!";
            statusDiv.style.color = "#666";
        }
    });

    // Copy Button Logic
    copyBtn.addEventListener('click', function() {
        urlBox.select();
        document.execCommand('copy');
        copyBtn.innerText = "Copied!";
        setTimeout(() => { copyBtn.innerText = "Copy Link"; }, 1000);
    });
});