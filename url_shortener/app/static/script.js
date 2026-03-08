async function shortenUrl() {
    const originalUrl = document.getElementById('originalUrl').value;
    const resultArea = document.getElementById('resultArea');
    const errorMsg = document.getElementById('errorMsg');
    const shortLink = document.getElementById('shortLink');

    // сброс
    resultArea.classList.add('hidden');
    errorMsg.classList.add('hidden');

    if (!originalUrl) return;

    try {
        const response = await fetch('/links/shorten', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                original_url: originalUrl
            })
        });

        if (!response.ok) {
            throw new Error('Error processing request');
        }

        const data = await response.json();
        
        // формируем полную ссылку (текущий хост + короткий код)
        const fullShortUrl = `${window.location.origin}/${data.short_code}`;
        
        shortLink.href = fullShortUrl;
        shortLink.textContent = fullShortUrl;
        resultArea.classList.remove('hidden');

    } catch (error) {
        errorMsg.textContent = "Something went wrong. Please check the URL.";
        errorMsg.classList.remove('hidden');
    }
}

function copyLink() {
    const link = document.getElementById('shortLink');
    navigator.clipboard.writeText(link.href);
    alert("Copied to clipboard!");
}