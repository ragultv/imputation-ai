let uploadedFileName = '';
        const chatArea = document.getElementById('chatArea');
        const fileInput = document.getElementById('file-input');
        const uploadBtn = document.getElementById('uploadBtn');
        const promptInput = document.getElementById('promptInput');
        const sendBtn = document.getElementById('sendBtn');
        const logoutBtn = document.getElementById('logoutBtn');


        function addMessage(content, type = 'system') {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            
            if (type === 'system') {
                // System message handling (unchanged)
                const rectangle = document.createElement('div');
                rectangle.className = 'system-message-rectangle';
                
                const logo = document.createElement('img');
                logo.src = '/static/assets/impai1.png';
                logo.alt = 'AI Logo';
                logo.className = 'message-logo';
                
                rectangle.appendChild(logo);
                
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                
                if (content.includes('<a')) {
                    contentDiv.innerHTML = content;
                } else {
                    contentDiv.textContent = content;
                }
                
                messageDiv.appendChild(rectangle);
                messageDiv.appendChild(contentDiv);
            } else {
                const contentContainer = document.createElement('div');
                contentContainer.style.cssText = `
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    width: 85%;
                    padding: 10px;
                `
                // For file upload messages
                if (content instanceof HTMLElement) {
                    const fileContainer = document.createElement('div');
                    fileContainer.style.cssText = `
                        background: white;
                        border-radius: 8px;
                        padding: 8px 16px;
                        display: flex;
                        align-items: center;
                        gap: 10px;
                    `;

                    const fileIcon = document.createElement('img');
                    fileIcon.src = '/static/assets/fileupload_icon.png';
                    fileIcon.alt = 'File';
                    fileIcon.style.cssText = `
                        width: 30px;
                        height: 30px;
                    `;

                    const fileName = document.createElement('span');
                    fileName.textContent = content.textContent || '';
                    fileName.style.cssText = `
                        color: black;
                        font-size: 14px;
                    `;

                    fileContainer.appendChild(fileIcon);
                    fileContainer.appendChild(fileName);
                    messageDiv.appendChild(fileContainer);
                } else {
                    // Regular user message
                    messageDiv.textContent = content;
                }
            }
            
            chatArea.appendChild(messageDiv);
            chatArea.scrollTop = chatArea.scrollHeight;
        }


        function typeMessage(content, type = 'system') {
            const messageDiv = document.createElement('div');
            messageDiv.className = `message ${type}-message`;
            
            if (type === 'system') {
                // Create rectangle container
                const rectangle = document.createElement('div');
                rectangle.className = 'system-message-rectangle';
                
                // Create logo image
                const logo = document.createElement('img');
                logo.src = '/static/assets/impai1.png';
                logo.alt = 'AI Logo';
                logo.className = 'message-logo';
                
                // Add logo to rectangle
                rectangle.appendChild(logo);
                
                // Create content container
                const contentDiv = document.createElement('div');
                contentDiv.className = 'message-content';
                
                // Add rectangle and content div to message
                messageDiv.appendChild(rectangle);
                messageDiv.appendChild(contentDiv);
                
                chatArea.appendChild(messageDiv);
                chatArea.scrollTop = chatArea.scrollHeight;

                // Split content into HTML and download link
                const parts = content.split(/<a\s+href="/);
                const mainContent = parts[0];
                const linkPart = parts.length > 1 ? '<a href="' + parts[1] : '';

                // Type the main content with HTML
                let index = 0;
                const typingInterval = setInterval(() => {
                    if (index < mainContent.length) {
                        contentDiv.innerHTML = mainContent.substring(0, index + 1);
                        chatArea.scrollTop = chatArea.scrollHeight;
                        index++;
                    } else {
                        // After main content is typed, add the download link if it exists
                        if (linkPart) {
                            contentDiv.innerHTML += linkPart;
                        }
                        clearInterval(typingInterval);
                    }
                }, 30);
            } else {
                // Handle user messages (unchanged)
                messageDiv.textContent = content;
                chatArea.appendChild(messageDiv);
                chatArea.scrollTop = chatArea.scrollHeight;
            }
        }

        uploadBtn.addEventListener('click', () => {
            fileInput.click();
        });

        // Update file input handler
        fileInput.addEventListener('change', async (event) => {
            const file = event.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);

            try {
                const fileMessageDiv = document.createElement('div');
                fileMessageDiv.textContent = file.name;
                addMessage(fileMessageDiv, 'user');
                
                uploadBtn.disabled = true;
                uploadBtn.classList.add('disabled');

                const response = await fetch('/upload', {
                    method: 'POST',
                    body: formData
                });

                const data = await response.json();

                if (response.ok) {
                    uploadedFileName = data.file_name;
                    typeMessage(`You have uploaded a file named "${data.file_name}". ` +` ${data.ai_suggestion}`, 'system')
                    promptInput.disabled = false;
                    sendBtn.disabled = false;
                    promptInput.focus();
                } else {
                    throw new Error(data.error || 'Upload failed');
                }
            } catch (error) {
                addMessage(` ${error.message}`);
            } finally {
                uploadBtn.disabled = false;
                uploadBtn.classList.remove('disabled');
            }
        });
        promptInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                sendBtn.click();
            }
        });

        sendBtn.addEventListener('click', async () => {
            const prompt = promptInput.value.trim();
            if (!prompt) return;

            addMessage(prompt, 'user');
            promptInput.value = '';

            try {
                sendBtn.disabled = true;
                sendBtn.classList.add('disabled');

                const response = await fetch('/impute', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        file_name: uploadedFileName,
                        prompt: prompt
                    })
                });

                const data = await response.json();

                if (response.ok) {
                    
                    const downloadLink = `<a href="/download/${data.imputed_file_name}" class="download-link" download>Download imputed file</a>`;
                    typeMessage(data.ai_response + ' ' + downloadLink, 'system');
                    //addMessage(downloadLink);
                } else {
                    throw new Error(data.error || 'Imputation failed. Please try again.');
                }
            } catch (error) {
                addMessage(`Error: ${error.message}`);
            } finally {
                sendBtn.disabled = false;
                sendBtn.classList.remove('disabled');
            }
        });

        logoutBtn.addEventListener('click', async () => {
            try {
                const response = await fetch('/logout', {
                    method: 'POST'
                });

                if (response.ok) {
                    window.location.href = '/';
                } else {
                    throw new Error('Logout failed');
                }
            } catch (error) {
                addMessage(`Error: ${error.message}`);
            }
        });

        // Initial chat with AI
        fetch('/chat', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                message: 'hi'
            })
        })
        .then(response => response.json())
        .then(data => {
            if (data.response) {
                addMessage(data.response);
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });