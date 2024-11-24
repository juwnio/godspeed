document.addEventListener('DOMContentLoaded', function() {
    // Search functionality
    const searchInput = document.getElementById('search-input');
    const searchResults = document.getElementById('search-results');
    let searchTimeout;

    searchInput?.addEventListener('input', function() {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            const query = this.value;
            if (query.length >= 2) {
                performSearch(query);
            } else {
                searchResults.innerHTML = '';
            }
        }, 300);
    });

    // Like functionality
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', async function() {
            const postId = this.dataset.postId;
            try {
                const response = await fetch(`/post/${postId}/like`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    }
                });
                const data = await response.json();
                this.querySelector('.like-count').textContent = data.likes;
                this.classList.add('liked');
            } catch (error) {
                console.error('Error liking post:', error);
            }
        });
    });

    // Profile tabs
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabContents = document.querySelectorAll('.tab-content');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const tabId = this.dataset.tab;
            
            tabBtns.forEach(b => b.classList.remove('active'));
            tabContents.forEach(c => c.classList.add('hidden'));
            
            this.classList.add('active');
            document.getElementById(tabId).classList.remove('hidden');
        });
    });

    // Image preview
    const imageInput = document.getElementById('cover-image');
    const imagePreview = document.getElementById('image-preview');

    imageInput?.addEventListener('change', function() {
        const file = this.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = function(e) {
                imagePreview.innerHTML = `<img src="${e.target.result}" class="preview-image">`;
            };
            reader.readAsDataURL(file);
        }
    });
});

async function performSearch(query) {
    try {
        const response = await fetch(`/api/search?q=${encodeURIComponent(query)}`);
        const results = await response.json();
        displaySearchResults(results);
    } catch (error) {
        console.error('Error performing search:', error);
    }
}

function displaySearchResults(results) {
    const searchResults = document.getElementById('search-results');
    if (!results.length) {
        searchResults.innerHTML = '<div class="no-results">No results found</div>';
        return;
    }

    const resultsHTML = results.map(result => `
        <div class="search-result-item">
            <h3>${result.title}</h3>
            <p>${result.content}</p>
            <div class="result-meta">
                <span>By ${result.author}</span>
                <span>${result.date}</span>
            </div>
        </div>
    `).join('');

    searchResults.innerHTML = resultsHTML;
}

function toggleComments(postId) {
    const commentsSection = document.getElementById(`comments-${postId}`);
    commentsSection.classList.toggle('hidden');
}

async function submitComment(event, postId) {
    event.preventDefault();
    const form = event.target;
    const content = form.content.value;

    try {
        const response = await fetch(`/post/${postId}/comment`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/form-data'
            },
            body: new FormData(form)
        });

        const data = await response.json();
        
        if (data.success) {
            // Add the new comment to the comments list
            const commentsList = document.querySelector(`#comments-${postId} .comments-list`);
            const newComment = document.createElement('div');
            newComment.className = 'comment';
            newComment.innerHTML = `
                <div class="comment-header">
                    <span class="comment-author">${data.comment.author}</span>
                    <span class="comment-date">${data.comment.date}</span>
                </div>
                <p class="comment-content">${data.comment.content}</p>
            `;
            commentsList.appendChild(newComment);

            // Update comment count
            const commentCount = document.querySelector(`[data-post-id="${postId}"] .comment-count`);
            commentCount.textContent = parseInt(commentCount.textContent) + 1;

            // Clear the form
            form.reset();
        }
    } catch (error) {
        console.error('Error submitting comment:', error);
    }
} 