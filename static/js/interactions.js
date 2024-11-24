document.addEventListener('DOMContentLoaded', () => {
    // Smooth scrolling and infinite scroll
    const postsGrid = document.querySelector('.posts-grid');
    let page = 1;
    
    
    const loadMorePosts = async () => {
        const response = await fetch(`/api/posts?page=${page}`);
        const posts = await response.json();
        
        posts.forEach(post => {
            const postElement = createPostElement(post);
            postsGrid.appendChild(postElement);
        });
        
        page++;
    };
    
    // Intersection Observer for infinite scroll
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                loadMorePosts();
            }
        });
    });
    
    // Like animation
    document.querySelectorAll('.like-btn').forEach(btn => {
        btn.addEventListener('click', async (e) => {
            e.preventDefault();
            const postId = btn.closest('.post-card').dataset.postId;
            
            btn.classList.add('liked');
            const response = await fetch(`/api/posts/${postId}/like`, {
                method: 'POST'
            });
            
            if (response.ok) {
                const data = await response.json();
                btn.querySelector('span').textContent = data.likes;
            }
        });
    });
    
    // Search functionality
    const searchInput = document.querySelector('.search-input');
    let searchTimeout;
    
    searchInput.addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(async () => {
            const query = e.target.value;
            const response = await fetch(`/api/search?q=${query}`);
            const results = await response.json();
            updateSearchResults(results);
        }, 300);
    });
}); 