async function checkWritingWithChatGPT(selectedText) {
    const apiUrl = 'https://api.openai.com/v1/chat/completions';
    const apiKey = ''; // Ensure this is a valid API key
    const system_prompt = `You are a brilliant university ESL teacher with meticulous ability to craft fluent, stylistically appropriate, standard usage of English. Make the minimum adjustments to the below text to raise it from CEFR B1 to B2, or from B2 to C1, in the areas of clarity, readability, word choice, and grammatical correctness. Make the text more concise, meaningful, logical, smoothly-flowing, and native-sounding, implementing domain-specific terminology, idiomatic expressions, and natural transitions. Wherever possible, use the words and phrases from the class notes below: 
    
    [class_notes_start]
    ${class_notes}
    [/class_notes_end]

    After the revised text, use a simple list to concisely mention the top ten phrases in the revised version that constitute an improvement over the original, and give a brief, useful, and insightful explanation into each change that can help an ESL student build a foundational understanding of English language usage. Then, estimate the CEFR and IELTS level of the original text and the revised text. Use no markdown or quotation marks. Use bullets instead of numbered lists. Refrain from making comments at the end.`;

    try {
        const response = await fetch(apiUrl, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${apiKey}`,
            },
            body: JSON.stringify({
                model: "gpt-4o",
                messages: [
                    {"role": "system", "content": `${system_prompt}`},
                    {"role": "user", "content": `${selectedText}`}],
                max_tokens: 1500,
                temperature: 0.7,
            }),
        });

        if (response.ok) {
            const data = await response.json();
            const annotatedText = data.choices[0].message.content.trim();
            return annotatedText;
        } else {
            console.error('Failed to get response from ChatGPT:', response.status, response.statusText);
            return null;
        }
    } catch (error) {
        console.error('Error during fetch:', error);
        return null;
    }
}

function createContextMenu() {
    chrome.contextMenus.removeAll(() => {
        console.log('Existing context menu items removed');
        chrome.contextMenus.create({
            id: 'check-writing',
            title: 'Check English Writing',
            contexts: ['selection'],
        }, () => {
            if (chrome.runtime.lastError) {
                console.error('Error creating context menu:', chrome.runtime.lastError);
            } else {
                console.log('Context menu item created');
            }
        });
    });
}

let class_notes = ``; // Default class notes

chrome.contextMenus.create({
    id: 'select-class-notes',
    title: 'Select Class Notes',
    contexts: ['action'],
}, () => {
    if (chrome.runtime.lastError) {
        console.error('Error creating context menu:', chrome.runtime.lastError);
    } else {
        console.log('Select Class Notes menu item created');
    }
});

chrome.contextMenus.onClicked.addListener((info, tab) => {
    if (info.menuItemId === 'select-class-notes') {
        chrome.runtime.openOptionsPage();
    }
});

chrome.contextMenus.onClicked.addListener(async function(info, tab) {
    if (info.menuItemId === 'check-writing') {
        const selectedText = info.selectionText;
        chrome.storage.local.get('class_notes', async (data) => {
            class_notes = data.class_notes || class_notes; // Use stored class notes or default
            const annotatedText = await checkWritingWithChatGPT(selectedText);

            if (annotatedText) {
                chrome.scripting.executeScript({
                    target: { tabId: tab.id },
                    files: ['content.js']
                }, () => {
                    chrome.tabs.sendMessage(tab.id, { action: 'annotateText', text: annotatedText }, (response) => {
                        if (chrome.runtime.lastError) {
                            console.error('Error sending message to content script:', chrome.runtime.lastError);
                        } else if (response.status === 'success') {
                            console.log('Message processed successfully');
                        } else {
                            console.error('Error from content script:', response.message);
                        }
                    });
                });
            } else {
                console.error('There was an error checking the text. Please try again later.');
            }
        });
    } else if (info.menuItemId === 'select-class-notes') {
        chrome.tabs.create({ url: chrome.runtime.getURL('select_notes.html') });
    }
});

createContextMenu();
console.log('Background script loaded');