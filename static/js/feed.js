const APP_USER = JSON.parse(document.body.dataset.user);
const APP_VERSION = document.body.dataset.version;

function validateTextLength(text, maxLength, fieldName) {
    if (text.length > maxLength) {
        showToast(`${fieldName} cannot exceed ${maxLength} characters! (${text.length}/${maxLength})`, 'error');
        return false;
    }
    return true;
}

function validateRequired(value, fieldName) {
    if (!value || value.trim() === '') {
        showToast(`${fieldName} cannot be empty!`, 'error');
        return false;
    }
    return true;
}

let posts = [];
let allPosts = [];
let currentFilter = 'all';
let currentPostId = null;
let editingPostId = null;
let deleteTarget = null;
let deleteType = null;
let createMediaFiles = [];
let editMediaFiles = [];
let isSearching = false;
let searchTimeout = null;

document.addEventListener('DOMContentLoaded', () => {
    fetchPosts();
    fetchNotifications();
    setupFilterButtons();
    setupModalCloseOnOutsideClick();
});

async function fetchPosts() {
    try {
        const response = await fetch(`/api/posts?userId=${APP_USER.id}&wordId=${CURRENT_WORD_ID}`);
        posts = await response.json();
        allPosts = [...posts];
        renderPosts();
    } catch (error) {
        console.error('Error fetching posts:', error);
        showToast('Error loading posts');
    }
}

function renderPosts() {
    const feed = document.getElementById('postsFeed');
    const filteredPosts = posts.filter(post => {
        if (currentFilter === 'all') return true;
        if (currentFilter === 'youth') return post.type === 'youth';
        if (currentFilter === 'senior') return post.type === 'senior';
        return true;
    });

    feed.innerHTML = filteredPosts.map(post => createPostCard(post)).join('');
}

function createPostCard(post) {
    const isOwner = post.userId === APP_USER.id;
    const avatarClass = post.type === 'youth' ? 'matt_avatar-youth' : 'matt_avatar-senior';
    const badgeClass = post.type === 'youth' ? 'matt_badge-youth' : 'matt_badge-senior';
    const badgeText = post.type === 'youth' ? 'Youth' : 'Senior';

    let mediaHtml = '';
    if (post.media && post.media.length > 0) {
        const mediaCount = Math.min(post.media.length, 4);
        mediaHtml = `<div class="matt_post-media-grid matt_ media-${mediaCount}">`;
        post.media.slice(0, 4).forEach(m => {
            if (m.type === 'video') {
                mediaHtml += `<div class="matt_post-media-item"><video src="${m.url}" muted></video></div>`;
            } else {
                mediaHtml += `<div class="matt_post-media-item"><img src="${m.url}" alt="Post media"></div>`;
            }
        });
        mediaHtml += '</div>';
    }

    let pollHtml = '';
    if (post.poll) {
        pollHtml = renderPoll(post.poll, post.id);
    }

    return `
        <div class="matt_post-card" data-post-id="${post.id}" data-type="${post.type}" onclick="openPostDetail('${post.id}')">
            <div class="matt_post-header" onclick="event.stopPropagation()">
                <div class="matt_avatar matt_${avatarClass}">${post.initials}</div>
                <div class="matt_post-author-info">
                    <div class="matt_post-author-row">
                        <span class="matt_post-author-name">${post.author}</span>
                        <span class="matt_post-badge matt_ ${badgeClass}">${badgeText}</span>
                    </div>
                    <div class="matt_post-author-age">${post.age} years old</div>
                </div>
                ${isOwner ? `
                    <div class="matt_post-actions-menu">
                        <button class="matt_btn-more" onclick="togglePostMenu(event, '${post.id}')">⋯</button>
                        <div class="matt_dropdown-menu-custom" id="menu-${post.id}">
                            <div class="matt_dropdown-item-custom" onclick="event.stopPropagation(); openEditModal('${post.id}')">
                                <span>✏️</span> Edit
                            </div>
                            <div class="matt_dropdown-item-custom matt_danger" onclick="event.stopPropagation(); confirmDeletePost('${post.id}')">
                                <span>🗑️</span> Delete
                            </div>
                        </div>
                    </div>
                ` : ''}
            </div>
            <div class="matt_post-content">
                ${post.text ? `<div class="matt_post-text">${escapeHtml(post.text)}</div>` : ''}
                ${mediaHtml}
                ${pollHtml}
            </div>
            <div class="matt_post-footer" onclick="event.stopPropagation()">
                <div class="matt_post-stats">
                    <div class="matt_post-stat ${post.liked ? 'matt_liked' : ''}" onclick="toggleLike('${post.id}')">
                        <span>❤️</span>
                        <span>${post.likes}</span>
                    </div>
                    <div class="matt_post-stat">
                        <span>💬</span>
                        <span>${post.comments.length}</span>
                    </div>
                </div>
                <div class="matt_post-time">${post.time}</div>
            </div>
        </div>
    `;
}

