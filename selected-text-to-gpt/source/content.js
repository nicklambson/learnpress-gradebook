console.log('Content script loaded');

chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    if (request.action === 'annotateText') {
        const annotatedText = request.text;
        navigator.clipboard.writeText(annotatedText).then(() => {
            console.log('Annotated text copied to clipboard');
            const audioUrl = chrome.runtime.getURL('notification.wav');
            const audio = new Audio(audioUrl);
            audio.play().then(() => {
                console.log('Notification sound played');
                sendResponse({status: 'success'});
            }).catch(err => {
                console.error('Failed to play sound: ', err);
                sendResponse({status: 'error', message: 'Failed to play sound'});
            });
        }).catch(err => {
            console.error('Failed to copy text: ', err);
            sendResponse({status: 'error', message: 'Failed to copy text'});
        });
        // Return true to indicate that the response will be sent asynchronously
        return true;
    }
});