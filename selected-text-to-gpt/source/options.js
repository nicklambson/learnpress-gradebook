document.getElementById('uploadButton').addEventListener('click', () => {
    console.log('Upload button clicked');
    const fileInput = document.getElementById('fileInput');
    const file = fileInput.files[0];

    if (file) {
        console.log('File selected:', file.name);
        const reader = new FileReader();
        reader.onload = function(event) {
            console.log('FileReader onload event triggered');
            const classNotes = event.target.result;
            console.log('Class notes read from file:', classNotes);
            chrome.storage.local.set({ class_notes: classNotes }, () => {
                if (chrome.runtime.lastError) {
                    console.error('Error setting class notes in storage:', chrome.runtime.lastError);
                } else {
                    console.log('Class notes updated in storage');
                    const status = document.getElementById('status');
                    status.textContent = 'Class notes updated successfully!';
                    setTimeout(() => {
                        status.textContent = '';
                    }, 750);
                }
            });
        };
        reader.onerror = function(event) {
            console.error('FileReader error:', event.target.error);
        };
        reader.readAsText(file);
    } else {
        console.log('No file selected');
        alert('Please select a file first.');
    }
});

document.addEventListener('DOMContentLoaded', () => {
    console.log('Options page loaded');
    if (chrome.storage && chrome.storage.local) {
        chrome.storage.local.get('class_notes', (data) => {
            if (chrome.runtime.lastError) {
                console.error('Error getting class notes from storage:', chrome.runtime.lastError);
            } else {
                if (data.class_notes) {
                    console.log('Current class notes:', data.class_notes);
                } else {
                    console.log('No class notes found in storage');
                }
            }
        });
    } else {
        console.error('chrome.storage is undefined');
    }
});