function renderPoll(poll, postId) {
    const hasVoted = poll.userVote !== null;
    
    const optionsHtml = poll.options.map(opt => {
        const isSelected = poll.userVote === opt.id;
        const selectedClass = isSelected ? 'matt_selected' : '';
        
        if (hasVoted) {
            return `
                <div class="matt_poll-option ${selectedClass}" data-option-id="${opt.id}">
                    <div class="matt_poll-option-bar" style="width: ${opt.percentage}%"></div>
                    <span class="matt_poll-option-text">${escapeHtml(opt.text)}</span>
                    <span class="matt_poll-option-percent">${opt.percentage}%</span>
                </div>
            `;
        } else {
            return `
                <div class="matt_poll-option votable" data-option-id="${opt.id}" onclick="event.stopPropagation(); votePoll('${poll.id}', '${opt.id}', '${postId}')">
                    <span class="matt_poll-option-text">${escapeHtml(opt.text)}</span>
                </div>
            `;
        }
    }).join('');
    
    return `
        <div class="matt_poll-container" data-poll-id="${poll.id}">
            <div class="matt_poll-question">📊 ${escapeHtml(poll.question)}</div>
            <div class="matt_poll-options">${optionsHtml}</div>
            <div class="matt_poll-total">${poll.totalVotes} votes</div>
        </div>
    `;
}

async function votePoll(pollId, optionId, postId) {
    try {
        const response = await fetch(`/api/polls/${pollId}/vote`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: APP_USER.id, optionId: optionId })
        });
        
        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error voting', 'error');
            return;
        }
        
        const result = await response.json();
        const post = posts.find(p => p.id === postId);
        if (post && post.poll) {
            post.poll.options = result.options;
            post.poll.totalVotes = result.totalVotes;
            post.poll.userVote = result.userVote;
            renderPosts();
            if (currentPostId === postId) {
                renderModalPost(post);
            }
            showToast('Vote recorded! 🗳️', 'success');
        }
    } catch (error) {
        console.error('Error voting:', error);
        showToast('Error voting');
    }
}

function setupFilterButtons() {
    document.querySelectorAll('.matt_filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.matt_filter-btn').forEach(b => b.classList.remove('matt_active'));
            btn.classList.add('matt_active');
            currentFilter = btn.dataset.filter;
            renderPosts();
        });
    });
}

function handleSearchKeyup(event) {
    const query = event.target.value.trim();
    
    if (searchTimeout) {
        clearTimeout(searchTimeout);
    }
    
    const clearBtn = document.getElementById('searchClearBtn');
    if (query.length > 0) {
        clearBtn.classList.add('matt_show');
    } else {
        clearBtn.classList.remove('matt_show');
        if (isSearching) {
            clearSearch();
        }
        return;
    }
    
    if (query.length < 2) return;
    
    searchTimeout = setTimeout(() => {
        performSearch(query);
    }, 300);
}

async function performSearch(query) {
    try {
        const response = await fetch(`/api/posts/search?q=${encodeURIComponent(query)}&userId=${APP_USER.id}&wordId=${CURRENT_WORD_ID}`);
        const results = await response.json();
        
        posts = results;
        isSearching = true;
        
        const header = document.getElementById('searchResultsHeader');
        const text = document.getElementById('searchResultsText');
        text.textContent = `Found ${results.length} result${results.length !== 1 ? 's' : ''} for "${query}"`;
        header.classList.add('matt_show');
        
        renderPosts();
    } catch (error) {
        console.error('Error searching:', error);
        showToast('Error searching posts');
    }
}

function clearSearch() {
    document.getElementById('searchInput').value = '';
    document.getElementById('searchClearBtn').classList.remove('matt_show');
    document.getElementById('searchResultsHeader').classList.remove('matt_show');
    
    posts = [...allPosts];
    isSearching = false;
    renderPosts();
}

async function fetchNotifications() {
    try {
        const response = await fetch(`/api/notifications?userId=${APP_USER.id}`);
        const data = await response.json();
        renderNotifications(data.notifications);
        updateNotificationBadge(data.unreadCount);
    } catch (error) {
        console.error('Error fetching notifications:', error);
    }
}

function renderNotifications(notifications) {
    const list = document.getElementById('notificationList');
    
    if (notifications.length === 0) {
        list.innerHTML = '<div class="matt_notification-empty">No notifications yet</div>';
        return;
    }
    
    list.innerHTML = notifications.map(n => {
        let icon = '💬';
        if (n.type === 'post_like') icon = '❤️';
        else if (n.type === 'comment_like') icon = '💗';
        else if (n.type === 'poll_vote') icon = '🗳️';
        
        const unreadClass = n.read ? '' : 'matt_unread';
        return `
            <div class="matt_notification-item ${unreadClass}" onclick="handleNotificationClick(${n.id}, '${n.postId}')">
                <span class="matt_notification-icon">${icon}</span>
                <div class="matt_notification-content">
                    <div class="matt_notification-message">${escapeHtml(n.message)}</div>
                    <div class="matt_notification-time">${n.time}</div>
                </div>
            </div>
        `;
    }).join('');
}

function updateNotificationBadge(count) {
    const badge = document.getElementById('notificationBadge');
    badge.textContent = count > 9 ? '9+' : count;
    if (count > 0) {
        badge.classList.add('matt_show');
    } else {
        badge.classList.remove('matt_show');
    }
}

function toggleNotifications() {
    const dropdown = document.getElementById('notificationDropdown');
    dropdown.classList.toggle('matt_show');
}

async function handleNotificationClick(notificationId, postId) {
    try {
        await fetch(`/api/notifications/${notificationId}/read`, { method: 'POST' });
        
        document.getElementById('notificationDropdown').classList.remove('matt_show');
        
        if (postId) {
            openPostDetail(postId);
        }
        
        fetchNotifications();
    } catch (error) {
        console.error('Error marking notification read:', error);
    }
}

async function markAllNotificationsRead() {
    try {
        await fetch('/api/notifications/read-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: APP_USER.id })
        });
        fetchNotifications();
        showToast('All notifications marked as read', 'success');
    } catch (error) {
        console.error('Error marking all read:', error);
    }
}

async function clearAllNotifications() {
    try {
        await fetch('/api/notifications/clear-all', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: APP_USER.id })
        });
        fetchNotifications();
        showToast('All notifications cleared', 'success');
    } catch (error) {
        console.error('Error clearing notifications:', error);
    }
}

document.addEventListener('click', (e) => {
    const wrapper = document.getElementById('notificationWrapper');
    if (wrapper && !wrapper.contains(e.target)) {
        document.getElementById('notificationDropdown').classList.remove('matt_show');
    }
});

function togglePostMenu(event, postId) {
    event.stopPropagation();
    const menu = document.getElementById(`menu-${postId}`);
    document.querySelectorAll('.matt_dropdown-menu-custom').forEach(m => {
        if (m !== menu) m.classList.remove('matt_show');
    });
    menu.classList.toggle('matt_show');
}

document.addEventListener('click', () => {
    document.querySelectorAll('.matt_dropdown-menu-custom').forEach(m => m.classList.remove('matt_show'));
});

async function toggleLike(postId) {
    try {
        const response = await fetch(`/api/posts/${postId}/like`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: APP_USER.id })
        });
        const result = await response.json();
        
        const post = posts.find(p => p.id === postId);
        if (post) {
            post.likes = result.likes;
            post.liked = result.liked;
            renderPosts();
            if (currentPostId === postId) {
                renderModalPost(post);
            }
        }
    } catch (error) {
        console.error('Error toggling like:', error);
    }
}

function openPostDetail(postId) {
    const post = posts.find(p => p.id === postId);
    if (!post) return;
    
    currentPostId = postId;
    renderModalPost(post);
    renderComments(post);
    document.getElementById('postDetailModal').classList.add('matt_show');
    document.body.style.overflow = 'hidden';
}

function renderModalPost(post) {
    const isOwner = post.userId === APP_USER.id;
    const avatarClass = post.type === 'youth' ? 'matt_avatar-youth' : 'matt_avatar-senior';
    const badgeClass = post.type === 'youth' ? 'matt_badge-youth' : 'matt_badge-senior';
    const badgeText = post.type === 'youth' ? 'Youth' : 'Senior';

    let mediaHtml = '';
    if (post.media && post.media.length > 0) {
        const mediaCount = Math.min(post.media.length, 4);
        mediaHtml = `<div class="matt_post-media-grid matt_ media-${mediaCount}">`;
        post.media.slice(0, 4).forEach(m => {
            if (m.type === 'video') {
                mediaHtml += `<div class="matt_post-media-item"><video src="${m.url}" controls></video></div>`;
            } else {
                mediaHtml += `<div class="matt_post-media-item"><img src="${m.url}" alt="Post media"></div>`;
            }
        });
        mediaHtml += '</div>';
    }

    let pollHtml = '';
    if (post.poll) {
        pollHtml = renderPoll(post.poll, post.id);
    }

    document.getElementById('modalPostContent').innerHTML = `
        <div class="matt_post-header">
            <div class="matt_avatar matt_${avatarClass}">${post.initials}</div>
            <div class="matt_post-author-info">
                <div class="matt_post-author-row">
                    <span class="matt_post-author-name">${post.author}</span>
                    <span class="matt_post-badge matt_ ${badgeClass}">${badgeText}</span>
                </div>
                <div class="matt_post-author-age">${post.age} years old</div>
            </div>
            ${isOwner ? `
                <div class="matt_post-actions-menu">
                    <button class="matt_btn-more" onclick="togglePostMenu(event, '${post.id}-modal')">⋯</button>
                    <div class="matt_dropdown-menu-custom" id="menu-${post.id}-modal">
                        <div class="matt_dropdown-item-custom" onclick="event.stopPropagation(); openEditModal('${post.id}')">
                            <span>✏️</span> Edit
                        </div>
                        <div class="matt_dropdown-item-custom matt_danger" onclick="event.stopPropagation(); confirmDeletePost('${post.id}')">
                            <span>🗑️</span> Delete
                        </div>
                    </div>
                </div>
            ` : ''}
        </div>
        <div class="matt_post-content">
            ${post.text ? `<div class="matt_post-text" style="-webkit-line-clamp: unset;">${escapeHtml(post.text)}</div>` : ''}
            ${mediaHtml}
            ${pollHtml}
        </div>
        <div class="matt_post-footer">
            <div class="matt_post-stats">
                <div class="matt_post-stat ${post.liked ? 'matt_liked' : ''}" onclick="toggleLike('${post.id}')">
                    <span>❤️</span>
                    <span>${post.likes}</span>
                </div>
                <div class="matt_post-stat">
                    <span>💬</span>
                    <span>${post.comments.length}</span>
                </div>
            </div>
            <div class="matt_post-time">${post.time}</div>
        </div>
    `;
}

function renderComments(post) {
    const commentsList = document.getElementById('commentsList');
    
    if (post.comments.length === 0) {
        commentsList.innerHTML = '<div class="matt_no-comments">No comments yet. Be the first to comment! 💬</div>';
        return;
    }

    commentsList.innerHTML = post.comments.map(comment => {
        const isOwner = comment.userId === APP_USER.id;
        const avatarClass = comment.type === 'youth' ? 'matt_avatar-youth' : 'matt_avatar-senior';
        const likesCount = comment.likes || 0;
        const likedClass = comment.liked ? 'liked' : '';
        
        return `
            <div class="matt_comment-item" data-comment-id="${comment.id}">
                <div class="matt_comment-avatar matt_ ${avatarClass}">${comment.initials}</div>
                <div class="matt_comment-content">
                    <div class="matt_comment-header">
                        <div class="matt_comment-header-left">
                            <span class="matt_comment-author">${comment.author}</span>
                            <span class="matt_comment-time">${comment.time}</span>
                        </div>
                        <div class="matt_comment-header-right">
                            <button class="matt_comment-like-btn ${likedClass}" onclick="event.stopPropagation(); toggleCommentLike('${comment.id}')" title="Like">
                                ❤️ <span id="comment-likes-${comment.id}">${likesCount}</span>
                            </button>
                            ${isOwner ? `
                                <button class="matt_btn-comment-action" onclick="event.stopPropagation(); editComment('${comment.id}')" title="Edit">✏️</button>
                                <button class="matt_btn-comment-action matt_danger" onclick="event.stopPropagation(); confirmDeleteComment('${comment.id}')" title="Delete">🗑️</button>
                            ` : ''}
                        </div>
                    </div>
                    <div class="matt_comment-text" id="comment-text-${comment.id}">${escapeHtml(comment.text)}</div>
                    <div class="matt_comment-edit-form" id="comment-edit-${comment.id}">
                        <input type="text" class="matt_comment-edit-input" id="comment-input-${comment.id}" value="${escapeHtml(comment.text)}">
                        <div class="matt_comment-edit-actions">
                            <button type="button" class="matt_btn-sm matt_btn-cancel" onclick="cancelEditComment('${comment.id}')">Cancel</button>
                            <button type="button" class="matt_btn-sm matt_btn-save" onclick="saveEditComment('${comment.id}')">Save</button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function closePostDetail() {
    document.getElementById('postDetailModal').classList.remove('matt_show');
    document.body.style.overflow = '';
    currentPostId = null;
}

async function addComment(event) {
    event.preventDefault();
    const input = document.getElementById('commentInput');
    const text = input.value.trim();
    
    if (!validateRequired(text, 'Comment')) return;
    if (!validateTextLength(text, 1000, 'Comment')) return;
    
    if (!currentPostId) return;

    try {
        const response = await fetch(`/api/posts/${currentPostId}/comments`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: APP_USER.id,
                author: APP_USER.name,
                initials: APP_USER.initials,
                type: APP_USER.type,
                text: text
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error posting comment', 'error');
            return;
        }
        
        const newComment = await response.json();
        const post = posts.find(p => p.id === currentPostId);
        if (post) {
            post.comments.unshift(newComment);
            input.value = '';
            renderComments(post);
            renderPosts();
            showToast('Comment posted! 💬', 'success');
        }
    } catch (error) {
        console.error('Error adding comment:', error);
        showToast('Error posting comment');
    }
}

function editComment(commentId) {
    document.getElementById(`comment-text-${commentId}`).classList.add('matt_editing');
    document.getElementById(`comment-edit-${commentId}`).classList.add('matt_show');
    document.getElementById(`comment-input-${commentId}`).focus();
}

function cancelEditComment(commentId) {
    document.getElementById(`comment-text-${commentId}`).classList.remove('matt_editing');
    document.getElementById(`comment-edit-${commentId}`).classList.remove('matt_show');
}

async function saveEditComment(commentId) {
    const input = document.getElementById(`comment-input-${commentId}`);
    const newText = input.value.trim();
    
    if (!validateRequired(newText, 'Comment')) return;
    if (!validateTextLength(newText, 1000, 'Comment')) return;

    try {
        const response = await fetch(`/api/posts/${currentPostId}/comments/${commentId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ text: newText })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error updating comment', 'error');
            return;
        }

        const post = posts.find(p => p.id === currentPostId);
        if (post) {
            const comment = post.comments.find(c => c.id === commentId);
            if (comment) {
                comment.text = newText;
                renderComments(post);
                showToast('Comment updated! ✅', 'success');
            }
        }
    } catch (error) {
        console.error('Error updating comment:', error);
        showToast('Error updating comment');
    }
}

function confirmDeleteComment(commentId) {
    deleteTarget = commentId;
    deleteType = 'comment';
    document.getElementById('confirmMessage').textContent = 'Delete this comment?';
    document.getElementById('confirmModal').classList.add('matt_show');
}

async function toggleCommentLike(commentId) {
    if (!currentPostId) return;
    
    const post = posts.find(p => p.id === currentPostId);
    if (!post) return;
    
    const comment = post.comments.find(c => c.id === commentId);
    if (!comment) return;
    
    try {
        const response = await fetch(`/api/posts/${currentPostId}/comments/${commentId}/like`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ userId: APP_USER.id })
        });
        
        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error liking comment', 'error');
            return;
        }
        
        const result = await response.json();
        comment.likes = result.likes;
        comment.liked = result.liked;
        
        const likesSpan = document.getElementById(`comment-likes-${commentId}`);
        if (likesSpan) {
            likesSpan.textContent = result.likes;
        }
        
        const likeBtn = likesSpan?.closest('.comment-like-btn');
        if (likeBtn) {
            if (result.liked) {
                likeBtn.classList.add('matt_liked');
            } else {
                likeBtn.classList.remove('matt_liked');
            }
        }
    } catch (error) {
        console.error('Error liking comment:', error);
        showToast('Error liking comment');
    }
}

function openCreateModal() {
    createMediaFiles = [];
    document.getElementById('createPostText').value = '';
    document.getElementById('createMediaPreview').innerHTML = '';
    document.getElementById('createMediaPreview').classList.remove('matt_has-media');
    document.getElementById('addPollCheckbox').checked = false;
    document.getElementById('pollForm').classList.remove('matt_show');
    document.getElementById('pollQuestion').value = '';
    document.getElementById('pollOptionsInputs').innerHTML = `
        <input type="text" class="matt_poll-option-input" placeholder="Option 1">
        <input type="text" class="matt_poll-option-input" placeholder="Option 2">
    `;
    document.getElementById('createPostModal').classList.add('matt_show');
    document.body.style.overflow = 'hidden';
}

function closeCreateModal() {
    document.getElementById('createPostModal').classList.remove('matt_show');
    document.body.style.overflow = '';
}

function togglePollForm() {
    const checkbox = document.getElementById('addPollCheckbox');
    const pollForm = document.getElementById('pollForm');
    if (checkbox.checked) {
        pollForm.classList.add('matt_show');
    } else {
        pollForm.classList.remove('matt_show');
    }
}

function addPollOption() {
    const container = document.getElementById('pollOptionsInputs');
    const optionCount = container.querySelectorAll('.matt_poll-option-input').length;
    if (optionCount >= 4) {
        showToast('Maximum 4 options allowed', 'error');
        return;
    }
    const input = document.createElement('input');
    input.type = 'text';
    input.className = 'matt_poll-option-input';
    input.placeholder = `Option ${optionCount + 1}`;
    container.appendChild(input);
}

function previewMedia(event, mode) {
    const files = Array.from(event.target.files);
    const mediaFiles = mode === 'create' ? createMediaFiles : editMediaFiles;

    files.forEach(file => {
        if (mediaFiles.length >= 4) return;
        
        const reader = new FileReader();
        reader.onload = (e) => {
            mediaFiles.push({
                type: file.type.startsWith('video') ? 'video' : 'image',
                url: e.target.result,
                file: file
            });
            renderMediaPreview(mode);
        };
        reader.readAsDataURL(file);
    });

    event.target.value = '';
}

function renderMediaPreview(mode) {
    const mediaFiles = mode === 'create' ? createMediaFiles : editMediaFiles;
    const container = document.getElementById(mode === 'create' ? 'createMediaPreview' : 'editMediaPreview');

    if (mediaFiles.length === 0) {
        container.innerHTML = '';
        container.classList.remove('matt_has-media');
        return;
    }

    container.classList.add('matt_has-media');
    container.innerHTML = mediaFiles.map((m, index) => `
        <div class="matt_media-preview-item">
            <img src="${m.url}" alt="Preview">
            <button type="button" class="matt_media-preview-remove" onclick="removeMediaPreview(${index}, '${mode}')">×</button>
        </div>
    `).join('');
}

function removeMediaPreview(index, mode) {
    if (mode === 'create') {
        createMediaFiles.splice(index, 1);
    } else {
        editMediaFiles.splice(index, 1);
    }
    renderMediaPreview(mode);
}

async function createPost(event) {
    event.preventDefault();
    const text = document.getElementById('createPostText').value.trim();
    const hasPoll = document.getElementById('addPollCheckbox').checked;
    
    let pollData = null;
    if (hasPoll) {
        const question = document.getElementById('pollQuestion').value.trim();
        const optionInputs = document.querySelectorAll('#pollOptionsInputs .matt_poll-option-input');
        const options = Array.from(optionInputs).map(input => input.value.trim()).filter(opt => opt);
        
        if (!question) {
            showToast('Please enter a poll question!', 'error');
            return;
        }
        if (options.length < 2) {
            showToast('Please add at least 2 poll options!', 'error');
            return;
        }
        
        pollData = { question, options };
    }
    
    if (!text && createMediaFiles.length === 0 && !pollData) {
        showToast('Please add some text, media, or a poll!');
        return;
    }
    
    if (text && !validateTextLength(text, 1000, 'Post')) return;

    try {
        const response = await fetch('/api/posts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                userId: APP_USER.id,
                author: APP_USER.name,
                initials: APP_USER.initials,
                age: APP_USER.age,
                type: APP_USER.type,
                text: text,
                wordId: CURRENT_WORD_ID,
                media: createMediaFiles.map(m => ({ type: m.type, url: m.url })),
                poll: pollData
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error creating post', 'error');
            return;
        }

        const newPost = await response.json();
        newPost.liked = false;
        posts.unshift(newPost);
        renderPosts();
        closeCreateModal();
        
        const message = APP_VERSION === 'elderly' ? 'Story shared! 🎉' : 'Post created! 🎉';
        showToast(message, 'success');
    } catch (error) {
        console.error('Error creating post:', error);
        showToast('Error creating post');
    }
}

function openEditModal(postId) {
    const post = posts.find(p => p.id === postId);
    if (!post) return;

    editingPostId = postId;
    editMediaFiles = post.media ? [...post.media] : [];
    document.getElementById('editPostText').value = post.text || '';
    renderMediaPreview('edit');
    
    closePostDetail();
    document.querySelectorAll('.matt_dropdown-menu-custom').forEach(m => m.classList.remove('matt_show'));
    document.getElementById('editPostModal').classList.add('matt_show');
    document.body.style.overflow = 'hidden';
}

function closeEditModal() {
    document.getElementById('editPostModal').classList.remove('matt_show');
    document.body.style.overflow = '';
    editingPostId = null;
}

async function saveEditPost(event) {
    event.preventDefault();
    const text = document.getElementById('editPostText').value.trim();
    
    if (!text && editMediaFiles.length === 0) {
        showToast('Please add some text or media!');
        return;
    }
    
    if (text && !validateTextLength(text, 1000, 'Post')) return;

    try {
        const response = await fetch(`/api/posts/${editingPostId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                text: text,
                media: editMediaFiles.map(m => ({ type: m.type, url: m.url }))
            })
        });

        if (!response.ok) {
            const error = await response.json();
            showToast(error.error || 'Error updating post', 'error');
            return;
        }

        const post = posts.find(p => p.id === editingPostId);
        if (post) {
            post.text = text;
            post.media = editMediaFiles.map(m => ({ type: m.type, url: m.url }));
            renderPosts();
            closeEditModal();
            
            const message = APP_VERSION === 'elderly' ? 'Story updated! ✅' : 'Post updated! ✅';
            showToast(message, 'success');
        }
    } catch (error) {
        console.error('Error updating post:', error);
        showToast('Error updating post');
    }
}

function confirmDeletePost(postId) {
    deleteTarget = postId;
    deleteType = 'post';
    const message = APP_VERSION === 'elderly' 
        ? 'Delete this story? All comments will also be removed.'
        : 'Delete this post? All comments will also be removed.';
    document.getElementById('confirmMessage').textContent = message;
    document.getElementById('confirmModal').classList.add('matt_show');
    document.querySelectorAll('.matt_dropdown-menu-custom').forEach(m => m.classList.remove('matt_show'));
}

function closeConfirmModal() {
    document.getElementById('confirmModal').classList.remove('matt_show');
    deleteTarget = null;
    deleteType = null;
}

async function executeDelete() {
    const targetId = deleteTarget;
    const type = deleteType;
    
    closeConfirmModal();
    
    if (type === 'post') {
        if (currentPostId === targetId) {
            closePostDetail();
        }
        
        try {
            await fetch(`/api/posts/${targetId}`, { method: 'DELETE' });
            
            const postCard = document.querySelector(`.matt_posts-feed [data-post-id="${targetId}"]`);
            if (postCard) {
                postCard.classList.add('matt_fade-out');
                setTimeout(() => {
                    posts = posts.filter(p => p.id !== targetId);
                    renderPosts();
                    const message = APP_VERSION === 'elderly' ? 'Story deleted' : 'Post deleted';
                    showToast(message);
                }, 300);
            } else {
                posts = posts.filter(p => p.id !== targetId);
                renderPosts();
                const message = APP_VERSION === 'elderly' ? 'Story deleted' : 'Post deleted';
                showToast(message);
            }
        } catch (error) {
            console.error('Error deleting post:', error);
            showToast('Error deleting post');
        }
        
    } else if (type === 'comment') {
        const post = posts.find(p => p.id === currentPostId);
        if (post) {
            try {
                await fetch(`/api/posts/${currentPostId}/comments/${targetId}`, { method: 'DELETE' });
                
                const commentItem = document.querySelector(`[data-comment-id="${targetId}"]`);
                if (commentItem) {
                    commentItem.classList.add('matt_fade-out');
                    setTimeout(() => {
                        post.comments = post.comments.filter(c => c.id !== targetId);
                        renderComments(post);
                        renderPosts();
                        showToast('Comment deleted');
                    }, 300);
                } else {
                    post.comments = post.comments.filter(c => c.id !== targetId);
                    renderComments(post);
                    renderPosts();
                    showToast('Comment deleted');
                }
            } catch (error) {
                console.error('Error deleting comment:', error);
                showToast('Error deleting comment');
            }
        }
    }
}

function setupModalCloseOnOutsideClick() {
    ['postDetailModal', 'createPostModal', 'editPostModal', 'confirmModal'].forEach(id => {
        document.getElementById(id).addEventListener('click', (e) => {
            if (e.target.classList.contains('matt_modal-overlay')) {
                if (id === 'postDetailModal') closePostDetail();
                else if (id === 'createPostModal') closeCreateModal();
                else if (id === 'editPostModal') closeEditModal();
                else if (id === 'confirmModal') closeConfirmModal();
            }
        });
    });
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        if (document.getElementById('confirmModal').classList.contains('matt_show')) {
            closeConfirmModal();
        } else if (document.getElementById('editPostModal').classList.contains('matt_show')) {
            closeEditModal();
        } else if (document.getElementById('createPostModal').classList.contains('matt_show')) {
            closeCreateModal();
        } else if (document.getElementById('postDetailModal').classList.contains('matt_show')) {
            closePostDetail();
        }
    }
});

function showToast(message, type = 'default') {
    const toast = document.getElementById('toast');
    toast.innerHTML = `
        <span class="matt_toast-message">${escapeHtml(message)}</span>
        <button class="matt_toast-close" onclick="hideToast()">×</button>
    `;
    toast.className = 'matt_toast ' + type;
    toast.classList.add('matt_show');
    if (window.toastTimeout) clearTimeout(window.toastTimeout);
    window.toastTimeout = setTimeout(() => toast.classList.remove('matt_show'), 5000);
}

function hideToast() {
    const toast = document.getElementById('toast');
    toast.classList.remove('matt_show');
    if (window.toastTimeout) clearTimeout(window.toastTimeout);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function changeWord(wordId) {
    const currentUrl = new URL(window.location.href);
    currentUrl.searchParams.set('word_id', wordId);
    window.location.href = currentUrl.toString();
}

function toggleWordDropdown(event) {
    event.stopPropagation();
    const dropdown = document.getElementById('wordSelectorDropdown');
    dropdown.classList.toggle('matt_show');
}

function selectWord(wordId) {
    document.getElementById('wordSelectorDropdown').classList.remove('matt_show');
    changeWord(wordId);
}

document.addEventListener('click', (e) => {
    const dropdown = document.getElementById('wordSelectorDropdown');
    const wrapper = document.querySelector('.matt_word-selector-wrapper');
    if (dropdown && wrapper && !wrapper.contains(e.target)) {
        dropdown.classList.remove('matt_show');
    }
});